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


def near_threshold(spread_pct, count=300):
    """A stream whose worst interval deviates by exactly `spread_pct` percent.

    §5.4 classifies an asset as VFR when the spread exceeds 1% of the nominal
    interval. A fixture that only produces an obvious 100% spread proves the
    detector fires; it does not prove where the boundary is. This one sits
    either side of it, which is what catches a threshold written with the
    wrong comparison operator — a bug that survives review indefinitely.
    """
    deviation = int(round(NOMINAL_US * spread_pct / 100.0))
    pts = []
    t = 0
    for i in range(count):
        pts.append(t)
        step = NOMINAL_US + (deviation if i == count // 2 else 0)
        t += step
    return pts


if __name__ == "__main__":
    pts = generate()
    print(f"{len(pts)} frames, {pts[-1] / 1e6:.2f} s, spread {spread(pts):.1%}, "
          f"VFR={is_vfr(pts)}, reordered equal after sort="
          f"{sorted(reorder(pts)) == sorted(pts)}")
    for pct in (0.9, 1.1):
        near = near_threshold(pct)
        print(f"near threshold {pct}%: spread {spread(near):.2%}, VFR={is_vfr(near)}")
