# Golden files — what each one is, and who approved it

A golden file is only as good as the review that approved it. Regenerating one is a single command, so the thing worth recording is not the graph but *why it changed*.

| File | Fixture | Approved in | Last change, and why |
|---|---|---|---|
| `appendix_a.graph` | `appendix_a_ir()` | v1.7 | v2.1 — the compiler now folds the track into `[v_out]`; before this it emitted transitions and never joined them, so the graph could not be rendered |
| `overlay.graph` | `overlay_ir()` | v1.8 | v2.1 — assembly added `[v_out]`; the filters are unchanged since v1.8. Originally: crop then fade, in IR order |
| `captions.graph` | `captions_ir()` | v1.8 | v2.1 — assembly added `[v_out]`; the filters are unchanged since v1.8. Originally: font size derived from project height |
| `hdr.graph` | `hdr_ir()` | v1.8 | v2.1 — assembly added `[v_out]`; the tone-map chain is unchanged since v1.9 |
| `wipe.graph` | `wipe_ir()` | v1.8 | v2.1 — assembly added `[v_out]`; the filters are unchanged since v1.8. Originally: `align: start` offsets the wipe by zero |
| `lut.graph` | `lut_ir()` | v1.9 | v2.1 — assembly added `[v_out]`; `lut3d` unchanged since v1.9 |
| `audio_mix.graph` | `audio_mix_ir()` | v1.9 | v2.3 — each track now folds to its own label before the bus mixes them, so a per-track crossfade has somewhere to live |
| `audio_transition.graph` | `audio_transition_ir()` | v2.3 | v2.3 — first approval: `acrossfade` between two clips on one track |
| `sdr_to_hdr.graph` | `sdr_to_hdr_ir()` | v1.9 | v2.1 — assembly added `[v_out]`; the expansion chain is unchanged |

## The rule

Change a golden only when a compiler change is intended, and say in the commit what moved and why. If a golden changes and you cannot name the change, the compiler changed something nobody asked it to.

`tests/test_compiler_extended.py` fails if a golden file exists that this table does not list, so a new one cannot be added without a line here.
