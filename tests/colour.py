"""A colour-difference metric, so "matched within a tolerance" can be a number.

§11.4 says per-shot matching needs an acceptance test. A tolerance in ΔE is the
usual form, and ΔE needs Lab. This is CIE76 — the simplest of the three — and
it is enough to make the tolerance checkable rather than aspirational.
"""
import math


def srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb):
    r, g, b = (srgb_to_linear(c) for c in rgb)
    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t) + (16 / 116)

    fx, fy, fz = f(x / 0.95047), f(y / 1.00000), f(z / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e(lab_a, lab_b):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab_a, lab_b)))


def mean_delta_e(frame_a, frame_b):
    """Mean CIE76 over two lists of RGB triples — a frame, summarised."""
    if len(frame_a) != len(frame_b):
        raise ValueError("frames must be the same size")
    total = sum(delta_e(rgb_to_lab(a), rgb_to_lab(b)) for a, b in zip(frame_a, frame_b))
    return total / len(frame_a)


def apply_gain(frame, gain):
    """A synthetic exposure change, for the matching fixture."""
    return [tuple(min(255, max(0, round(c * gain))) for c in pixel) for pixel in frame]
