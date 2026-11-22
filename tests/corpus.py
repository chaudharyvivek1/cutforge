"""The labelled set §8.6 needs, as a contract rather than an aspiration.

The repository cannot carry a corpus of real faces, and synthesising one would
be dishonest. What it can carry is the *shape* — so that the corpus has
somewhere to land, and so that a set that arrives malformed is rejected before
it is used to make a claim about accuracy.
"""
import json
from pathlib import Path

REQUIRED = {"id", "distance", "same_person", "conditions"}
CONDITIONS = {"lighting", "angle", "occlusion", "age"}


def validate(entries):
    """Reject a corpus that cannot support §8.6's claims."""
    problems = []
    if not entries:
        return ["empty corpus"]
    seen = set()
    for n, entry in enumerate(entries):
        missing = REQUIRED - set(entry)
        if missing:
            problems.append(f"entry {n}: missing {sorted(missing)}")
            continue
        if entry["id"] in seen:
            problems.append(f"entry {n}: duplicate id {entry['id']}")
        seen.add(entry["id"])
        if not isinstance(entry["same_person"], bool):
            problems.append(f"entry {n}: same_person must be a boolean")
        if not 0.0 <= float(entry["distance"]) <= 1.0:
            problems.append(f"entry {n}: distance outside 0..1")
        if not CONDITIONS <= set(entry["conditions"]):
            problems.append(f"entry {n}: conditions must span {sorted(CONDITIONS)}")
    # §8.6 says the set spans lighting, angle, occlusion and age
    for condition in CONDITIONS:
        if not any(condition in e.get("conditions", []) for e in entries):
            problems.append(f"corpus has no {condition} variation")
    if not any(e.get("same_person") for e in entries):
        problems.append("corpus has no positive pairs")
    if not any(not e.get("same_person") for e in entries):
        problems.append("corpus has no negative pairs")
    return problems


def load(path, synthetic=False):
    """Load a corpus, and refuse to pretend a synthetic one is a measurement.

    v2.3 committed a synthetic fixture with a note in its first line, which is
    the kind of warning a reader skims past and then quotes. The flag puts the
    distinction in the signature instead of in a comment.
    """
    data = json.loads(Path(path).read_text())
    problems = validate(data.get("pairs", []))
    if problems:
        raise ValueError("; ".join(problems))
    if data.get("synthetic") and not synthetic:
        raise ValueError("this corpus is synthetic; pass synthetic=True and do not "
                         "quote its rates as accuracy")
    return data
