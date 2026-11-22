"""Chunked rendering and segment publishing (§11.5, §18).

§11.5's claim is that a render split at cut points and concatenated is
*frame-identical* to a single pass. That claim had never been tested here —
v2.8 could hash one graph and nothing else — and it is the one that decides
whether a 4K render can be resumed at all.

Splitting is only safe at a boundary no transition spans (§11.5), which is why
the split points come from the timeline rather than from a frame count.
"""
import hashlib

import renderer as R


def split_at_cuts(count, transitions=()):
    """Clip index ranges that no transition spans.

    A split at position `p` falls between clip `p-1` and clip `p`, so it is
    unsafe exactly when a transition joins that pair — the transition would be
    cut in half and rendered twice. v2.9's first version marked *both* clips of
    a transition as un-splittable, which merged the whole timeline into one
    segment and defeated the purpose.
    """
    joined = {tuple(pair) for pair in transitions}
    boundaries = [0] + [p for p in range(1, count) if (p - 1, p) not in joined] + [count]
    return [(a, b) for a, b in zip(boundaries, boundaries[1:]) if b > a]


def render_segment(graph, inputs):
    """One chunk, as raw frames."""
    return R.render_bytes(graph, inputs)


def concat(segments):
    """Raw yuv420p frames concatenate by simple join — same size, same rate."""
    return b"".join(segments)


class Publisher:
    """Content-addressed segments, so a resumed render does not redo work."""

    def __init__(self, store, tenant="tnt_a"):
        self.store = store
        self.tenant = tenant
        self.published = {}

    def key(self, asset_id, index, params):
        return f"{asset_id}:{index}:{params}"

    def publish(self, asset_id, index, params, data):
        digest = hashlib.sha256(data).hexdigest()
        self.published[self.key(asset_id, index, params)] = (digest, data)
        self.store.add_derivative(self.tenant, asset_id, "segment",
                                  len(data), f"{params}:{index}", f"mem://{digest}")
        return digest

    def fetch(self, asset_id, index, params):
        return self.published.get(self.key(asset_id, index, params))


def render_chunked(asset_id, segments, publisher, params="seg"):
    """Render the segments that are missing, reuse the ones already published.

    Returns (frames, rendered_count, reused_count). A resume is the same call
    with a publisher that already holds some segments — which is the whole of
    §18's checkpointing, without a scheduler.
    """
    out, rendered, reused = [], 0, 0
    for index, (graph, inputs) in enumerate(segments):
        cached = publisher.fetch(asset_id, index, params)
        if cached is not None:
            out.append(cached[1])
            reused += 1
            continue
        data = render_segment(graph, inputs)
        publisher.publish(asset_id, index, params, data)
        out.append(data)
        rendered += 1
    return concat(out), rendered, reused


# --------------------------------------------------------------- encoded path
NVENC = "h264_nvenc"


def has_encoder(name):
    """Is the encoder listed by this build? Necessary, not sufficient."""
    import subprocess
    result = subprocess.run([R.FFMPEG, "-hide_banner", "-encoders"],
                            capture_output=True, text=True)
    return name in result.stdout


def usable_encoder(name):
    """Does a one-frame encode actually work?

    v2.11's first guard asked only whether ffmpeg *listed* h264_nvenc, which
    it does on every build — the failure is a missing device, and it appears
    as exit code 255 halfway through a render. Listing and working are
    different questions and only the second one matters.
    """
    import subprocess
    result = subprocess.run(
        [R.FFMPEG, "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", "testsrc2=size=64x64:rate=1:duration=1", "-frames:v", "1",
         "-c:v", name, "-f", "null", "-"], capture_output=True, text=True)
    return result.returncode == 0


def encode_segment(graph, inputs, out_path, crf=18, codec="libx264"):
    """Encode one chunk to a file with a closed GOP.

    Raw-frame concatenation proves the *graph*; a customer receives a file, so
    the segments must also survive an encode and a container join. Closed GOPs
    keep a segment decodable on its own, which is what makes the join safe.
    """
    import subprocess
    out_path = str(out_path)
    cmd = [R.FFMPEG, "-y", "-loglevel", "error"]
    for path in inputs:
        cmd += ["-i", str(path)]
    cmd += ["-filter_complex", graph, "-map", "[v_out]",
            "-c:v", codec,
            "-preset", "ultrafast" if codec == "libx264" else "p4",
            "-crf" if codec == "libx264" else "-cq", str(crf),
            "-g", "48", "-keyint_min", "48", "-sc_threshold", "0",
            "-force_key_frames", "expr:gte(t,0)", out_path]
    if codec == NVENC and not usable_encoder(NVENC):
        # §12.3's whole model rests on this encoder. A machine without a device
        # must say so, not fall back to a CPU encode and report success.
        raise RuntimeError("h264_nvenc is not usable on this machine "
                           f"(listed: {has_encoder(NVENC)}, no working device)")
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except Exception as error:
        raise RuntimeError(f"encode failed with {codec}: {error}") from error
    return out_path


def concat_encoded(paths, out_path):
    """Join encoded segments at the container level, as a renderer would."""
    import subprocess
    listing = str(out_path) + ".txt"
    with open(listing, "w") as handle:
        for path in paths:
            handle.write(f"file '{path}'\n")
    subprocess.run([R.FFMPEG, "-y", "-loglevel", "error", "-f", "concat",
                    "-safe", "0", "-i", listing, "-c", "copy", str(out_path)],
                   check=True, capture_output=True)
    return out_path


def decoded(path):
    """The decoded frames of a file, for comparing what a viewer would see."""
    import subprocess
    result = subprocess.run(
        [R.FFMPEG, "-y", "-loglevel", "error", "-i", str(path),
         "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"], capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode()[-500:])
    return result.stdout


def frame_count(path):
    """Frames in a file, from a decode pass — `-i` alone does not report one."""
    import re
    import subprocess
    result = subprocess.run(
        [R.FFMPEG, "-hide_banner", "-i", str(path), "-f", "null", "-"],
        capture_output=True, text=True)
    matches = re.findall(r"frame=\s*(\d+)", result.stderr)
    return int(matches[-1]) if matches else None
