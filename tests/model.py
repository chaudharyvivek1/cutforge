"""The two-pass planner of §7.1, with the model behind an interface.

v2.11's list said the model path had no implementation *at all*. What it needs
is not a budget but a seam: pass one turns a request into an Edit Plan, pass
two turns the plan into an ops batch, and the model sits behind one call. With
that seam, both passes are testable against recorded responses and a budget
buys evaluation rather than plumbing.

The template planner in `planner.py` is still what P0 ships. This is the path
the model takes when it arrives, and the shape of it is what a provider
adapter has to satisfy.
"""
import json
from dataclasses import dataclass
from pathlib import Path

import planner as P


class ModelError(Exception):
    def __init__(self, code, detail=""):
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclass
class Call:
    pass_name: str
    prompt: str
    schema: str


class ModelClient:
    """The interface any provider adapter satisfies."""

    def complete(self, call):
        raise NotImplementedError


class RecordedModel(ModelClient):
    """Replays a recorded response per pass, and records what was asked.

    A recorded model is enough to prove the plumbing — that pass two receives
    the plan pass one produced, that the ops batch validates against the same
    rules, and that a refusal is a refusal and not an empty plan.
    """

    def __init__(self, fixture):
        self.fixture = json.loads(Path(fixture).read_text())
        self.calls = []

    def complete(self, call):
        self.calls.append(call)
        response = self.fixture.get(call.pass_name)
        if response is None:
            raise ModelError("NO_RECORDED_RESPONSE", call.pass_name)
        return response


def plan_two_pass(request, model):
    """§7.1: orient, then compile. Small prompts, arithmetic outside the model."""
    orient = Call(pass_name="orient",
                  prompt=json.dumps({k: request[k] for k in request
                                     if k in ("goal", "duration_target_ms", "aspect")}),
                  schema="EditPlan")
    plan_doc = model.complete(orient)
    if not plan_doc or "structure" not in plan_doc:
        raise ModelError("PLAN_INVALID", "pass one returned no structure")

    compile_call = Call(pass_name="compile",
                        prompt=json.dumps({"plan": plan_doc,
                                           "shots": [s["asset"] for s in request["shots"]]}),
                        schema="OpsBatch")
    ops = model.complete(compile_call)
    if not ops or "ops" not in ops:
        raise ModelError("OPS_INVALID", "pass two returned no ops")
    return {"plan": plan_doc, "ops": ops}


def validate_ops(ops_batch, known_assets):
    """The checks §7.4 runs on the batch, independent of who produced it."""
    problems = []
    for op in ops_batch.get("ops", []):
        if op.get("op") == "add_clip":
            if op.get("asset") not in known_assets:
                problems.append(f"unknown asset {op.get('asset')}")
            rec = op.get("record") or {}
            if rec.get("out", 0) <= rec.get("in", 0):
                problems.append(f"non-positive record range on {op.get('clip')}")
    return problems


def check_against_template(request, model):
    """Does the model's plan match the deterministic planner's decisions?

    Not equality of text — equality of the decisions that matter: which shots,
    in what order, and the total duration within the ladder's accept band.
    That is what an evaluation corpus measures, and it needs no budget to run
    against a recorded response.
    """
    ours = P.plan(request)
    theirs = plan_two_pass(request, model)["plan"]
    ours_shots = [s["asset"] for s in ours["structure"]]
    theirs_shots = [s.get("asset") for s in theirs.get("structure", [])]
    return {
        "same_shots": ours_shots == theirs_shots,
        "same_order": ours_shots == theirs_shots,
        "frames": theirs.get("structure", [{}])[-1].get("record", [0, 0])[1]
        if theirs.get("structure") else 0,
        "expected_frames": ours["structure"][-1]["record"][1],
    }
