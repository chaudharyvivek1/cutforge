"""Calibrating the rubric against plans labelled by construction (§19.2).

v2.12's rubric had thresholds written in the same hour as the planner fix they
now pass: the hook band's upper edge sat just above the cap imposed on the
planner. That is circular, and the way out is a labelled set the rubric was
not tuned on.

Every plan here is labelled by a rule stated in its `why`, and none of the
labels mentions a threshold. A plan is bad because a viewer would reject it —
a single unbroken take, a twenty-second opening, a film that misses its
length by half — not because it scores below a number.
"""
from fractions import Fraction as F

import rubric as RB

PROJECT_FPS = F(30000, 1001)


def shot(start, end):
    return {"record": [start, end]}


def even(frames, n):
    share = frames // n
    out = []
    cursor = 0
    for i in range(n):
        length = share if i < n - 1 else frames - cursor
        out.append(shot(cursor, cursor + length))
        cursor += length
    return out


def sequential(lengths):
    """Shots laid end to end from a list of lengths."""
    out, cursor = [], 0
    for length in lengths:
        out.append(shot(cursor, cursor + length))
        cursor += length
    return out


def labelled_set():
    """Plans a viewer would accept, and plans a viewer would reject."""
    total = 1349          # 45 s at 29.97
    return [
        # ---- accept: someone would publish these
        {"plan": {"structure": [shot(0, 90), shot(90, 420), shot(420, 800),
                                shot(800, 1100), shot(1100, 1349)]},
         "label": "good", "why": "three-second hook, then four cuts to the payoff"},
        {"plan": {"structure": sequential([60] + [215] * 5 + [total - 60 - 1075])},
         "label": "good", "why": "two-second hook, six cuts, lands on target"},
        {"plan": {"structure": [shot(0, 75), shot(75, 700), shot(700, 1349)]},
         "label": "good", "why": "a short hook, a long middle, a longer payoff"},

        # ---- reject: a viewer would close the tab
        {"plan": {"structure": [shot(0, 1349)]},
         "label": "bad", "why": "one unbroken 45-second take"},
        {"plan": {"structure": [shot(0, 900), shot(900, 1349)]},
         "label": "bad", "why": "a thirty-second opening shot is not a hook"},
        {"plan": {"structure": even(1349, 4)},
         "label": "bad", "why": "four even cuts: an eleven-second opening is not a hook"},
        {"plan": {"structure": even(300, 3)},
         "label": "bad", "why": "ten seconds long when forty-five were asked for"},
        {"plan": {"structure": even(4000, 2)},
         "label": "bad", "why": "two minutes long when forty-five were asked for"},
        {"plan": {"structure": [shot(0, 5)] + even(total - 5, 40)[1:]},
         "label": "bad", "why": "a five-frame hook is a flash frame"},
        {"plan": {"structure": []},
         "label": "bad", "why": "no structure at all"},

        # ---- the second ten, added in v2.14 and labelled before scoring
        {"plan": {"structure": [shot(0, 45), shot(45, 500), shot(500, 900),
                                shot(900, 1349)]},
         "label": "good", "why": "a one-and-a-half second hook, three cuts, on target"},
        {"plan": {"structure": even(1349, 7)},
         "label": "bad", "why": "seven even cuts: a three-second hook needs an uneven share"},
        {"plan": {"structure": [shot(0, 120), shot(120, 1349)]},
         "label": "bad", "why": "a four-second opening is past the point a hook holds"},
        {"plan": {"structure": [shot(0, 90), shot(90, 1349)]},
         "label": "good", "why": "a three-second hook and a long payoff, deliberately slow"},
        {"plan": {"structure": [shot(0, 90)] + [shot(90 + 70 * i, 90 + 70 * (i + 1))
                                                for i in range(18)]},
         "label": "good", "why": "eighteen cuts: fast, but the reel is a montage"},
        {"plan": {"structure": [shot(0, 2), shot(2, 1349)]},
         "label": "bad", "why": "a two-frame opening is a flash"},
        {"plan": {"structure": even(1349, 2)},
         "label": "bad", "why": "two even cuts: a twenty-two second opening"},
        {"plan": {"structure": [shot(0, 60), shot(60, 120), shot(120, 180),
                                shot(180, 1349)]},
         "label": "good", "why": "three quick cuts then a long payoff"},
        {"plan": {"structure": even(1349, 40)},
         "label": "bad", "why": "forty cuts in forty-five seconds is a slideshow"},
        {"plan": {"structure": [shot(0, 90), shot(90, 700), shot(700, 1300)]},
         "label": "good",
         "why": "fifty frames short — 3.7 per cent, inside delivery tolerance"},
    ]


def separation(request=None):
    """Does the rubric rank the accepted plans above the rejected ones?

    Reported as the fraction of (good, bad) pairs ordered correctly — the
    same question as an AUC, asked in the vocabulary of a review. A rubric
    that cannot separate plans it was not tuned on is decoration.
    """
    request = request or {"duration_target_ms": 45011,
                          "shots": [{"labels": []}] * 6}
    rows = labelled_set()
    scored = []
    for row in rows:
        result = RB.score(row["plan"], request)
        scored.append({**row, "total": result["total"],
                       "verdict": result["verdict"],
                       "failed": [k for k, v in result["criteria"].items() if v < 0.99]})

    good = [r for r in scored if r["label"] == "good"]
    bad = [r for r in scored if r["label"] == "bad"]
    pairs = [(g["total"], b["total"]) for g in good for b in bad]
    ordered = sum(1 for g, b in pairs if g > b)
    tied = sum(1 for g, b in pairs if g == b)
    return {
        "scored": scored,
        "good": len(good),
        "bad": len(bad),
        "pairs": len(pairs),
        "ordered": ordered,
        "tied": tied,
        "separation": round((ordered + 0.5 * tied) / len(pairs), 3) if pairs else 0.0,
    }


