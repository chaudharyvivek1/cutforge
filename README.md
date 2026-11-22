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

## Repository documents

| Document | Answers |
|---|---|
| [`ROADMAP.md`](ROADMAP.md) | Where the project stands, what is left, and how long the remainder plausibly takes |
| [`PADDING-AUDIT.md`](PADDING-AUDIT.md) | How much of twenty-seven versions was work, and how much was ritual — measured |
| [`RELEASES.md`](RELEASES.md) | Every version, its date, its basis, and what a release means here |
| [`docs/repo/description.md`](docs/repo/description.md) | The repository's own description, topics, scope and the five claims worth checking |
| [`docs/repo/ABOUT.md`](docs/repo/ABOUT.md) | Paste-ready About panel text — the field cannot be set by a commit |
| [`LICENSE`](LICENSE) | Terms — all rights reserved |
| [`CHANGELOG.md`](CHANGELOG.md) | What each version changed and why |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How a version is cut |
| [`docs/README.md`](docs/README.md) | The documentation index |

## Repository map

```
README.md                                    what this is, what it refuses to be, how to read it
docs/
  README.md                                  index: every document and who should read it
  worklog.md                                 how the repo was built, step by step, and what is open
  spec/
    AI_Video_Editor_Architecture_v2.17.docx  canonical artefact of record
    v2.17.md                                 source of record, from which the .docx is built
    figures/                                 figures extracted from the document
  engine/
    01-platform-map.md                       where this engine sits, and what it talks to
    02-engine-contract.md                    the interface the platform may depend on
  reviews/
    v2.18-candidates.md                      open findings the next version must close
archive/                                     v1.0 through v2.16, superseded
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

**A day, to build against it.** The whole of §13 (data model), §14 (multi-tenancy), §15 (API) and Appendix B (tool schemas), plus `docs/reviews/v2.18-candidates.md`. The candidates list is where the specification is still soft, and it is deliberately kept separate so that the spec never claims more than it has earned.

## Version history

| Version | Change basis | What it fixed |
|---|---|---|
| v1.0 | First draft | The architecture: IR, three stages, tool layer, engine choice |
| v1.1 | First technical review | Time model, IR schema, database design, API and tool contracts, enforced multi-tenancy |
| v1.2 | Second technical review | Mixed-rate speed arithmetic, multi-track duration, composite tenant keys, 4K60 capacity model |
| v1.3 | Third technical review | Executable contracts: BigInt wire format, complete migration, P010 figures, preview cost, RLS threat model, endpoints |
| v1.4 | Fourth technical review | The conform map, speed that carries its audio, remapped captions, reconciled unit economics, erasure propagation |
| v1.5 | Fifth technical review | The edge cases: VFR proved, atempo to the sample, transition handles at speed, tempo grids that scale, erasure release, storage and egress costed |
| v1.6 | Sixth technical review | The rules executed: a 29-test conformance suite, audio handles to the sample, the VFR map under speed, one duration field instead of two |
| v1.7 | Seventh technical review | The translation proved: a reference compiler under golden files, the VFR threshold tested either side, the erasure schema, and a static check on the migration |
| v1.8 | Eighth technical review | The artefact tested: five golden graphs, a byte-reproducible build, a round-trip test and a rendered-page check |
| v1.9 | Ninth technical review | The implementation caught up: LUTs, colour in both directions, a mixed audio bus, and goldens that record why they changed |
| v2.0 | Tenth technical review | The first version that produces frames: a renderer under frame hashes, a template planner, the identity state machine and an OTIO round trip |
| v2.1 | Eleventh technical review | The engine runs: a job service with a hold and a cancellation, the repair loop, and the compiler's own fixtures rendered |
| v2.2 | Twelfth technical review | The engine survives: a job that outlives its worker, a repair band closed by a real shortfall, and a corpus contract |
| v2.3 | Thirteenth technical review | The engine stops: a poison job quarantined, an acrossfade measured to the sample, and one state machine instead of two |
| v2.4 | Fourteenth technical review | The queue behaves: fairness across tenants, backoff with jitter, and a schema that matches the code |
| v2.5 | Fifteenth technical review | The surface is defended: authorisation from a token, Prometheus metrics, and signed webhooks |
| v2.6 | Sixteenth technical review | The credential has a life: expiry, rotation, revocation, rate limits and delivery retry |
| v2.7 | Seventeenth technical review | State is shared: the dispatcher posts, revocation and buckets live in the store |
| v2.8 | Eighteenth technical review | Assets exist: probe, deduplicate, proxy, conform with its map; shots detected |
| v2.9 | Nineteenth technical review | The render resumes: chunked equals single-pass, segments published, VFR refused |
| v2.10 | Twentieth technical review | The file survives the join: closed-GOP segments, a provider adapter, segment expiry |
| v2.11 | Twenty-first technical review | The model has a seam: two passes behind one interface, an absent GPU refused, retention policy |
| v2.12 | Twenty-second technical review | Quality is a number: a rubric, a bounded hook, a worker loop, a split suite |
| v2.13 | Twenty-third technical review | The rubric is calibrated against labels it was not tuned on; repair consults quality |
| v2.14 | Twenty-fourth technical review | A calibration set that disagrees, and a quality gate in the service |
| v2.15 | Twenty-fifth technical review | A blind judge, one shared rule, and a gate that can refuse |
| v2.16 | Twenty-sixth technical review | A second judge of a different shape, and a coverage measurement |
| v2.17 | Twenty-seventh technical review | The slideshow only the shape judge sees; a padding audit |
| v2.18 | *Not started* | The five open findings in `docs/reviews/v2.18-candidates.md` — four are purchases, and a version would close nothing |

Each version is a full standalone specification, not a patch. A reader should be able to open any one of them and understand the whole system.

## Status

The architecture is settled and has survived three reviews without a structural change. What remains is contract work: v1.3 is P0-ready on contracts, and every performance figure is still a target with a measurement plan rather than a measured result. `build/check_figures.py` recomputes the arithmetic the document asserts, so a figure that stops being true fails the build rather than aging quietly.

Nothing here is legal advice. §16 covers biometric processing, consent and erasure, and §16.3 says explicitly that counsel must review the consent flow and retention schedule before identity matching ships.

## Building and checking

```bash
python build/check_figures.py        # recompute every asserted figure
python build/check_consistency.py    # versions, enums, counts, numbering
python build/check_sql.py            # the migration: tenant keys and RLS coverage
python -m unittest discover -s tests -t tests   # execute the worked examples, including the golden graph
python build/build_docx.py docs/spec/v1.5.md \
    docs/spec/AI_Video_Editor_Architecture_v1.5.docx docs/spec   # build the document
```

From v1.4 the markdown is the **source** and the `.docx` is built from it by `build/build_docx.py`, so a change is reviewed as text and shipped as a document. `build/extract_spec.py` runs the other way, and the round trip is checked: extracting the built `.docx` and re-running the figure check must pass on the extracted text. Earlier versions were authored in Word, which is why their markdown is generated rather than authored.

## Licence

All rights reserved. This repository is public for review and reference; it is not an open-source release.
