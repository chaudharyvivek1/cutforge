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


def labelled_set():
    """Plans a viewer would accept, and plans a viewer would reject."""
    total = 1349          # 45 s at 29.97
    return [
        # ---- accept: someone would publish these
        {"plan": {"structure": [shot(0, 90), shot(90, 420), shot(420, 800),
                                shot(800, 1100), shot(1100, 1349)]},
         "label": "good", "why": "three-second hook, then four cuts to the payoff"},
        {"plan": {"structure": [shot(0, 60)] + even(total - 60, 7)[1:]},
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
