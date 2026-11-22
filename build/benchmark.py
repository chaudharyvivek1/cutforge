#!/usr/bin/env python3
"""Render the §12.9 matrix and record throughput beside the hardware.

A throughput figure without its GPU, driver and ffmpeg build is a rumour, so
every row carries all three. Usage:

    python build/benchmark.py docs/benchmarks
"""
import json
import platform
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
import renderer as R  # noqa: E402


def gpu_name():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version",
                              "--format=csv,noheader"], capture_output=True, text=True).stdout
        return out.strip().split(", ")
    except FileNotFoundError:
        return ["unknown", "unknown"]


def measure(size, preset, seconds=10, rate=60):
    """One row: a synthetic source, encoded, timed."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "src.mp4"
        subprocess.run([R.FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", f"testsrc2=size={size}:rate={rate}:duration={seconds}",
                        "-c:v", "libx264", "-preset", "ultrafast", str(src)], check=True)
        out = Path(tmp) / "out.mp4"
        start = time.monotonic()
        subprocess.run([R.FFMPEG, "-y", "-loglevel", "error", "-i", str(src),
                        "-c:v", "h264_nvenc", "-preset", preset, str(out)], check=True)
        elapsed = time.monotonic() - start
    frames = seconds * rate
    return {"size": size, "preset": preset, "frames": frames,
            "seconds": round(elapsed, 3),
            "realtime_factor": round(frames / rate / elapsed, 3)}


def main(out_dir="docs/benchmarks"):
    name, driver = gpu_name()
    rows = [measure("1920x1080", "p4"), measure("3840x2160", "p4"),
            measure("3840x2160", "p1")]
    record = {"gpu": name, "driver": driver, "ffmpeg": R.version(),
              "platform": platform.platform(), "date": str(date.today()),
              "rows": rows}
    out = Path(out_dir) / f"{record['date']}-{name.replace(' ', '-').lower()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
