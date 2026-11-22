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
