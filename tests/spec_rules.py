"""Reference implementation of the deterministic rules the specification states.

This is not the engine. It is the smallest code that can be wrong in the same
way the specification can, so that the specification's worked examples are
executed rather than re-derived in a checker.

Every function here is named after the section that specifies it. If a rule
changes, this file changes with it, and the tests say which example broke.

No dependencies beyond the standard library, on purpose: the point is that
anyone can run it anywhere and get the same answer.
"""
from fractions import Fraction as F
import math


# ---------------------------------------------------------------- §5.1, §5.2
def round_half_away(x):
    """§5.1: half away from zero, applied once, at the boundary only.

    Python's round() is half-to-even and disagrees on exactly the cases a
    frame boundary produces.
    """
    x = F(x)
    sign = -1 if x < 0 else 1
    return sign * math.floor(abs(x) + F(1, 2))


def samples_for(frame, fps, hz=48000):
    """§5.5: a frame boundary converted to an exact sample offset."""
    return round_half_away(F(frame) * hz / fps)


def frames_for_seconds(seconds, fps):
    """§5.1: seconds to frames, rounded once."""
    return round_half_away(F(seconds) * fps)


# ---------------------------------------------------------------------- §5.9
class AffineConformMap:
    """§5.9: the constant-rate conform map. Total on [0, native_duration]."""

    kind = "affine"

    def __init__(self, fps_src, fps_proj, native_duration):
        self.fps_src = F(fps_src)
        self.fps_proj = F(fps_proj)
        self.native_duration = native_duration
        self.version = f"affine-{fps_src}-{fps_proj}"

    def to_conformed(self, n):
        if not 0 <= n <= self.native_duration:
            raise ValueError(f"{n} outside [0, {self.native_duration}]")
        return round_half_away(F(n) * self.fps_proj / self.fps_src)

    def to_native(self, c):
        return F(c) * self.fps_src / self.fps_proj

    @property
    def conformed_duration(self):
        return self.to_conformed(self.native_duration)

    @property
    def conform_delta(self):
        return self.conformed_duration - self.to_conformed(self.native_duration)


