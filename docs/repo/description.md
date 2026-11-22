# Repository description and scope

The text in this file is what the repository's GitHub description, topics and "About" section should say. It is kept here because repository metadata cannot be set by a commit, and because a description that lives only in a web form is a description nobody reviews.

## Short description (the one-line field)

> Video engine: turns a sentence of intent into a frame-accurate cut. Timeline IR, exact rational time, MCP tool layer, 4K60 capacity and unit economics. Engine 3 of a multi-engine platform.

## Topics

```
ai-video              video-editing         ffmpeg
mcp                   video-engine          timeline-ir
system-architecture   technical-specification
otio                  hdr                   4k-video
design-document       render-pipeline       unit-economics
```

## About (the long field)

A design record and reference implementation for a **prompt-driven video engine** — the third engine in a multi-engine platform, after the 3D engine and the dubbing engine.

The engine takes a declared intent and a set of assets, plans an edit, compiles it to a filter graph, and renders it. It is an engine, not an application: no UI, no accounts, no billing, no editor chrome. It exposes a typed contract that the platform composes with other engines.

**What is in the repository**

- A 61-page technical specification at **v2.3**, in fourteen versions, each answering one external technical review.
- A **reference implementation** of the deterministic core — exact rational time, the conform map, the speed cascade, the compiler, the planner, the repair loop, the identity state machine, the export, a job service and a durable worker.
- **167 tests** that execute the document's own worked examples, compile five golden filter graphs, render frames with ffmpeg and hash them, and render the document to check its layout.
- **Three static checkers** that recompute every asserted figure, verify cross-references and version strings, and parse the published SQL migration.
- An **open findings list** for every version, which is part of the release rather than an appendix to it.

## Technology scope

**In scope.** Timeline model and time arithmetic; prompt-to-plan translation; filter-graph compilation; render orchestration and job lifecycle; media analysis; colour management including HDR; captions; audio mixing and loudness; multi-tenancy and row-level security; capacity and unit economics at 4K60.

**Deliberately out of scope.** Footage generation, speech synthesis and dubbing, 3D scene authoring, the tenancy registry and identity provider, billing, and any user interface. Those belong to other engines or to the platform.

**The stack the document specifies** — not all of it is in this repository, and §19 says which parts are:

| Layer | Specified | In this repository |
|---|---|---|
| Language | Python 3.12 core, TypeScript for overlays | Python |
| Media | ffmpeg filter graphs, NVENC, NVDEC | ffmpeg, executed in tests |
| Overlays | Remotion to an alpha intermediate | `drawtext` only |
| Database | PostgreSQL 16 with RLS, JSONB | SQLite in the worker reference |
| Interfaces | MCP tool server, REST, webhooks | stdlib HTTP service |
| Interchange | OTIO, FCPXML | OTIO-shaped JSON, round-tripped |

## The five claims worth checking

If you read one thing, check these — each is falsifiable in this repository:

1. Every cut lands on the requested frame at any rate (§5) — `tests/test_conformance.py`.
2. The renderer decodes conformed frames, not native ones (§5.9) — the Appendix A conform table.
3. A filter graph the compiler emits actually renders (§19.1) — `tests/golden/frame_hashes.json`.
4. A hold expires to failed, never to delivered (§8.5) — `tests/test_identity.py`, `tests/test_service.py`.
5. Every asserted figure is computed, not typed (§19.1) — `build/check_figures.py`, 91 assertions.

## Status

Pre-implementation for everything outside the deterministic core. The specification is implementation-ready for P0 on contracts; performance figures are targets, and §2.2 marks every one that is unvalidated.

All rights reserved — see [LICENSE](../../LICENSE).
