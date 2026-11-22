# Releases

Every version is a full standalone specification, not a patch. A reader can open any one of them and understand the whole system; this file records what shipped, when, and what changed the shape of it.

Artefacts for the current version live in [`docs/spec/`](docs/spec/). Everything earlier is in [`archive/`](archive/), unedited.

## Current

| Version | Date | Document | Tests | Figures |
|---|---|---|---|---|
| **v2.17** | 22 Nov 2026 | [`AI_Video_Editor_Architecture_v2.17.docx`](docs/spec/AI_Video_Editor_Architecture_v2.17.docx) | 365 | 91 |

## The line

| Version | Date | Basis | What changed in shape |
|---|---|---|---|
| v1.0 | 19 Nov 2026 | First draft | The architecture: IR, MCP tools, render engine, data model |
| v1.1 | 19 Nov 2026 | First technical review | Contracts made executable; the arithmetic corrected |
| v1.2 | 19 Nov 2026 | Second review | Time model, multi-track duration, composite tenant keys, §12 capacity |
| v1.3 | 19 Nov 2026 | Third review | The wire format, a migration that builds a database, P010 figures, the RLS threat model |
| v1.4 | 22 Nov 2026 | Fourth review | **The conform map** — the first structural addition since v1.0 |
| v1.5 | 22 Nov 2026 | Fifth review | Every rule v1.4 added, exercised: VFR, atempo, handles, erasure release |
| v1.6 | 22 Nov 2026 | Sixth review | A conformance suite — the document's own examples, executed |
| v1.7 | 22 Nov 2026 | Seventh review | A reference compiler under golden files; the migration checked statically |
| v1.8 | 22 Nov 2026 | Eighth review | The artefact tested: byte-reproducible build, round trip, rendered page |
| v1.9 | 22 Nov 2026 | Ninth review | The implementation caught up: LUTs, colour both ways, the audio bus |
| v2.0 | 22 Nov 2026 | Tenth review | **The first version that produces frames** — a renderer under frame hashes |
| v2.1 | 22 Nov 2026 | Eleventh review | The engine runs: a job service, the repair loop, the compiler's fixtures rendered |
| v2.2 | 22 Nov 2026 | Twelfth review | The engine survives: a durable store and a worker that resumes |
| v2.3 | 22 Nov 2026 | Thirteenth review | The engine stops: quarantine, an acrossfade to the sample, one state machine |
| v2.4 | 22 Nov 2026 | Fourteenth review | The queue behaves: fairness across tenants, backoff with jitter, and a schema that matches the code |
| v2.5 | 22 Nov 2026 | Fifteenth review | The surface is defended: authorisation from a token, metrics, and signed webhooks |
| v2.6 | 22 Nov 2026 | Sixteenth review | The credential has a life: expiry, rotation, revocation, rate limits and delivery retry |
| v2.7 | 22 Nov 2026 | Seventeenth review | State is shared: the dispatcher posts, revocation and buckets live in the store |
| v2.8 | 22 Nov 2026 | Eighteenth review | Assets exist: probe, deduplicate, proxy, conform with its map; shots detected |
| v2.9 | 22 Nov 2026 | Nineteenth review | The render resumes: chunked equals single-pass, segments published, VFR refused |
| v2.10 | 22 Nov 2026 | Twentieth review | The file survives the join: closed-GOP segments, a provider adapter, segment expiry |
| v2.11 | 22 Nov 2026 | Twenty-first review | The model has a seam: two passes behind one interface, an absent GPU refused, retention policy |
| v2.12 | 22 Nov 2026 | Twenty-second review | Quality is a number: a rubric, a bounded hook, a worker loop, a split suite |
| v2.13 | 22 Nov 2026 | Twenty-third review | The rubric is calibrated, and repair consults quality |
| v2.14 | 22 Nov 2026 | Twenty-fourth review | A calibration set that disagrees, and a quality gate in the service |
| v2.15 | 22 Nov 2026 | Twenty-fifth review | A blind judge, one shared rule, and a gate that can refuse |
| v2.16 | 22 Nov 2026 | Twenty-sixth review | A second judge of a different shape, and a coverage measurement |
| v2.17 | 22 Nov 2026 | Twenty-seventh review | The slideshow only the shape judge sees; a padding audit |

## What "release" means here

There is no binary to download and no service to call. A release is a version of the specification plus the reference implementation that proves it:

- **The document** — `docs/spec/AI_Video_Editor_Architecture_vX.Y.docx`, built from `docs/spec/vX.Y.md` by `build/build_docx.py`, byte-reproducibly.
- **The checks** — three static checkers and a test suite that must pass on the source *and* on the document extracted back out of the `.docx`.
- **The open list** — `docs/reviews/`, which says what the version does not solve. It is part of the release, not an appendix to it.

A version is not released until `python build/check_figures.py`, `check_consistency.py`, `check_sql.py` and the test suite all pass from a clean clone.

## Versioning

The **document** version and the **IR** version are separate. The document goes up with every review; the IR goes up only when the schema breaks. v2.0 was a major document release with `timeline/1.9` unchanged, and the front matter of every version states both.
