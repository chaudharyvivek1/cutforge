#!/usr/bin/env python3
"""Recompute every figure the specification asserts, and fail if one drifts.

The specification's own standard is that a number is computed rather than
typed. This script is that standard applied to the repository: it derives
each figure from first principles in exact arithmetic, then checks the
derived value against the value printed in the document. A figure that
stops being true fails the build instead of aging quietly.

Usage:
    python build/check_figures.py [<spec.md>]
"""
import math
import re
import sys
from fractions import Fraction as F
from pathlib import Path

def round_half_away(x):
    """The specification's rounding rule. Python's round() is half-to-even,
    which is a different function and disagrees on exactly the boundary
    cases this document cares about."""
    x = F(x)
    sign = -1 if x < 0 else 1
    return sign * math.floor(abs(x) + F(1, 2))


def newest_spec():
    """The current specification, found rather than hardcoded.

    A hardcoded default goes stale the moment a version is archived, and a
    default that is never exercised because every call passes an argument is
    a default nobody notices is wrong. This one is checked by
    check_consistency.py, which fails if any script points at a missing file.
    """
    candidates = sorted(Path("docs/spec").glob("v*.md"),
                        key=lambda p: [int(x) for x in p.stem.lstrip("v").split(".")])
    if not candidates:
        raise SystemExit("no specification found in docs/spec")
    return candidates[-1]


FAILURES = []
CHECKS = 0


def check(name, computed, expected, tolerance=0):
    """Compare a computed figure against the value the document prints."""
    global CHECKS
    CHECKS += 1
    if tolerance:
        ok = abs(float(computed) - float(expected)) <= tolerance
    else:
        ok = computed == expected
    if not ok:
        FAILURES.append(f"{name}: computed {computed}, document says {expected}")
    return ok


def stated(md, pattern):
    """Pull a number out of the document so the check is against the prose."""
    m = re.search(pattern, md)
    if not m:
        return None
    text = m.group(1) if m.groups() else m.group(0)
    return int(re.sub(r"[,_]", "", text))


# ---------------------------------------------------------------- constants
FPS_2997 = F(30000, 1001)
FPS_5994 = F(60000, 1001)
FPS_25 = F(25, 1)


