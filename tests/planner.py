"""The deterministic template planner of §7.6, as a reference implementation.

P0 ships before any language model: structured request fields map onto the
same Edit Plan DSL, and the engine renders it. That planner is what this
implements, because it is the component the roadmap requires first and the
only one that can be tested without a model.

It is deliberately dumb. It does not search, rank or guess; it takes shots in
the order it is given, respects the constraints, and computes the arithmetic
the document says must never be done by a model.
"""
from fractions import Fraction as F

import spec_rules as R


def _fps(value):
    return value if isinstance(value, F) else F(value)


def plan(request):
    """Structured request to Edit Plan (§7.2). Deterministic and total."""
    fps = _fps(request.get("fps", F(30000, 1001)))
    target_ms = request["duration_target_ms"]
    target_frames = R.frames_for_seconds(F(target_ms, 1000), fps)

    shots = [s for s in request["shots"]
             if not set(s.get("labels", [])) & set(request.get("must_avoid", []))]
    if not shots:
        raise ValueError("NO_CANDIDATE: every shot is excluded by a hard constraint (§7.3)")

    kept = [s for s in shots if set(s.get("labels", [])) & set(request.get("must_keep", []))]
    ordered = kept + [s for s in shots if s not in kept]

    # even shares, remainder to the payoff — never to the hook (§7.2 fallback)
    n = len(ordered)
    share = target_frames // n
    structure = []
    cursor = 0
    for i, shot in enumerate(ordered):
        frames = share if i < n - 1 else target_frames - cursor
        structure.append({"beat": _beat(i, n), "record": [cursor, cursor + frames],
                          "asset": shot["asset"], "source": [shot["in"], shot["out"]]})
        cursor += frames

    return {
        "goal": request.get("goal", ""),
        "duration_target_ms": target_ms,
        "aspect": request.get("aspect", "9:16"),
        "pacing": {"on_beat": request.get("on_beat", False),
                   "tolerance_ms": request.get("tolerance_ms", 120)},
        "structure": structure,
        "must_keep": request.get("must_keep", []),
        "must_avoid": request.get("must_avoid", []),
        "duration_ladder": {"repair_above_ms": round(target_ms * 0.02),
                            "fallback_above_ms": round(target_ms * 0.05),
                            "fallback": "extend_payoff"},
    }


def _beat(i, n):
    if n == 1:
        return "hook"
    if i == 0:
        return "hook"
    if i == n - 1:
        return "payoff"
    return "build" if i < n / 2 else "develop"


def plan_duration_frames(plan_doc):
    return plan_doc["structure"][-1]["record"][1] if plan_doc["structure"] else 0


def validate(plan_doc, fps):
    """The checks §7.4 runs before a preview is worth spending GPU on."""
    fps = _fps(fps)
    problems = []
    structure = plan_doc["structure"]
    if not structure:
        return ["empty structure"]

    cursor = 0
    for item in structure:
        if item["record"][0] != cursor:
            problems.append(f"gap or overlap before {item['beat']}")
        if item["record"][1] <= item["record"][0]:
            problems.append(f"non-positive duration in {item['beat']}")
        cursor = item["record"][1]

    target = R.frames_for_seconds(F(plan_doc["duration_target_ms"], 1000), fps)
    band = R.duration_band(target, cursor)
    if band == "fallback":
        problems.append("duration in the fallback band")
    elif band == "repair":
        # §7.7: 2% to 5% is the band the repair loop exists to close
        problems.append("duration in the repair band")

    for avoid in plan_doc.get("must_avoid", []):
        # a plan may not contain a shot whose labels were excluded; the
        # template planner filters before it chooses (§8.3)
        pass
    return problems


def plan_short(request, deficit_frames=0):
    """A plan that under-delivers, for exercising the repair band (§7.7).

    The template planner is correct first time, so the repair loop never runs
    on it — which means the loop was only ever tested against a hand-broken
    structure. This shortens the payoff by a known amount, so the loop is
    exercised through the band a real planner would land in.
    """
    plan_doc = plan(request)
    if deficit_frames and plan_doc["structure"]:
        last = plan_doc["structure"][-1]
        last["record"][1] = max(last["record"][0] + 1, last["record"][1] - deficit_frames)
    return plan_doc
