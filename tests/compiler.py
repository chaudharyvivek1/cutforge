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

    graph = ";\n".join(lines)
    assemble = _assemble(seq, fps)
    if assemble:
        graph += ";\n" + assemble

    bus = _audio_bus(seq, fps)
    if bus:
        graph += ";\n" + bus
    return graph


def _audio_bus(seq, fps):
    """§11.1: one mixed, loudness-normalised bus, not one stream per track.

    A track with transitions is folded with `acrossfade` before the mix. That
    is §5.7's audio handle rule meeting ffmpeg for the first time in v2.3: the
    overlap is a record boundary converted to samples once, never a rounded
    half doubled.
    """
    per_track = []
    for track in seq["tracks"]:
        if track["kind"] != "audio" or track.get("enabled", True) is False:
            continue
        items = [i for i in track["items"] if i.get("kind") == "clip"]
        if not items:
            continue
        by_pair = {(t["between"][0], t["between"][1]): t
                   for t in track.get("transitions", []) or []}
        filters = []
        current = f"a_{items[0]['id']}"
        for step, (prev, nxt) in enumerate(zip(items, items[1:]), start=1):
            trans = by_pair.get((prev["id"], nxt["id"]))
            if trans:
                seconds = float(F(trans["frames"]) / fps)
                out = f"ac_{track['id']}_{step}"
                filters.append(f"[{current}][a_{nxt['id']}]acrossfade=d={seconds:.6f}[{out}]")
            else:
                out = f"am_{track['id']}_{step}"
                filters.append(f"[{current}][a_{nxt['id']}]amix=inputs=2:normalize=0[{out}]")
            current = out
        label = f"a_t_{track['id']}"
        filters.append(f"[{current}]anull[{label}]")
        per_track.append((label, filters))

    if not per_track:
        return ""
    lines = [f for _, fs in per_track for f in fs]
    labels = [l for l, _ in per_track]
    if len(labels) == 1:
        lines.append(f"[{labels[0]}]loudnorm=I=-14:TP=-1.5:LRA=11[a_mix]")
    else:
        joined = "".join(f"[{l}]" for l in labels)
        lines.append(f"{joined}amix=inputs={len(labels)}:normalize=0"
                     f":dropout_transition=0,loudnorm=I=-14:TP=-1.5:LRA=11[a_mix]")
    return ";\n".join(lines)


def _video_item(item, fps, width, height, ir):
    rid = item["id"]
    rec_in, rec_out = item["record"]["in"], item["record"]["out"]
    if item.get("kind") == "gap":
        # §6.3: an authored gap is black, not a hole
        return [f"color=c=black:s={width}x{height}:r={fps}:d={(rec_out - rec_in)}[v_{rid}]"]
    if item.get("kind") == "title":
        # §11.4: captions and titles rasterise at output resolution, never at
        # a fixed pixel size — a 1080p caption scaled to 4K is visibly soft.
        size = round(height * 0.045)
        text = item["text"].replace(":", "\\:").replace("'", "")
        return [f"color=c=black@0.0:s={width}x{height}:r={fps}:d={rec_out - rec_in},"
                f"drawtext=text='{text}':fontsize={size}:x=(w-text_w)/2:y=h*0.82[v_{rid}]"]

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

    # §12.6: colour is converted, never retagged, and the operator comes from
    # the manifest because two tone maps of the same source are different
    # pictures (§11.6).
    project_cs = ir["project"].get("color_space", "rec709")
    transfer = src.get("transfer")
    if project_cs == "rec709" and transfer in ("arib-std-b67", "smpte2084"):
        chain.extend(_tonemap(transfer, ir.get("metadata", {}).get("tonemap", {})))
    elif project_cs != "rec709" and transfer is None:
        chain.extend(_inverse_map(project_cs))

    for effect in item.get("effects", []) or []:
        chain.extend(_effect(effect, fps))

    return [f"[{_input_index(ir, item['asset'])}:v]" + ",".join(chain) + f"[v_{rid}]"]


def _tonemap(transfer, settings):
    """§12.6: linearise, compress highlights, map BT.2020 into BT.709, strip SEI.

    The operator and the reference white come from the manifest, not from a
    constant here: a render is only reproducible if the tone map it used is
    recorded (§11.6).
    """
    tin = "arib-std-b67" if transfer == "arib-std-b67" else "smpte2084"
    operator = settings.get("operator", "hable")
    peak = settings.get("peak", 100)
    desat = settings.get("desat", 0)
    return [f"zscale=tin={tin}:t=linear:npl={peak}", "format=gbrpf32le",
            "zscale=p=bt709", f"tonemap={operator}:desat={desat}",
            "zscale=t=bt709:m=bt709:r=tv", "format=yuv420p",
            "sidedata=mode=delete:type=MASTERING_DISPLAY_METADATA",
            "sidedata=mode=delete:type=CONTENT_LIGHT_LEVEL"]