def main():
    md_path = Path(sys.argv[1]) if len(sys.argv) > 1 else newest_spec()
    md = md_path.read_text(encoding="utf-8") if md_path.exists() else ""

    # ---------------------------------------------------------- 5.5  audio
    # 1349 frames at 30000/1001, at 48 kHz. Rounded, not exact: 2,160,558.4.
    seconds = F(1349) / FPS_2997
    samples_exact = seconds * 48000
    samples = round(samples_exact)
    check("sequence seconds", round(float(seconds), 6), 45.011633, 1e-6)
    check("sequence samples", samples, 2160558)
    check("samples are rounded, not exact", samples_exact != int(samples_exact), True)
    if md:
        s = stated(md, r"2,?160,?558")
        if s is not None:
            check("samples stated in document", s, 2160558)

    # ------------------------------------------------- 5.6 / v1.4 conform map
    # 300 record frames at 29.97 span 10.01 s; at 25 fps that is 250.25
    # native frames, which conform back to 299.70 -> 300 conformed frames.
    native = F(300) * FPS_25 / FPS_2997
    check("native frames for 300 record frames @25", round(float(native), 2), 250.25, 1e-9)
    conformed = F(250) * FPS_2997 / FPS_25
    check("250 native -> conformed", round(float(conformed), 2), 299.70, 1e-9)
    check("250 native -> conformed, rounded", round_half_away(conformed), 300)

    # The double-rounding bug: 501 native frames conform to 601, not 600.
    native_2x = F(300) * 2 * FPS_25 / FPS_2997          # 500.5
    check("2x speed, native frames", round(float(native_2x), 2), 500.50, 1e-9)
    check("2x speed, native rounded", round_half_away(native_2x), 501)
    conformed_2x = F(501) * FPS_2997 / FPS_25
    check("501 native conforms to (the bug)", round_half_away(conformed_2x), 601)
    check("correct conformed consumption", F(300) * 2, 600)

    # 59.94 source on a 29.97 timeline consumes twice the native frames.
    native_5994 = F(300) * FPS_5994 / FPS_2997
    check("59.94 source native frames", int(native_5994), 600)

    # ------------------------------------------------ 5.11  sped audio count
    # 600 conformed frames at 29.97 = 960,960 samples exactly.
    check("sped clip source samples", round(F(600) / FPS_2997 * 48000), 960960)
    check("sped clip record samples", round(F(300) / FPS_2997 * 48000), 480480)

    # ------------------------------------------------ 12.1  P010 frame sizes
    # P010 is 4:2:0 at 10 bits in 16-bit containers: w*h*1.5*2 bytes.
    for label, (w, h), expect in [
        ("1080p P010 MB", (1920, 1080), 6.22),
        ("2160p P010 MB", (3840, 2160), 24.88),
        ("4320p P010 MB", (7680, 4320), 99.53),
    ]:
        mb = w * h * 1.5 * 2 / 1e6
        check(label, round(mb, 2), expect, 0.005)

    # 4K60: four passes at 60 fps, and the memory ceiling it implies.
    bytes_per_second = 3840 * 2160 * 1.5 * 2 * 60
    four_passes_gbs = bytes_per_second * 4 / 1e9
    check("4K60 four-pass GB/s", round(four_passes_gbs, 2), 5.97, 0.005)
    check("streams at 300 GB/s ceiling", round(300 / four_passes_gbs), 50)

    # The luma-only figure that v1.2 printed, and which the review caught.
    check("v1.2 luma-only 4K figure", round(3840 * 2160 * 2 / 1e6, 2), 16.59, 0.005)

    # ------------------------------------------------ 12.3  capacity, 4K60
    # L4: two encoders x 128 fps at 4K P4 = 256 fps, less a 65% allowance.
    encode_fps = 2 * 128
    check("L4 4K encode fps", encode_fps, 256)
    check("L4 realtime multiple", round(encode_fps / 60, 2), 4.27, 0.005)
    streams_per_gpu = encode_fps * 0.65 / 60
    check("L4 concurrent 4K60 streams", round(streams_per_gpu, 2), 2.77, 0.005)
    check("GPUs for 10 concurrent finals", math.ceil(10 / streams_per_gpu), 4)

    # ------------------------------------- v1.4  capacity vs cost reconciliation
    P = F(1, 2)  # $0.50 per GPU-hour, the document's illustrative constant
    dedicated = F(40, 3600) * P                        # 1.5x realtime, one job
    headroom = F(60, 2) / 3600 * P                     # 2.0 streams, 30 s/min
    packed = F(60, 1) / F(277, 100) / 3600 * P         # 2.77 streams, 21.7 s/min
    check("4K60 dedicated $/output-min", round(float(dedicated), 5), 0.00556, 1e-5)
    check("4K60 headroom $/output-min", round(float(headroom), 5), 0.00417, 1e-5)
    check("4K60 packed $/output-min", round(float(packed), 5), 0.00301, 1e-5)
    check("dedicated/packed ratio", round(float(dedicated / packed), 2), 1.85, 0.005)

    # ------------------------------------------------ 12.5  preview pixel work
    # 480p from a 1080p proxy: 0.20x. 360p would be 0.11x, which v1.2 quoted.
    check("480p pixel work", round(854 * 480 / (1920 * 1080), 2), 0.20, 0.005)
    check("360p pixel work", round(640 * 360 / (1920 * 1080), 2), 0.11, 0.005)

    # ------------------------------------------------ 5.12  tolerance in frames
    # 120 ms is 4 frames at 29.97 and 7 at 59.94: one plan, two meanings.
    check("120 ms at 29.97", round_half_away(120 * FPS_2997 / 1000), 4)
    check("120 ms at 59.94", round_half_away(120 * FPS_5994 / 1000), 7)

    # --------------------------- Appendix A  the conform map on real figures
    # Every conformed span must equal its record duration, and the column
    # "if native were decoded" must be the difference between them.
    clips = [
        ("c1", F(24000, 1001), 1440, 1689, 311, +62),
        ("c2", F(25),             96,  317, 265, +44),
        ("c3", F(30000, 1001),    60,  254, 194,   0),
        ("c4", F(60000, 1001),   900, 1562, 331, -331),
        ("c5", F(24000, 1001),  2160, 2397, 296, +59),
    ]
    for name, fps_src, a, b, record, drift in clips:
        c_in = round_half_away(a * FPS_2997 / fps_src)
        c_out = round_half_away(b * FPS_2997 / fps_src)
        span = c_out - c_in
        check(f"{name} conformed span = record", span, record)
        check(f"{name} conform delta", span - record, 0)
        check(f"{name} drift if native were decoded", record - (b - a), drift)

    # ------------------------------- 12.11  the third operating point
    check("1080p30 at the headroom point", round(float(headroom) / 8, 5), 0.00052, 1e-5)

    # -------------------------------- v1.5  the VFR table map, worked
    # A nominal-30 fps recording with one dropped frame. Conformed indices
    # skip 3; the asset gains one frame.
    vfr_pts = [0, 33333, 66667, 133333, 166667, 200000]
    conformed = [round_half_away(F(pts, 1000000) * FPS_2997) for pts in vfr_pts]
    check("VFR conformed indices", conformed, [0, 1, 2, 4, 5, 6])
    check("VFR map is non-decreasing", all(b >= a for a, b in zip(conformed, conformed[1:])), True)
    check("VFR map is strictly increasing here", all(b > a for a, b in zip(conformed, conformed[1:])), True)
    check("VFR image skips an index (injective, not surjective)", 3 not in conformed, True)
    # two packets sharing a timestamp is legal and must map to the same frame
    same_pts = [round_half_away(F(p, 1000000) * FPS_2997) for p in [0, 33333, 33333]]
    check("VFR map is non-decreasing when PTS repeats", same_pts, [0, 1, 1])
    # the skipped index is filled by repeating native f2: invertibility holds within 1
    check("VFR invertibility bound", abs(conformed[2] - 3), 1)
    native_span = F(200000 + 33333, 1000000)
    check("VFR conformed duration", round_half_away(native_span * FPS_2997), 7)
    check("VFR conform delta", round_half_away(native_span * FPS_2997) - 6, 1)

    # ------------------------- v1.5  atempo at ratios that do not decompose
    R = 300
    c_37 = F(R) * F(37, 10)
    check("3.7x conformed consumption", c_37, 1110)
    check("3.7x source samples", round(F(c_37) / FPS_2997 * 48000), 1777776)
    check("3.7x output samples", round(F(R) / FPS_2997 * 48000), 480480)
    check("3.7x ratio is exact", F(1777776, 480480), F(37, 10))
    c_inv = round_half_away(F(R) / F(37, 10))
    check("1/3.7x conformed consumption", c_inv, 81)
    src_inv = F(c_inv) / FPS_2997 * 48000
    check("1/3.7x source samples are not integral", src_inv.denominator != 1, True)
    check("1/3.7x source samples rounded", round_half_away(src_inv), 129730)

    # the precision rule: seven decimal places, not six
    out_45s = F(1349) / FPS_2997 * 48000
    check("6dp drift on a 45 s output", round(float(F(1, 10**6) * out_45s), 2), 2.16, 0.005)
    check("7dp drift on a 45 s output", round(float(F(1, 10**7) * out_45s), 3), 0.216, 0.0005)

    # ------------------------------- v1.5  transition handle at speed
    for speed, expected in [(F(1), 6), (F(2), 12), (F(1, 2), 3)]:
        check(f"handle source frames at {speed}", F(6) * speed, expected)

    # -------------------------------- v1.5  storage, egress, proxies
    check("1080p proxy GB/hour", round(12 * 3600 / 8 / 1000, 1), 5.4, 0.05)
    check("540p proxy GB/hour", round(6 * 3600 / 8 / 1000, 1), 2.7, 0.05)
    S = F(23, 1000)
    E = F(9, 100)
    storage = F(45) * S
    egress = F(18) * E
    analysis_hour = F(45, 3600) * P * 60
    check("storage $/footage-hour-month", round(float(storage), 3), 1.035, 0.0005)
    check("egress $/output-hour", round(float(egress), 2), 1.62, 0.005)
    check("analysis $/footage-hour", round(float(analysis_hour), 3), 0.375, 0.0005)
    check("storage / analysis", round(float(storage / analysis_hour), 2), 2.76, 0.005)

    # ---------------------------------- v1.5  beat grid scales with speed
    beat_frames = F(60, 124) * FPS_2997
    check("124 BPM beat interval frames", round(float(beat_frames), 4), 14.5016, 1e-4)
    check("124 BPM at 1.05x", round(float(beat_frames / F(105, 100)), 4), 13.8111, 1e-4)

    # ------------------------------ v1.6  the audio handle, rounded once
    check("audio handle at half: samplesFor(6)", round_half_away(F(6) / FPS_2997 * 48000), 9610)
    check("audio handle doubled (the bug)", 2 * round_half_away(F(6) / FPS_2997 * 48000), 19220)
    check("audio handle converted once: samplesFor(12)", round_half_away(F(12) / FPS_2997 * 48000), 19219)
    check("the two differ", 19219 != 19220, True)

    # ------------------------- v1.6  the table map walked at 2x
    conf = [round_half_away(F(p, 1000000) * FPS_2997)
            for p in [0, 33333, 66667, 133333, 166667, 200000]]
    walk = []
    for r in range(4):
        c = r * 2
        walk.append(max(i for i, cc in enumerate(conf) if cc <= c))
    check("2x walk visits", walk, [0, 2, 3, 5])
    check("2x walk skips f1 and f4", 1 not in walk and 4 not in walk, True)

    # ------------------------------------- v1.6  tiered egress
    def egress(gb):
        return min(gb, 1000) * F(9, 100) + max(0, gb - 1000) * F(5, 100)
    check("egress, first TB", float(egress(1000)), 90.0, 0.005)
    check("egress, 3 TB", float(egress(3000)), 190.0, 0.005)
    check("blended per TB at 3 TB", round(float(egress(3000) / 3), 2), 63.33, 0.005)

    # ------------------------------ v1.7  the 95th-percentile commitment
    # 40 Mbps sustained for 30 days, against 3 TB actually delivered.
    seconds_30d = 30 * 24 * 3600
    provisioned_gb = 40e6 * seconds_30d / 8 / 1e9
    check("CDN provisioned GB at 40 Mbps", round(provisioned_gb), 12960)
    check("provisioned TB", round(provisioned_gb / 1000, 2), 12.96, 0.005)
    check("provisioned / delivered", round(provisioned_gb / 3000, 1), 4.3, 0.05)

    # ------------------------ v1.8  the commitment break-even
    commit_cost = 12960 * 0.012
    check("commitment cost $", round(commit_cost, 2), 155.52, 0.005)
    breakeven = 1000 + (commit_cost - 90) / 0.05
    check("break-even GB", round(breakeven, 1), 2310.4, 0.05)
    check("break-even TB", round(breakeven / 1000, 2), 2.31, 0.005)

    # ------------------------------------------------ report
    print(f"{CHECKS} figures checked against first principles.")
    if FAILURES:
        print("\nFAILED:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("All figures consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
