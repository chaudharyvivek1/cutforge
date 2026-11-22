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


def video(path, frames, fps, size="320x180", pattern="testsrc2"):
    """A clip of exactly `frames` frames at `fps`."""
    rate = float(fps)
    seconds = float(F(frames) / F(fps))
    subprocess.run([R.FFMPEG, "-y", "-loglevel", "error",
                    "-f", "lavfi",
                    "-i", f"{pattern}=size={size}:rate={rate}:duration={seconds:.6f}",
                    "-frames:v", str(frames), "-pix_fmt", "yuv420p",
                    "-c:v", "libx264", "-preset", "ultrafast", str(path)],
                   check=True, capture_output=True)
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
APPENDIX_A = {
    "ast_a91": (3000, "testsrc2"),   # c5 reads 2700-2996
    "ast_b07": (400, "smptebars"),   # c2 reads 115-380
    "ast_c13": (300, "testsrc2"),    # c3 reads 60-254
    "ast_d22": (800, "smptebars"),   # c4 reads 450-781
}
PROJECT_FPS = F(30000, 1001)


def appendix_a_assets(directory):
    """Build the four conformed sources and return them by asset id."""
    directory = Path(directory)
    return {name: video(directory / f"{name}.mp4", frames, PROJECT_FPS, pattern=pattern)
            for name, (frames, pattern) in APPENDIX_A.items()}
