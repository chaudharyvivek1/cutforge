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
