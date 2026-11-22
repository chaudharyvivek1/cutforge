"""A reference compiler: Timeline IR to a filter graph.

This is the second thing the conformance suite was missing. `spec_rules.py`
proves the arithmetic; this proves the translation, which is where a spec and
an implementation diverge most quietly — a graph that runs, produces a file,
and is subtly wrong.

It covers the operations Appendix A exercises: cuts, gaps, speed, transitions
and an audio bus. It does not cover overlays, colour management or captions,
and it says so rather than pretending.

Determinism is the contract (§11.6): the same IR compiles to the same string,
byte for byte, with no timestamps, no paths and no dictionary-order artefacts.
"""
from fractions import Fraction as F

import spec_rules as R


def _rational(r):
    """§5.1: rates are string pairs on the wire; parse them to exact rationals."""
    return F(int(r["num"]), int(r["den"]))


def _track(items):
    return [i for i in items]


def compile_ir(ir):
    """Compile a timeline/1.x document to one filter_complex string.

    The output is deterministic and self-contained: every input is named by an
    index, every label is derived from the item id, and nothing depends on
    iteration order that is not explicit.
    """
    fps = _rational(ir["project"]["fps"])
    width, height = ir["project"]["resolution"]
    seq = ir["sequence"]
    lines = []
    labels = []

    for track in seq["tracks"]:
        kind = track["kind"]
        items = _track(track["items"])
        if kind == "video":
            for item in items:
                lines.extend(_video_item(item, fps, width, height, ir))
                labels.append((item["id"], item["record"]["in"]))
        elif kind == "audio":
            for item in items:
                lines.extend(_audio_item(item, fps, ir))
                labels.append((item["id"], item["record"]["in"]))

    transitions = _transitions(seq, fps)
    graph = ";\n".join(lines)
    if transitions:
        graph += ";\n" + transitions
    return graph


def _video_item(item, fps, width, height, ir):
    rid = item["id"]
    rec_in, rec_out = item["record"]["in"], item["record"]["out"]
    if item.get("kind") == "gap":
        # §6.3: an authored gap is black, not a hole
        return [f"color=c=black:s={width}x{height}:r={fps}:d={(rec_out - rec_in)}[v_{rid}]"]

    src = item["source"]
    speed = item.get("speed")
    speed = F(int(speed["num"]), int(speed["den"])) if speed else F(1)

    # §5.9.2: native source range resolved to conformed frames before any filter
    c_in = src["in"] if "in" in src else 0
    c_out = src["out"]
    if speed != 1:
        # §5.9.3: the renderer consumes the RECORD duration times speed.
        # Multiplying the source span by speed instead was the first bug this
        # file's own test caught: it conflates the two domains §5.9.3 separates.
        record_frames = rec_out - rec_in
        c_out = c_in + R.conformed_consumption(record_frames, speed)

    chain = [f"trim=start_frame={c_in}:end_frame={c_out}",
             "setpts=PTS-STARTPTS"]
    if speed != 1:
        chain.append(f"setpts=PTS/{float(speed)}")
    chain.append(f"scale={width}:{height}")
    return [f"[{_input_index(ir, item['asset'])}:v]" + ",".join(chain) + f"[v_{rid}]"]


def _audio_item(item, fps, ir):
    rid = item["id"]
    src = item["source"]
    speed = item.get("speed")
    speed = F(int(speed["num"]), int(speed["den"])) if speed else F(1)
    start = src.get("in_sample", R.samples_for(src.get("in", 0), fps))
    end = src.get("out_sample", R.samples_for(src.get("out", 0), fps))
    chain = [f"atrim=start_sample={start}:end_sample={end}", "asetpts=PTS-STARTPTS"]
    if speed != 1:
        for f in R.atempo_cascade(speed):
            chain.append(f"atempo={float(f):.7f}".rstrip("0").rstrip("."))
    return [f"[{_input_index(ir, item['asset'])}:a]" + ",".join(chain) + f"[a_{rid}]"]


def _transitions(seq, fps):
    """§5.7: a transition overlaps two clips and consumes record time."""
    out = []
    for track in seq["tracks"]:
        for t in track.get("transitions", []) or []:
            a, b = t["between"]
            frames = t["frames"]
            seconds = float(F(frames) / fps)
            out.append(f"[v_{a}][v_{b}]xfade=transition=fade:duration={seconds:.6f}"
                       f":offset=0[tr_{a}_{b}]")
    return ";\n".join(out)


def _input_index(ir, asset_id):
    """Inputs are named by the order they appear in the manifest, never by path."""
    manifest = ir.get("metadata", {}).get("assets", [])
    for i, a in enumerate(manifest):
        if a.get("id") == asset_id:
            return i
    raise KeyError(f"asset {asset_id} not in the manifest (§6.5)")


def appendix_a_ir():
    """The Appendix A timeline, as the document states it."""
    return {
        "schema": "timeline/1.6",
        "project": {"id": "prj_8f2a", "fps": {"num": "30000", "den": "1001"},
                    "resolution": [1080, 1920], "color_space": "rec709"},
        "sequence": {
            "id": "seq_reel_916", "primary_video_track": "V1",
            "content_duration_frames": 1349, "render_duration_frames": 1349,
            "tracks": [
                {"id": "V1", "kind": "video", "items": [
                    {"kind": "clip", "id": "c1", "asset": "ast_a91",
                     "source": {"in": 1440, "out": 1689},
                     "record": {"in": 0, "out": 311}},
                    {"kind": "clip", "id": "c2", "asset": "ast_b07",
                     "source": {"in": 96, "out": 317},
                     "record": {"in": 299, "out": 564}},
                    {"kind": "clip", "id": "c3", "asset": "ast_c13",
                     "source": {"in": 60, "out": 254},
                     "record": {"in": 552, "out": 746}},
                    {"kind": "clip", "id": "c4", "asset": "ast_d22",
                     "source": {"in": 900, "out": 1562},
                     "record": {"in": 734, "out": 1065}},
                    {"kind": "clip", "id": "c5", "asset": "ast_a91",
                     "source": {"in": 2160, "out": 2397},
                     "record": {"in": 1053, "out": 1349}},
                ],
                 "transitions": [
                     {"between": ["c1", "c2"], "type": "dissolve", "frames": 12},
                     {"between": ["c2", "c3"], "type": "dissolve", "frames": 12},
                     {"between": ["c3", "c4"], "type": "dissolve", "frames": 12},
                     {"between": ["c4", "c5"], "type": "dissolve", "frames": 12},
                 ]},
            ],
        },
        "metadata": {"assets": [{"id": "ast_a91"}, {"id": "ast_b07"},
                                {"id": "ast_c13"}, {"id": "ast_d22"}]},
    }
