"""A second judge of a different shape (§19.2).

v2.15's two judges agreed by construction: both read the same constants, so
their agreement was a regression guard rather than evidence. A second opinion
has to measure something the first does not.

This one measures the *shape of the shot-length distribution* rather than any
threshold. A real edit varies its shot lengths — a two-second hook, a long
middle, a payoff — and a machine that divides a target evenly produces a
distribution with no spread at all. That is a different question from "is the
hook under three seconds", and it can be wrong in different ways.
"""
from fractions import Fraction as F

PROJECT_FPS = F(30000, 1001)

# Below this, the shot lengths carry no information: the plan was divided
# evenly rather than edited.
UNIFORM_CV = 0.05


def _stats(lengths):
    n = len(lengths)
    mean = F(sum(lengths), n)
    if mean == 0:
        return mean, F(0)
    variance = sum((F(x) - mean) ** 2 for x in lengths) / n
    sd = variance ** F(1, 2)
    return mean, sd / mean            # coefficient of variation


def judge(plan, request=None):
    """Bad when the distribution is degenerate, not when a number is out of range."""
    structure = plan.get("structure", [])
    if not structure:
        return {"label": "bad", "why": "no structure", "cv": 0.0}
    lengths = [s["record"][1] - s["record"][0] for s in structure]
    if len(lengths) == 1:
        return {"label": "bad", "why": "a single take has no rhythm", "cv": 0.0}

    mean, cv = _stats(lengths)
    cv = float(cv)
    # A montage of equal beats is a legitimate form; an evenly divided short
    # film is not. The distinction is the mean shot length — a cut every three
    # seconds or faster is a montage, and anything slower that is perfectly even
    # was divided rather than edited — not the cut count:
    # v2.16's first version exempted plans with more than six cuts, which let
    # seven evenly divided shots — the exact case it was meant to catch — pass.
    seconds = float(mean) / float(PROJECT_FPS)
    if cv < UNIFORM_CV and seconds >= 3.0:
        return {"label": "bad", "why": "shot lengths carry no information: evenly divided",
                "cv": cv}
    return {"label": "good", "why": "shot lengths vary", "cv": cv}


def compare_with_thresholds(plans, request=None):
    """Where a distribution judge and a threshold judge disagree.

    Disagreement is the product. Two judges agreeing on everything are either
    both right or both reading the same number, and only one of those is good
    news — so the pairs are printed rather than counted.
    """
    import rubric
    rows = []
    for row in plans:
        shape = judge(row["plan"], request)
        threshold = rubric.score(row["plan"], request)
        rows.append({
            "why": row["why"],
            "label": row.get("label"),
            "shape": shape["label"],
            "threshold": threshold["verdict"],
            "cv": round(shape["cv"], 3),
            "agree": (shape["label"] == "good")
                     == (threshold["verdict"] == "acceptable"),
        })
    agree = sum(1 for r in rows if r["agree"])
    return {"rows": rows, "agree": agree, "total": len(rows),
            "disagreements": [r for r in rows if not r["agree"]]}


def coverage(plans, request=None):
    """Which judge catches which bad plan — the union, not the agreement.

    v2.15 measured agreement between two judges that read one set of constants.
    This measures coverage between two judges with different blind spots, which
    is the only sense in which a second opinion adds anything: a shape judge
    cannot see a hook that is too long, and a threshold judge cannot see a plan
    that happens to satisfy every threshold for the wrong reason.
    """
    import rubric
    rows = []
    for row in plans:
        shape = judge(row["plan"], request)
        threshold = rubric.score(row["plan"], request)
        rows.append({
            "why": row["why"], "label": row.get("label"),
            "shape_catches": shape["label"] == "bad",
            "threshold_catches": threshold["verdict"] != "acceptable",
        })
    bad = [r for r in rows if r["label"] == "bad"]
    good = [r for r in rows if r["label"] == "good"]
    return {
        "rows": rows,
        "bad": len(bad),
        "caught_by_either": sum(1 for r in bad
                                if r["shape_catches"] or r["threshold_catches"]),
        "caught_by_shape_only": sum(1 for r in bad
                                    if r["shape_catches"] and not r["threshold_catches"]),
        "caught_by_threshold_only": sum(1 for r in bad
                                        if r["threshold_catches"] and not r["shape_catches"]),
        "false_alarms": sum(1 for r in good
                            if r["shape_catches"] and r["threshold_catches"]),
        "shape_false_alarms": sum(1 for r in good if r["shape_catches"]),
    }
