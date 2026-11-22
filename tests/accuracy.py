"""Measuring identity accuracy, which is different from achieving it.

§8.6 sets false-positive ≤ 1%, false-negative ≤ 2% and a grey band ≤ 8% of
detections. Those numbers cannot be reached without a labelled corpus, and the
repository does not carry one — so this measures the *measurement*: given
labelled distances, does the harness report the rates the definitions imply?

A harness that has never been checked against a known answer is a harness that
will quietly report 0% because it counted nothing.
"""
from collections import Counter


def rates(pairs, accept=0.35, reject=0.55):
    """FPR, FNR, grey-band rate and decision counts for labelled pairs.

    `pairs` is [(distance, same_person: bool)]. The definitions are §8.6's:
    a false positive is a different person accepted, a false negative is the
    same person rejected, and the grey band is neither.
    """
    counts = Counter()
    for distance, same in pairs:
        if distance <= accept:
            counts["tp" if same else "fp"] += 1
        elif distance >= reject:
            counts["fn" if same else "tn"] += 1
        else:
            counts["grey"] += 1
    positives = counts["tp"] + counts["fn"] + counts["grey"]
    negatives = counts["fp"] + counts["tn"] + counts["grey"]
    detections = sum(counts.values())
    return {
        "fpr": counts["fp"] / (counts["fp"] + counts["tn"]) if counts["fp"] + counts["tn"] else 0.0,
        "fnr": counts["fn"] / (counts["tp"] + counts["fn"]) if counts["tp"] + counts["fn"] else 0.0,
        "grey_rate": counts["grey"] / detections if detections else 0.0,
        "counts": {k: counts[k] for k in ("tp", "fp", "fn", "tn", "grey")},
        "positives": positives,
        "negatives": negatives,
    }


def meets_targets(result, fpr=0.01, fnr=0.02, grey=0.08):
    """§8.6's acceptance, as a function rather than a paragraph."""
    failures = []
    if result["fpr"] > fpr:
        failures.append(f"fpr {result['fpr']:.2%} > {fpr:.0%}")
    if result["fnr"] > fnr:
        failures.append(f"fnr {result['fnr']:.2%} > {fnr:.0%}")
    if result["grey_rate"] > grey:
        failures.append(f"grey {result['grey_rate']:.2%} > {grey:.0%}")
    return failures


def synthetic_corpus(n_pairs=500, separation=0.55, seed=20261122):
    """A labelled set with a known answer, so the harness can be checked.

    Two clusters: same-person distances drawn below the accept threshold and
    different-person distances above the reject threshold, with `separation`
    controlling how cleanly they part.
    """
    import random
    rng = random.Random(seed)
    pairs = []
    for _ in range(n_pairs):
        if rng.random() < 0.5:
            pairs.append((max(0.0, rng.gauss(0.20, 0.08)), True))
        else:
            pairs.append((min(1.0, rng.gauss(0.85, 0.10)), False))
    return pairs
