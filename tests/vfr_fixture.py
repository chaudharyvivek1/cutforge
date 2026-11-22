"""Generate the VFR fixture the specification asks for, rather than sourcing one.

§5.9.4 names the fixture — a variable-rate stream with a PTS spread beyond 1%
of nominal, plus one whose packets arrive out of order — and §19 asserts the
properties. A captured screen recording is not reproducible in CI; a generated
one is.

The generator is deterministic: the same seed produces the same timestamps, so
a failing assertion has a fixed example to point at.
"""
import random

NOMINAL_US = 33333          # 30 fps


def generate(count=1800, drops=7, jitter_us=900, seed=20261122):
    """A nominal-30 fps stream with dropped frames and small jitter.

    Returns timestamps in microseconds, monotonically increasing in capture
    order. `drops` removes frames, which widens the gap to about two intervals
    and pushes the spread beyond 1% of nominal.
    """
    rng = random.Random(seed)
    pts = []
    t = 0
    for i in range(count):
        pts.append(t)
        step = NOMINAL_US
        if rng.random() < drops / count:
            step *= 2                       # a dropped frame: the next arrives late
        else:
            step += rng.randint(-jitter_us, jitter_us)
        t += step
    return pts


def reorder(pts, seed=20261122):
    """Deliver the same frames with some adjacent packets swapped.

    A table built from this must equal the table built from the ordered
    stream, because ingest sorts by PTS before mapping. If it does not, the
    sort is the bug rather than the map.
    """
    rng = random.Random(seed)
    out = list(pts)
    for i in range(0, len(out) - 1, 97):
        if rng.random() < 0.5:
            out[i], out[i + 1] = out[i + 1], out[i]
    return out


def spread(pts):
    """Largest deviation of an interval from nominal, as a fraction."""
    deltas = [b - a for a, b in zip(sorted(pts), sorted(pts)[1:])]
    return max(abs(d - NOMINAL_US) / NOMINAL_US for d in deltas)


def is_vfr(pts, threshold=0.01):
    """§5.4: a spread beyond 1% of the nominal interval marks the asset VFR."""
    return spread(pts) > threshold


if __name__ == "__main__":
    pts = generate()
    print(f"{len(pts)} frames, {pts[-1] / 1e6:.2f} s, spread {spread(pts):.1%}, "
          f"VFR={is_vfr(pts)}, reordered equal after sort="
          f"{sorted(reorder(pts)) == sorted(pts)}")
