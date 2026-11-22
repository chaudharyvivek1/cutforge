"""Scoring an edit plan on more than agreement (§19.2).

v2.11 could tell whether a plan matched the template planner. That measures
agreement, and a model that agrees with a template is not necessarily a model
that produces a good edit — the template is a floor, not a standard.

This scores the things §19.2's rubric names, and every one of them is
computable from the plan alone, so the score is reproducible and a regression
is a number rather than an opinion. What it cannot judge is taste: whether the
hook is *interesting* needs a human, and the rubric says so.
"""
from fractions import Fraction as F

PROJECT_FPS = F(30000, 1001)


def _frames(ms):
    return F(ms) * PROJECT_FPS / 1000


def _shot_lengths(plan):
    out = []
    for shot in plan.get("structure", []):
        rec = shot.get("record") or [0, 0]
        out.append(rec[1] - rec[0])
    return out


def score(plan, request=None):
    """A rubric with four measurable criteria and one that is not."""
    lengths = _shot_lengths(plan)
    if not lengths:
        return {"total": 0.0, "verdict": "no structure", "criteria": {}}

    target = _frames((request or {}).get("duration_target_ms", 45000))
    total = lengths[-1] if len(lengths) == 1 else sum(lengths)

    # 1. Hook: the first shot must be short enough to hold attention and long
    #    enough to be read. Below half a second it is a flash frame; above
    #    three seconds it is not a hook.
    hook = lengths[0]
    hook_score = 1.0 if _frames(700) <= hook <= _frames(3200) else 0.0

    # 2. Payoff: the film must land on something rather than stopping.
    #    v2.12 required the last shot to be at least the median, which fails
    #    half of all plans by construction — a criterion that rejects half the
    #    sample on its own definition is measuring the sample, not the plan.
    #    Within a quarter of the median still reads as a payoff.
    others = sorted(lengths[:-1]) or [lengths[-1]]
    median = others[len(others) // 2]
    payoff_score = 1.0 if lengths[-1] >= median * F(3, 4) else 0.0

    # 3. Duration: within one frame of the target. §7.4's ladder either hits
    #    it or reports the deficit, so a plan that misses is a plan the ladder
    #    will repair — and a repaired plan is not a scored plan.
    duration_score = 1.0 if abs(total - target) <= 1 else max(
        0.0, 1.0 - float(abs(total - target) / target))

    # 4. Pacing: cuts roughly every six seconds, capped by the material.
    #    v2.12's first version asked that no shot exceed a third of the film,
    #    which is unsatisfiable for a two-shot reel — with two shots one of them
    #    is always at least half. A criterion nobody can pass measures the
    #    rubric, not the plan, so this one compares cuts made to cuts the
    #    available material could support.
    seconds = float(total) / float(PROJECT_FPS)
    wanted = max(1, int(-(-seconds // 6)))          # ceil: one cut per six seconds
    avoid = set((request or {}).get("must_avoid", []))
    candidates = [s for s in (request or {}).get("shots", [])
                  if not set(s.get("labels", [])) & avoid]
    # A planner honouring a hard constraint is not under-cutting; the material
    # it was allowed to use is what the cut density is measured against.
    available = len(candidates) or len(lengths)
    wanted = min(wanted, available)
    pacing_score = round(min(1.0, len(lengths) / wanted), 3)

    criteria = {
        "hook": hook_score,
        "payoff": payoff_score,
        "duration": round(duration_score, 3),
        "pacing": pacing_score,
    }
    # Taste is deliberately absent: §19.2 says a human labels that, and a
    # score that silently omitted it would look more complete than it is.
    total_score = sum(criteria.values()) / len(criteria)
    # A verdict of "below bar" needs a hard failure or a genuinely poor score.
    # v2.12 demanded 0.99 on every criterion, which called a plan with slightly
    # slow pacing unacceptable — a bar no real edit clears, and a rubric that
    # rejects everything separates nothing.
    return {
        "total": round(total_score, 3),
        "verdict": ("below bar" if min(criteria.values()) == 0 or total_score < 0.75
                    else "acceptable"),
        "criteria": criteria,
        "unmeasured": ["taste: whether the hook is interesting (human label)"],
    }


def compare(plan_a, plan_b, request=None):
    """Which of two plans scores higher, and on what."""
    a, b = score(plan_a, request), score(plan_b, request)
    better = "b" if b["total"] > a["total"] else "a" if a["total"] > b["total"] else "tie"
    return {"a": a, "b": b, "better": better,
            "delta": round(b["total"] - a["total"], 3)}
