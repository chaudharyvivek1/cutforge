"""Synthetic assets, so the fixtures can be rendered rather than described.

v2.0's render test hashed two graphs written as string literals. That proves
*a* graph renders identically; it says nothing about the graph the compiler
emits, because a compiler bug that produces a plausible wrong graph passes
both checks. Generating assets lets the fixtures be compiled *and* rendered,
so the golden graph and the golden hash describe the same artefact.

Everything is synthetic and seeded: no media in the repository, the same bytes
on every machine.
"""
import subprocess
from fractions import Fraction as F
from pathlib import Path

import renderer as R


def video(path, frames, fps, size="320x180", pattern="testsrc2", vf=None):
    """A clip of exactly `frames` frames at `fps`, animated by construction.

    `vf` distinguishes assets that share a pattern: two clips that look alike
    would hash alike if the compiler swapped their inputs, which is a bug a
    hash cannot catch if the fixtures are interchangeable.
    """
    rate = float(fps)
    seconds = float(F(frames) / F(fps))
    cmd = [R.FFMPEG, "-y", "-loglevel", "error",
           "-f", "lavfi", "-i", f"{pattern}=size={size}:rate={rate}:duration={seconds:.6f}"]
    if vf:
        cmd += ["-vf", vf]
    cmd += ["-frames:v", str(frames), "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", str(path)]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


def audio(path, seconds=6, hz=48000, tone=440):
    """A sine tone, for the audio bus fixtures."""
    subprocess.run([R.FFMPEG, "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"sine=frequency={tone}:sample_rate={hz}:duration={seconds}",
                    "-c:a", "pcm_s16le", str(path)], check=True, capture_output=True)
    return path


# Appendix A's four assets, **already conformed** to the project rate.
#
# This is not a shortcut, it is the model: §5.9.2 says the compiler resolves a
# native range through the conform map and hands the graph conformed indices,
# so what the graph reads is a conformed derivative at project rate. Building
# the fixtures at native rates and expecting the compiler to conform them
# would put ingest's job in the compiler and, as the first render showed,
# produce an xfade whose inputs disagree on timebase.
#
# Lengths are the largest conformed index each asset is asked for.
# Each asset gets a *different animated* pattern. Two assets sharing a pattern
# would hash identically if the compiler swapped their inputs, and a static
# pattern would hide an off-by-one trim: neither is visible to a hash that only
# proves the render completed.
APPENDIX_A = {
    "ast_a91": (3000, "testsrc2", None),                  # c5 reads 2700-2996
    "ast_b07": (400, "testsrc", None),                    # c2 reads 115-380
    "ast_c13": (300, "testsrc2", "hue=h=90"),             # c3 reads 60-254
    "ast_d22": (800, "testsrc", "hue=h=200,negate"),      # c4 reads 450-781
}
PROJECT_FPS = F(30000, 1001)


def appendix_a_assets(directory):
    """Build the four conformed sources and return them by asset id."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return {name: video(directory / f"{name}.mp4", frames, PROJECT_FPS,
                        pattern=pattern, vf=vf)
            for name, (frames, pattern, vf) in APPENDIX_A.items()}
