"""IR to OpenTimelineIO-shaped JSON and back (§11.7, FR-10).

The export is a translation, not a rewrite, and the cheapest proof of that is
a round trip: emit the document, read it back, and compare the timeline. No
NLE and no OTIO dependency required.
"""
OTIO_VERSION = "0.17.0"


def export(ir):
    """A minimal OTIO document carrying the structure Resolve needs."""
    fps = ir["project"]["fps"]
    rate = int(fps["num"]) / int(fps["den"])
    tracks = []
    for track in ir["sequence"]["tracks"]:
        children = []
        for item in track["items"]:
            if item.get("kind") == "clip":
                children.append({
                    "OTIO_SCHEMA": "Clip.2",
                    "name": item["id"],
                    "source_range": {"start_time": item["source"]["in"] / rate,
                                     "duration": (item["record"]["out"] - item["record"]["in"]) / rate},
                    "metadata": {"asset": item["asset"],
                                 "record_in": item["record"]["in"]},
                })
            elif item.get("kind") == "gap":
                children.append({
                    "OTIO_SCHEMA": "Gap.1",
                    "source_range": {"duration": (item["record"]["out"] - item["record"]["in"]) / rate},
                })
        tracks.append({"OTIO_SCHEMA": "Track.1", "name": track["id"],
                       "kind": "Video" if track["kind"] == "video" else "Audio",
                       "children": children})
    return {
        "OTIO_SCHEMA": "Timeline.1",
        "name": ir["sequence"]["id"],
        "global_start_time": {"OTIO_SCHEMA": "RationalTime.1", "value": 0, "rate": rate},
        "tracks": {"OTIO_SCHEMA": "Stack.1", "children": tracks},
        "metadata": {"ir_schema": ir["schema"], "fps": fps},
    }


def read_back(doc):
    """Recover the structure the round-trip test compares."""
    fps = doc["metadata"]["fps"]
    rate = int(fps["num"]) / int(fps["den"])
    out = {}
    for track in doc["tracks"]["children"]:
        items = []
        for child in track["children"]:
            if child["OTIO_SCHEMA"].startswith("Clip"):
                items.append({
                    "kind": "clip",
                    "id": child["name"],
                    "asset": child["metadata"]["asset"],
                    "record_in": child["metadata"]["record_in"],
                    "frames": round(child["source_range"]["duration"] * rate),
                })
            else:
                items.append({"kind": "gap",
                              "frames": round(child["source_range"]["duration"] * rate)})
        out[track["name"]] = items
    return out