def _inverse_map(project_color_space):
    """§12.6: an SDR source on an HDR timeline goes the other way.

    This is a display-referred expansion, not an inverse of a tone map: the
    scene metadata an HDR grade would carry does not exist for an SDR source,
    so the result is a plausible HDR picture rather than the original one.
    """
    if project_color_space == "rec2020-pq":
        transfer = "smpte2084"
    else:
        transfer = "arib-std-b67"
    return ["zscale=t=linear:npl=100", "format=gbrpf32le",
            f"zscale=p=bt2020:t={transfer}:m=bt2020nc:r=tv",
            "format=yuv420p10le"]


def _effect(effect, fps):
    """Only the effects the compiler implements. §6.4: an enum value is a promise."""
    kind = effect.get("type")
    if kind == "transform":
        chain = []
        if "crop" in effect:
            w, h, x, y = effect["crop"]
            chain.append(f"crop={w}:{h}:{x}:{y}")
        if "rotate" in effect:
            chain.append(f"rotate={effect['rotate']}*PI/180")
        return chain
    if kind == "lut":
        # §11.4: the creative grade sits at the end of the chain. The file is a
        # manifest reference, never a path — no tool takes a path (§9.3).
        ref = effect.get("ref", "lut_identity")
        return [f"lut3d=file={ref}.cube:interp=tetrahedral"]
    if kind in ("fade_in", "fade_out"):
        direction = "in" if kind == "fade_in" else "out"
        frames = effect.get("frames", 12)
        return [f"fade=t={direction}:st=0:d={float(F(frames) / fps):.6f}"]
    raise NotImplementedError(f"effect {kind} has no compiler implementation (§6.4)")


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


def _assemble(seq, fps):
    """Fold the primary video track into one output label.

    v2.0 emitted one xfade per transition and never joined them, so the graph
    had no `[v_out]` at all — it could not be rendered. Hand-written test
    graphs hid this for a version; the first render of the compiler's own
    output found it in a second.

    The fold is left to right: a transition joins the accumulator to the next
    clip with xfade, and a cut joins them with concat.
    """
    track = next((t for t in seq["tracks"]
                  if t["id"] == seq["primary_video_track"]), None)
    if track is None:
        return ""                      # an audio-only timeline has no picture to assemble
    clips = [i for i in track["items"] if i.get("kind") == "clip"]
    if not clips:
        return ""
    if len(clips) == 1:
        return f"[v_{clips[0]['id']}]null[v_out]"

    by_pair = {}
    for t in track.get("transitions", []) or []:
        a, b = t["between"]
        by_pair[(a, b)] = t

    lines = []
    current = f"v_{clips[0]['id']}"
    step = 0
    for prev, nxt in zip(clips, clips[1:]):
        step += 1
        target = f"v_{nxt['id']}"
        trans = by_pair.get((prev["id"], nxt["id"]))
        if trans:
            seconds = float(F(trans["frames"]) / fps)
            align = trans.get("align", "center")
            if trans.get("type") == "wipe":
                name = {"start": "wipeleft", "end": "wiperight"}.get(align, "wipeleft")
                offset = {"start": 0.0, "end": seconds / 2, "center": seconds / 4}[align]
            else:
                name = "fade"
                offset = 0.0
            out = f"xf_{step}"
            lines.append(f"[{current}][{target}]xfade=transition={name}"
                         f":duration={seconds:.6f}:offset={offset:.6f}[{out}]")
        else:
            out = f"cc_{step}"
            lines.append(f"[{current}][{target}]concat=n=2:v=1:a=0[{out}]")
        current = out
    lines.append(f"[{current}]null[v_out]")
    return ";\n".join(lines)


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


# --------------------------------------------------------------- fixtures
def _base_ir():
    return appendix_a_ir()


def overlay_ir():
    """A logo overlay with a transform effect, and a fade in."""
    ir = _base_ir()
    clip = ir["sequence"]["tracks"][0]["items"][0]
    clip["effects"] = [{"type": "transform", "crop": [960, 540, 0, 0]},
                       {"type": "fade_in", "frames": 12}]
    return ir