def disagreements(request=None):
    """Where the rubric and the labels part company.

    A calibration set that never disagrees is a set the rubric already agrees
    with — either because the labels were written by looking at the scores, or
    because the rubric learned the labels. Either way it proves nothing. This
    reports the disagreements so they can be read rather than assumed absent.
    """
    result = separation(request)
    return [r for r in result["scored"]
            if (r["label"] == "good" and r["verdict"] != "acceptable")
            or (r["label"] == "bad" and r["verdict"] == "acceptable")]


# ------------------------------------------------------------ blind labelling
def label_from_request(request):
    """A label derived from the request, before any plan exists.

    v2.14's set was labelled by one author who is also the rubric's author, so
    a label could always be adjusted after seeing a score. Labelling from the
    request removes that: the expectations are written down first, and a plan
    is then judged against them rather than against a number.

    This is the harness a second author needs, not a substitute for one.
    """
    import planner

    target = request["duration_target_ms"]
    shots = [s for s in request.get("shots", [])
             if not set(s.get("labels", [])) & set(request.get("must_avoid", []))]
    return {
        "target_ms": target,
        "shots_available": len(shots),
        # The same constant the planner enforces, so producer and judge cannot
        # drift. Two copies of one rule is this repository's recurring defect,
        # and a judge with its own 3000 ms rejected the planner's 90-frame hook
        # by three milliseconds.
        "expected_hook_max_frames": planner.HOOK_MAX_FRAMES,
        # A hook has a floor as well as a cap: two frames is a flash, not an
        # opening. The judge had only the cap, and a flash frame passed it.
        "expected_hook_min_frames": round(0.7 * float(PROJECT_FPS)),
        "expected_hook_max_ms": round(
            float(planner.HOOK_MAX_FRAMES) / float(PROJECT_FPS) * 1000),
        "expected_cuts": max(1, round(target / 6000)),
        # A target, not a floor. v2.15's first judge demanded the full target
        # and rejected seven plans the rubric accepts, including four-cut reels
        # a viewer would happily watch. The floor is half the target, and it is
        # stated here so the judge and the rubric read one number.
        "min_cuts": max(2, round(target / 6000) // 2),
        "expected_total_ms": target,
        "tolerance_ms": round(target * 0.05),
        # stated before scoring, so it cannot be revised to fit a result
        "accept_if": [f"hook between 700 ms and {planner.HOOK_MAX_FRAMES} frames",
                      "total within 5 per cent of target",
                      "at least half the cut target, capped by material",
                      "mean shot at least 1500 ms"],
    }


def judge(plan, request):
    """Judge a plan against the request's stated expectations, not a score."""
    expect = label_from_request(request)
    structure = plan.get("structure", [])
    if not structure:
        return {"label": "bad", "why": "no structure"}
    lengths = [s["record"][1] - s["record"][0] for s in structure]
    fps = PROJECT_FPS
    ms = lambda frames: float(frames) / float(fps) * 1000  # noqa: E731

    reasons = []
    if lengths[0] > expect["expected_hook_max_frames"]:
        reasons.append("hook over the cap")
    if lengths[0] < expect["expected_hook_min_frames"]:
        reasons.append("hook under 700 ms")
    total_ms = ms(sum(lengths))
    if abs(total_ms - expect["expected_total_ms"]) > expect["tolerance_ms"]:
        reasons.append("total outside 5 per cent")
    floor = min(expect["min_cuts"], expect["shots_available"] or 1)
    notes = []
    if len(structure) < floor:
        # A slow film is a legitimate film. The rubric gives partial credit for
        # pacing rather than failing it, and the judge must not be stricter than
        # the thing it is checking — three of v2.15's four disagreements were
        # slow-but-legitimate plans rejected by a cut floor.
        notes.append("slower than the cut target")
    if total_ms / len(structure) < 1500:
        reasons.append("mean shot under 1500 ms")
    return {"label": "bad" if reasons else "good",
            "why": "; ".join(reasons) or "meets the stated expectations",
            "notes": notes}


def compare_expectation_lists(first, second):
    """Diff two independently written expectation lists (finding 5).

    v2.15's harness writes expectations before a plan exists, so a label cannot
    be revised after a score. The remaining circularity is human: the same
    person wrote the rubric and the expectations. This compares two lists field
    by field so a second person's can be read against the first without either
    being privileged.
    """
    fields = sorted(set(first) | set(second))
    diffs = []
    for field in fields:
        a, b = first.get(field), second.get(field)
        if isinstance(a, list) and isinstance(b, list):
            if sorted(map(str, a)) != sorted(map(str, b)):
                diffs.append({"field": field, "first": a, "second": b})
        elif a != b:
            diffs.append({"field": field, "first": a, "second": b})
    return {"fields": len(fields), "differences": diffs}
