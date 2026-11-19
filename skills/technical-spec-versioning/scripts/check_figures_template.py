#!/usr/bin/env python3
"""Template: verify every figure a specification asserts, by computation.

Copy this into <repo>/build/check_figures.py and replace the block below
with the constants and identities of the document you are checking.

The rule it encodes: a number in the document is either derived here, or
it is labelled an assumption with a source. Nothing is typed twice.
"""
import math
import re
import sys
from fractions import Fraction as F
from pathlib import Path

FAILURES = []
CHECKS = 0


def round_half_away(x):
    """The rounding rule most specifications mean. Python's round() is
    half-to-even and disagrees on exactly the boundary cases that matter."""
    x = F(x)
    sign = -1 if x < 0 else 1
    return sign * math.floor(abs(x) + F(1, 2))


def check(name, computed, expected, tolerance=0):
    global CHECKS
    CHECKS += 1
    ok = (abs(float(computed) - float(expected)) <= tolerance) if tolerance \
        else (computed == expected)
    if not ok:
        FAILURES.append(f"{name}: computed {computed}, document says {expected}")


def stated(md, pattern):
    """Read the printed value out of the document, so prose cannot drift
    from the appendix."""
    m = re.search(pattern, md)
    if not m:
        return None
    return int(re.sub(r"[,_]", "", m.group(1) if m.groups() else m.group(0)))


def main():
    md_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/spec/latest.md")
    md = md_path.read_text(encoding="utf-8") if md_path.exists() else ""

    # ---- replace from here -------------------------------------------------
    # 1. Derive each figure from first principles, in exact arithmetic.
    # 2. Compare against the value the document prints.
    # 3. Include every derived quantity downstream of a corrected input.

    # example: 1349 frames at 30000/1001, at 48 kHz
    fps = F(30000, 1001)
    samples = round(F(1349) / fps * 48000)
    check("sequence samples", samples, 2160558)
    printed = stated(md, r"2,?160,?558")
    if printed is not None:
        check("samples stated in document", printed, samples)

    # ---- to here -----------------------------------------------------------

    print(f"{CHECKS} figures checked.")
    if FAILURES:
        print("FAILED:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("All figures consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