def captions_ir():
    """A title item on the primary track, rasterised at output resolution."""
    ir = _base_ir()
    ir["sequence"]["tracks"][0]["items"].insert(
        0, {"kind": "title", "id": "t1", "text": "Made in India",
            "record": {"in": 0, "out": 48}})
    return ir


def hdr_ir():
    """An HLG source on an SDR timeline: tone-mapped, never retagged."""
    ir = _base_ir()
    ir["sequence"]["tracks"][0]["items"][0]["source"]["transfer"] = "arib-std-b67"
    return ir


def wipe_ir():
    """A wipe aligned to the start of the overlap rather than centred."""
    ir = _base_ir()
    ir["sequence"]["tracks"][0]["transitions"][0] = {
        "between": ["c1", "c2"], "type": "wipe", "frames": 12, "align": "start"}
    return ir


def lut_ir():
    """A creative LUT at the end of the chain, referenced by manifest id."""
    ir = _base_ir()
    ir["sequence"]["tracks"][0]["items"][0]["effects"] = [
        {"type": "lut", "ref": "lut_warm_07"}]
    return ir


def audio_mix_ir():
    """A music bed and dialogue: one mixed, normalised bus, not two streams."""
    ir = _base_ir()
    ir["sequence"]["tracks"].append({
        "id": "A1", "kind": "audio",
        "items": [{"kind": "clip", "id": "a1", "asset": "ast_b07",
                   "source": {"in_sample": 0, "out_sample": 480480},
                   "record": {"in": 0, "out": 300}}]})
    ir["sequence"]["tracks"].append({
        "id": "A2", "kind": "audio",
        "items": [{"kind": "clip", "id": "a2", "asset": "ast_c13",
                   "source": {"in_sample": 0, "out_sample": 480480},
                   "record": {"in": 0, "out": 300}}]})
    return ir


def sdr_to_hdr_ir():
    """An SDR source on an HDR timeline: expanded, and said to be an expansion."""
    ir = _base_ir()
    ir["project"]["color_space"] = "rec2020-hlg"
    return ir


def audio_only_ir():
    """Two audio tracks and no picture, so the bus can be rendered alone.

    Rendering the full graph from audio-only inputs fails: ffmpeg still tries
    to build the video chains, which reference streams that do not exist. A
    fixture with no picture is the honest way to test the mix.
    """
    return {
        "schema": "timeline/1.9",
        "project": {"id": "prj_audio", "fps": {"num": "30000", "den": "1001"},
                    "resolution": [180, 320], "color_space": "rec709"},
        "sequence": {
            "id": "seq_audio", "primary_video_track": "V1",
            "content_duration_frames": 300, "render_duration_frames": 300,
            "tracks": [
                {"id": "A1", "kind": "audio", "items": [
                    {"kind": "clip", "id": "a1", "asset": "mus_01",
                     "source": {"in_sample": 0, "out_sample": 480480},
                     "record": {"in": 0, "out": 300}}]},
                {"id": "A2", "kind": "audio", "items": [
                    {"kind": "clip", "id": "a2", "asset": "dlg_02",
                     "source": {"in_sample": 0, "out_sample": 480480},
                     "record": {"in": 0, "out": 300}}]},
            ],
        },
        "metadata": {"assets": [{"id": "mus_01"}, {"id": "dlg_02"}]},
    }


def audio_transition_ir():
    """Two audio clips on one track, joined by a dissolve.

    §5.7's audio handle rule — a record boundary converted to samples once —
    has never met ffmpeg. This is the fixture that makes it do so.
    """
    return {
        "schema": "timeline/1.9",
        "project": {"id": "prj_xfade", "fps": {"num": "30000", "den": "1001"},
                    "resolution": [180, 320], "color_space": "rec709"},
        "sequence": {
            "id": "seq_xfade", "primary_video_track": "V1",
            "content_duration_frames": 588, "render_duration_frames": 588,
            "tracks": [
                {"id": "A1", "kind": "audio",
                 "items": [
                     {"kind": "clip", "id": "a1", "asset": "mus_01",
                      "source": {"in_sample": 0, "out_sample": 480480},
                      "record": {"in": 0, "out": 300}},
                     {"kind": "clip", "id": "a2", "asset": "dlg_02",
                      "source": {"in_sample": 0, "out_sample": 480480},
                      "record": {"in": 288, "out": 588}},
                 ],
                 "transitions": [{"between": ["a1", "a2"], "type": "dissolve", "frames": 12}]},
            ],
        },
        "metadata": {"assets": [{"id": "mus_01"}, {"id": "dlg_02"}]},
    }
