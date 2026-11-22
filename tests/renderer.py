"""Render a compiled graph and hash the decoded frames.

This is the layer the repository was missing: every other check proves a
string, and a filter graph can be syntactically perfect and semantically
wrong. Here the graph is executed and the output hashed.

Two decisions worth stating, because both are load-bearing.

**The hash is taken on raw frames before the encoder.** §11.8 splits
determinism into compiler determinism (raw frames at the graph sink) and
delivered-byte reproducibility (a pinned encoder). Hashing pre-encode tests
the first without inheriting the second's variance.

**The ffmpeg build is recorded with the hash.** Filter output changes between
ffmpeg majors, so a hash without the build that produced it is a number
without a meaning — which is exactly what §11.6 says about a render manifest.
A mismatch here reports the two builds rather than a mystery failure.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:                                     # pragma: no cover
    FFMPEG = shutil.which("ffmpeg")


def available():
    return FFMPEG is not None


def version():
    """The build string, so a hash can name what produced it."""
    if not available():
        return None
    out = subprocess.run([FFMPEG, "-version"], capture_output=True, text=True).stdout
    return out.split("\n")[0]


def major():
    line = version() or ""
    for token in line.split():
        if token.startswith("n") and "." in token:
            return token.split("-")[0]
        if token[:1].isdigit():
            return token.split(".")[0]
    return None


def make_source(path, seconds=2, size="320x180", rate=24, pattern="testsrc2"):
    """A synthetic source, so the fixtures need no media in the repository."""
    subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"{pattern}=size={size}:rate={rate}:duration={seconds}",
                    "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast",
                    str(path)], check=True, capture_output=True)
    return path


def render_raw(graph, inputs, size="320x180", rate=24):
    """Execute the graph and return a hash of the decoded frames."""
    cmd = [FFMPEG, "-y", "-loglevel", "error"]
    for path in inputs:
        cmd += ["-i", str(path)]
    cmd += ["-filter_complex", graph, "-map", "[v_out]",
            "-pix_fmt", "yuv420p", "-f", "rawvideo", "-"]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode()[-800:])
    return hashlib.sha256(result.stdout).hexdigest()


def load_hashes(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else {}


def save_hashes(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def render_audio(graph, inputs):
    """Hash the decoded audio, which frame hashes cannot speak for (§11.5)."""
    cmd = [FFMPEG, "-y", "-loglevel", "error"]
    for path in inputs:
        cmd += ["-i", str(path)]
    cmd += ["-filter_complex", graph, "-map", "[a_mix]",
            "-f", "s16le", "-ac", "2", "-ar", "48000", "-"]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode()[-800:])
    return hashlib.sha256(result.stdout).hexdigest()


def perceptual(graph, inputs, size="64x36"):
    """A coarse fingerprint, for when the ffmpeg build differs.

    §11.6's manifest exists so a difference can be attributed. When the build
    changes, a hash mismatch says nothing about whether the picture changed —
    so compare a downscaled, greyscaled stream instead and report the mean
    absolute difference. That is the same split §11.2 makes between identical
    decisions and non-identical pixels.
    """
    cmd = [FFMPEG, "-y", "-loglevel", "error"]
    for path in inputs:
        cmd += ["-i", str(path)]
    # the graph already produces [v_out]; rename it so it can be consumed again
    body = graph.replace("[v_out]", "[v_final]")
    cmd += ["-filter_complex", f"{body};[v_final]scale={size},format=gray[v_out]",
            "-map", "[v_out]", "-f", "rawvideo", "-"]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode()[-800:])
    return result.stdout


def mean_abs_difference(a, b):
    if len(a) != len(b):
        raise ValueError("fingerprints differ in length")
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)