class TableConformMap:
    """§5.9.4: the VFR conform map, backed by a sorted table of timestamps.

    Non-decreasing, injective but not necessarily surjective: two packets can
    share a timestamp, and the image can skip conformed indices.
    """

    kind = "table"

    def __init__(self, pts_us, fps_proj, nominal_frame_us=None):
        self.pts = sorted(int(p) for p in pts_us)      # ingest sorts; reorder is not a map bug
        self.fps_proj = F(fps_proj)
        self.nominal = nominal_frame_us or (self._median_delta() if len(self.pts) > 1 else 33333)
        self.version = f"table-{len(self.pts)}-{fps_proj}"
        self._conf = [round_half_away(F(p, 1_000_000) * self.fps_proj) for p in self.pts]

    def _median_delta(self):
        d = sorted(b - a for a, b in zip(self.pts, self.pts[1:]))
        return d[len(d) // 2] or 33333

    @property
    def native_duration(self):
        return len(self.pts)

    def to_conformed(self, n):
        if not 0 <= n < len(self.pts):
            raise ValueError(f"{n} outside [0, {len(self.pts)})")
        return self._conf[n]

    def to_native(self, c):
        """Source timestamp of the last native frame whose image is <= c."""
        candidates = [i for i, cc in enumerate(self._conf) if cc <= c]
        if not candidates:
            return F(0)
        return F(self.pts[candidates[-1]], 1_000_000)

    @property
    def conformed_duration(self):
        span = F(self.pts[-1] + self.nominal, 1_000_000)
        return round_half_away(span * self.fps_proj)

    def skipped_indices(self):
        return [c for c in range(0, self._conf[-1] + 1) if c not in self._conf]


# ------------------------------------------------------------ §5.9.3, §5.11
def conformed_consumption(record_frames, speed):
    """§5.9.3: the number the renderer decodes. R x s, rounded once."""
    return round_half_away(F(record_frames) * F(speed))


def native_projection(record_frames, speed, fps_src, fps_proj):
    """§5.6: the native figure, for reporting and authoring bounds only."""
    return round_half_away(F(record_frames) * F(speed) * F(fps_src) / F(fps_proj))


def atempo_cascade(speed, decimals=7):
    """§5.11: factors within 0.5-2.0, cascaded, residual to seven places.

    Returns the list of factors and the predicted drift in samples for an
    output of the given length, so a validator can reject before rendering.
    """
    speed = F(speed)
    if speed <= 0:
        raise ValueError("speed must be positive")
    if speed > 16 or speed < F(1, 16):
        raise ValueError("speed outside 1/16..16")
    remaining = speed
    factors = []
    while remaining > 2:
        factors.append(F(2))
        remaining /= 2
    while remaining < F(1, 2):
        factors.append(F(1, 2))
        remaining *= 2
    quantised = F(round(float(remaining), decimals)).limit_denominator(10 ** decimals)
    factors.append(quantised)
    return factors


def atempo_drift(speed, output_samples, decimals=7):
    """§5.11: predicted length error of the cascade, in samples.

    For a ratio that is exactly representable at the chosen precision this is
    zero — 3.7 is 2.0 x 1.85 and needs no rounding at all. The interesting
    number is the bound, not this one.
    """
    product = F(1)
    for f in atempo_cascade(speed, decimals):
        product *= f
    return abs(product - F(speed)) * output_samples


def atempo_drift_bound(output_samples, decimals=7):
    """§5.11: the worst case, which is what the precision rule is about.

    A residual truncated to d decimals can be off by up to 10^-d, so the
    length can move by 10^-d x N samples. This is the figure the specification
    quotes: 2.16 samples at six decimals on a 45-second output, 0.216 at seven.
    """
    return F(1, 10 ** decimals) * output_samples


# ---------------------------------------------------------------------- §5.7
def handle_source_frames(dissolve_frames, speed):
    """§5.7: the handle is measured in record frames; the source follows."""
    record_handle = F(dissolve_frames, 2)
    return record_handle * F(speed)


def handle_source_samples(dissolve_frames, speed, fps):
    """§5.7 audio half: convert the boundary once, never double a rounded half.

    samples_for(12) is 19,219 while 2 x samples_for(6) is 19,220. The second
    is the bug: it rounds twice.
    """
    record_handle = F(dissolve_frames, 2) * F(speed)
    return samples_for(record_handle, fps)


# --------------------------------------------------------------------- §5.10
def record_frame_for(native_frame, conform_map, clip_source_in, clip_record_in, speed):
    """§5.10: one affine source-to-record transform for every timed annotation."""
    offset = conform_map.to_conformed(native_frame) - conform_map.to_conformed(clip_source_in)
    return F(clip_record_in) + F(offset) / F(speed)


def beat_interval_frames(bpm, fps, speed=1):
    """§5.10: the grid scales with speed, positions and intervals together."""
    return F(60, bpm) * F(fps) / F(speed)


# ---------------------------------------------------------------------- §7.7
def duration_band(target_frames, actual_frames):
    """§7.7: the ladder, as four named bands rather than two thresholds."""
    if target_frames <= 0:
        raise ValueError("target must be positive")
    deviation = abs(F(actual_frames - target_frames)) / F(target_frames)
    if deviation <= F(2, 100):
        return "accept"
    if deviation <= F(5, 100):
        return "repair"
    return "fallback"


# ------------------------------------------------------------- §16.6.1, §20.3
ERASURE_OUTCOMES = ("withdrawn", "retained_lawful", "restored")
DEFAULT_DEADLINE_DAYS = {"withdrawn": 30, "retained_lawful": 90, "restored": 0}


def erasure_deadline(outcome, jurisdiction_days=None):
    """§16.6.1: the deadline is a function of jurisdiction, not of the document."""
    if outcome not in ERASURE_OUTCOMES:
        raise ValueError(f"unknown outcome {outcome}")
    if jurisdiction_days is not None:
        return jurisdiction_days[outcome]
    return DEFAULT_DEADLINE_DAYS[outcome]


def egress_cost(gb, first_tb_rate=F(9, 100), above_tb_rate=F(5, 100)):
    """§20.3: tiered, because a flat rate is not how delivery is billed."""
    gb = F(gb)
    tier_one = min(gb, F(1000))
    tier_two = max(F(0), gb - F(1000))
    return tier_one * first_tb_rate + tier_two * above_tb_rate
