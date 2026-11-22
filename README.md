# Prompt-Driven AI Video Editor — Engine Specification

The design record for the **video engine**: the third engine in a multi-engine platform, after the 3D engine and the dubbing engine. This repository holds the technical specification, the engine boundary, the review history and the open findings that the next version must close.

This is an **engine**, not an application. There is no product surface here — no UI, no accounts, no billing, no editor chrome. The engine takes a declared intent and a set of assets, and returns a frame-accurate video plus the artefacts needed to explain and reproduce it. Everything above that line belongs to the platform.

---

## What the engine does

A user states an intent — *"cut these four clips into a 45-second vertical reel, keep the product close-up, Hindi captions, land the cuts on the beat, no footage of the CEO"* — and the engine produces a finished, frame-accurate video.

The hard problem is not calling a language model. It is making a model's output land on exact frames, deterministically, on media it has never seen, without the model ever touching a pixel. Five decisions carry the architecture, and three successive technical reviews have endorsed all five:

1. **A canonical timeline IR.** The model never emits video. It emits a declarative edit description with rational time, which a compiler turns into a render.
2. **Three-stage separation — plan, compile, render.** Each stage is independently testable and independently editable.
3. **Tools over free text.** The model selects among frame-accurate candidate identifiers; it never writes a timestamp from memory.
4. **Analysis is cached and content-addressed, per tenant.** Computed once per unique byte, reused forever.
5. **The IR is independent of everything downstream.** It knows nothing of the language model, ffmpeg or Remotion — which is why 4K60 support is a capacity problem rather than a rewrite.

The renderer is a Python core compiling the IR into an ffmpeg filter graph, with Remotion for motion-graphics overlays and OTIO/FCPXML for professional handoff.

## What the engine does not do

Stated because a platform composes engines, and a boundary that is not written down is a boundary that gets crossed.

- **It does not generate footage.** It assembles existing media. Generative synthesis is another engine's job, and the IR accepts generated clips as one more asset type.
- **It does not synthesise or translate speech.** Voice, dubbing and lip-sync belong to the dubbing engine. This engine consumes its audio tracks and timed word data.
- **It does not author 3D scenes.** Scene generation, rendering and asset production belong to the 3D engine. This engine consumes its renders as assets or as alpha overlays.
- **It does not own tenancy, identity or billing.** It enforces tenant isolation inside its own data layer — that is a security requirement, not a product one — but the tenant registry, plans and quotas live in the platform.
- **It does not decide what the edit should be.** The planner proposes, the compiler validates, the user corrects. The engine never silently substitutes.

## Repository map

```
README.md                                    what this is, what it refuses to be, how to read it
docs/
  README.md                                  index: every document and who should read it
  worklog.md                                 how the repo was built, step by step, and what is open
  spec/
    AI_Video_Editor_Architecture_v1.5.docx   canonical artefact of record
    v1.5.md                                  source of record, from which the .docx is built
    figures/                                 figures extracted from the document
  engine/
    01-platform-map.md                       where this engine sits, and what it talks to
    02-engine-contract.md                    the interface the platform may depend on
  reviews/
    v1.6-candidates.md                       open findings the next version must close
archive/                                     v1.0 through v1.4, superseded
build/
  build_docx.py                              markdown → styled .docx, house style
  extract_spec.py                            docx → markdown, for round-trip verification
  check_figures.py                           recomputes every number the spec asserts
skills/
  technical-spec-versioning/                 the routine this repo is built with
CHANGELOG.md                                 what each version changed and why
CONTRIBUTING.md                              how a version is cut, how a finding is proposed
```

## How to read this

**Fifteen minutes, for orientation.** Read §1 (executive summary) and §4 (system architecture) of the spec, then `docs/engine/01-platform-map.md`. That is enough to know whether the design is sound and where it plugs in. [`docs/README.md`](docs/README.md) carries the same guidance per role — reviewer, compiler author, platform author, spec author.

**Two hours, to review the design.** §5 (time and frame model), §6 (the IR) and §11 (the render engine). Those three sections carry almost all the risk. If the time model is wrong, every downstream section inherits the error.

**A day, to build against it.** The whole of §13 (data model), §14 (multi-tenancy), §15 (API) and Appendix B (tool schemas), plus `docs/reviews/v1.6-candidates.md`. The candidates list is where the specification is still soft, and it is deliberately kept separate so that the spec never claims more than it has earned.

## Version history

| Version | Change basis | What it fixed |
|---|---|---|
| v1.0 | First draft | The architecture: IR, three stages, tool layer, engine choice |
| v1.1 | First technical review | Time model, IR schema, database design, API and tool contracts, enforced multi-tenancy |
| v1.2 | Second technical review | Mixed-rate speed arithmetic, multi-track duration, composite tenant keys, 4K60 capacity model |
| v1.3 | Third technical review | Executable contracts: BigInt wire format, complete migration, P010 figures, preview cost, RLS threat model, endpoints |
| v1.4 | Fourth technical review | The conform map, speed that carries its audio, remapped captions, reconciled unit economics, erasure propagation |
| v1.5 | Fifth technical review | The edge cases: VFR proved, atempo to the sample, transition handles at speed, tempo grids that scale, erasure release, storage and egress costed |
| v1.6 | *Not started* | The six open findings in `docs/reviews/v1.6-candidates.md` |

Each version is a full standalone specification, not a patch. A reader should be able to open any one of them and understand the whole system.

## Status

The architecture is settled and has survived three reviews without a structural change. What remains is contract work: v1.3 is P0-ready on contracts, and every performance figure is still a target with a measurement plan rather than a measured result. `build/check_figures.py` recomputes the arithmetic the document asserts, so a figure that stops being true fails the build rather than aging quietly.

Nothing here is legal advice. §16 covers biometric processing, consent and erasure, and §16.3 says explicitly that counsel must review the consent flow and retention schedule before identity matching ships.

## Building and checking

```bash
python build/check_figures.py docs/spec/v1.5.md     # recompute every asserted figure
python build/check_consistency.py docs/spec/v1.5.md # versions, enums, counts, numbering
python build/build_docx.py docs/spec/v1.5.md \
    docs/spec/AI_Video_Editor_Architecture_v1.5.docx docs/spec   # build the document
```

From v1.4 the markdown is the **source** and the `.docx` is built from it by `build/build_docx.py`, so a change is reviewed as text and shipped as a document. `build/extract_spec.py` runs the other way, and the round trip is checked: extracting the built `.docx` and re-running the figure check must pass on the extracted text. Earlier versions were authored in Word, which is why their markdown is generated rather than authored.

## Licence

All rights reserved. This repository is public for review and reference; it is not an open-source release.
