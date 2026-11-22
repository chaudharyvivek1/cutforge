# Golden files — what each one is, and who approved it

A golden file is only as good as the review that approved it. Regenerating one is a single command, so the thing worth recording is not the graph but *why it changed*.

| File | Fixture | Approved in | Last change, and why |
|---|---|---|---|
| `appendix_a.graph` | `appendix_a_ir()` | v1.7 | v1.8 — the wipe work moved `offset=0` to `offset=0.000000`; formatting only, no filter changed |
| `overlay.graph` | `overlay_ir()` | v1.8 | v1.8 — first approval: crop then fade, in IR order |
| `captions.graph` | `captions_ir()` | v1.8 | v1.8 — first approval: font size derived from project height |
| `hdr.graph` | `hdr_ir()` | v1.8 | v1.9 — the tone-map operator now comes from the manifest rather than a constant |
| `wipe.graph` | `wipe_ir()` | v1.8 | v1.8 — first approval: `align: start` offsets the wipe by zero |
| `lut.graph` | `lut_ir()` | v1.9 | v1.9 — first approval: `lut3d` resolved by manifest id, never a path |
| `audio_mix.graph` | `audio_mix_ir()` | v1.9 | v1.9 — first approval: two tracks mixed with `amix` and normalised |
| `sdr_to_hdr.graph` | `sdr_to_hdr_ir()` | v1.9 | v1.9 — first approval: SDR source expanded onto an HLG timeline |

## The rule

Change a golden only when a compiler change is intended, and say in the commit what moved and why. If a golden changes and you cannot name the change, the compiler changed something nobody asked it to.

`tests/test_compiler_extended.py` fails if a golden file exists that this table does not list, so a new one cannot be added without a line here.
