"""Ingest: probe, deduplicate, proxy and conform (§10.1, §5.3).

This is the subsystem v2.7's list said did not exist. The compiler assumes a
conformed derivative at project rate (§5.9.2) and nothing produced one; every
downstream gap was downstream of this.

The conform map is produced here, which is the point: §5.9 says the map is a
property of the *asset*, computed once at ingest, not something the compiler
recomputes per render.
"""
import hashlib
import json
import re
import subprocess
from fractions import Fraction as F
from pathlib import Path

import renderer as R
import spec_rules as SR


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# The rates ffmpeg prints as decimals, which are roundings of these rationals.
# §5.1 forbids storing 29.97: it is a rounding of a frame rate, not a frame
# rate, and a probe that stored it would corrupt every conform downstream.
STANDARD_RATES = [
    F(24000, 1001), F(30000, 1001), F(60000, 1001), F(120000, 1001),
    F(24), F(25), F(30), F(48), F(50), F(60),
]


def snap_rate(value, tolerance=F(1, 1000)):
    """Map a decimal rate back to the rational it rounds."""
    for candidate in STANDARD_RATES:
        if abs(candidate - value) / candidate <= tolerance:
            return candidate.numerator, candidate.denominator
    nearest = F(value).limit_denominator(1001)
    return nearest.numerator, nearest.denominator


def probe(path):
    """Duration, rate, frame count, size and transfer from ffmpeg's own report.

    No ffprobe dependency: the static build ships ffmpeg, and its stderr is a
    stable enough source for the five fields ingest needs.
    """
    result = subprocess.run([R.FFMPEG, "-hide_banner", "-i", str(path)],
                            capture_output=True, text=True)
    text = result.stderr
    rate = re.search(r"(\d+)/(\d+)\s*,\s*(\S+) fps|(\d+(?:\.\d+)?) fps", text)
    if not rate:
        raise ValueError(f"cannot read a frame rate from {path}")
    if rate.group(1):
        num, den = int(rate.group(1)), int(rate.group(2))
    else:
        num, den = snap_rate(F(rate.group(4)))
    size = re.search(r"Video:.*?, (\d+)x(\d+)", text)
    frames = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", text)
    if not (size and frames):
        raise ValueError(f"cannot read size and duration from {path}")
    seconds = (int(frames.group(1)) * 3600 + int(frames.group(2)) * 60
               + float(frames.group(3)))
    transfer = "arib-std-b67" if "arib-std-b67" in text else (
        "smpte2084" if "smpte2084" in text else None)
    return {
        "fps": (num, den),
        "width": int(size.group(1)),
        "height": int(size.group(2)),
        "frames": SR.frames_for_seconds(F(str(seconds)).limit_denominator(1000),
                                        F(num, den)),
        "transfer": transfer,
        "bytes": Path(path).stat().st_size,
    }


class Ingest:
    def __init__(self, store, workdir, tenant="tnt_a", project="prj_1"):
        self.store = store
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.tenant = tenant
        self.project = project

    def register(self, path):
        """Content-addressed, deduplicated, and probed once (§10.1)."""
        info = probe(path)
        asset, created = self.store.register_asset(
            self.tenant, self.project, sha256(path), info["bytes"], info["fps"],
            info["frames"], info["width"], info["height"], info["transfer"])
        return asset, created

    def proxy(self, asset, source, height=180):
        """A low-resolution copy for editing and analysis (§11.3)."""
        out = self.workdir / f"{asset['id']}_proxy.mp4"
        subprocess.run([R.FFMPEG, "-y", "-loglevel", "error", "-i", str(source),
                        "-vf", f"scale=-2:{height}", "-c:v", "libx264",
                        "-preset", "ultrafast", "-an", str(out)], check=True)
        params = f"proxy:{height}"
        self.store.add_derivative(self.tenant, asset["id"], "proxy",
                                  out.stat().st_size, params, out)
        return out

    def conform(self, asset, source, project_fps):
        """The derivative the compiler consumes, plus the map it assumes.

        §5.9.2: the graph only ever sees conformed frames, so ingest owes it
        both the file and the map. For CFR sources the map is affine and the
        delta is computable; VFR would emit a table here instead.
        """
        project_fps = F(project_fps)
        src_fps = F(asset["fps_num"], asset["fps_den"])
        out = self.workdir / f"{asset['id']}_conform.mp4"
        subprocess.run([R.FFMPEG, "-y", "-loglevel", "error", "-i", str(source),
                        "-r", f"{project_fps.numerator}/{project_fps.denominator}",
                        "-c:v", "libx264", "-preset", "ultrafast", "-an",
                        str(out)], check=True)
        conformed_frames = SR.frames_for_seconds(
            F(asset["frames"]) / src_fps, project_fps)
        conform_map = {
            "kind": "affine",
            "source_rate": f"{src_fps.numerator}/{src_fps.denominator}",
            "project_rate": f"{project_fps.numerator}/{project_fps.denominator}",
            "native_frames": asset["frames"],
            "conformed_frames": conformed_frames,
            "delta_frames": conformed_frames - asset["frames"],
        }
        params = f"conform:{project_fps.numerator}/{project_fps.denominator}"
        self.store.add_derivative(self.tenant, asset["id"], "conform",
                                  out.stat().st_size, params, out)
        sidecar = self.workdir / f"{asset['id']}_conform_map.json"
        sidecar.write_text(json.dumps(conform_map, indent=2) + "\n")
        return out, conform_map
