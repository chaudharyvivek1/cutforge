# Changelog

All versions of the specification are full standalone documents, not patches. A reader can open any one of them and understand the whole system; the changelog records what each version changed and why.

The change basis is always an external technical review. Every version carries a §0 table mapping each finding to the section that resolves it, and that table is the authority for what a version claims.

---

## v1.4 — 22 November 2026

**Basis:** fourth technical review. Verdict: the architecture is settled; what remained was a boundary, not a design.
**Theme:** the frame-domain boundary. Every finding was two true statements that had never been introduced to each other.

| Finding | Resolved by |
|---|---|
| No conform map between native and conformed frames — §5.3 says the renderer only decodes conformed frames, §5.6 answers in native frames, nothing joined them | §5.9: a total, monotone, stored map per asset; the compiler consumes conformed indices only; Appendix A works all five clips through it |
| Speed computed in the wrong domain — conforming §5.6's answer double-rounds 501 native into 601 against a correct 600 | §5.9.3: native-space arithmetic for reporting and bounds, `C = R × s` in conformed space for the render path, rounded once |
| Speed said nothing about audio | §5.11: `speed.audio` with atempo as default, the cascade rule outside 0.5–2.0, asserted sample counts |
| Captions and markers never remapped | §5.10: one affine source-to-record transform per clip, cues stored in record time, mapped word position as the acceptance test |
| Tolerances expressed in frames | §5.12: authored in milliseconds or beats, converted once at compile time; §7.2's plan DSL follows |
| The native-duration invariant guarded a path that does not exist | §6.5: both bounds, native for authoring and conformed for rendering, plus a required conform map version per clip |
| “Every op has an inverse” was false for `remove_clip`, `trim` and `snap_to_beat` | §6.6: an inverse is a function of (base revision, op), materialised at apply time and stored; `snap_to_beat` is expanded before apply_ops |
| `speed_curve` was in the effect enum but not in the compiler | §6.4 removes it and states the rule: an enum value is a promise the compiler keeps |
| Capacity and cost disagreed by 1.85× — 2.77 streams per L4 against one job owning the card | §12.11 states three operating points; §20 adopts the headroom point at $0.00417 and keeps the dedicated figure as the tail case |
| Erasure did not propagate to caches, index entries or delivered renders | §16.6: tombstone, cache invalidation, index removal, render quarantine, erasure log, and retention flagged as a legal decision |
| A held job had no column for its deadline | §13.3: `hold_question` and `hold_deadline` with a CHECK binding them to `awaiting_input` |
| Assets carried no upstream provenance | §6.8: `origin: {engine, job_id, version, params_hash}` on the asset and in the render manifest |

Also in this version: the markdown becomes the source and the `.docx` is built from it, so a change is reviewed as text and shipped as a document. `build/check_figures.py` grew from 32 to 48 assertions, including Appendix A's five clips at four rates.

**Still open after v1.4:** eight findings, in `docs/reviews/v1.5-candidates.md`. Three of them were created by v1.4's own resolutions.

---

## v1.3 — 19 November 2026

**Basis:** third technical review. Verdict: architecture approved, "complete P0 readiness" withheld.
**Theme:** contracts and evidence. No new architecture was added.

| Finding | Resolved by |
|---|---|
| Multi-track duration contradicted itself — `max(trackEnd)` and `primaryDuration == duration_frames` cannot both hold when a music bed runs past the video | §6.2 separates three quantities: `track_end_frames`, `content_duration_frames`, `render_duration_frames` |
| BigInt had no JSON contract — internal BigInt, JSON integer and `JSON.parse` number were three incompatible representations | §5.1 canonical wire format: rates as decimal strings, frame indices bounded by 2^53−1 and asserted at parse |
| Audio was described as exact — 2,160,558 is rounded from 2,160,558.4 | §5.5 states the rounding policy and stops claiming exactness; the invariant moves to the mixed output bus |
| Migration incomplete — `sequences`, `asset_derivatives`, `analysis_artifacts`, `ops_log`, `music_licences`, `audit_log`, `webhook_endpoints` were referenced but never created | §13.3 complete executable migration: 16 tables in dependency order, parser-checked for forward references |
| `renders.revision` was a bare integer, so a render could reference a revision that did not exist | §13.3 composite FK plus `UNIQUE (tenant_id, sequence_id, revision)` |
| Duplicate constraints — some `UNIQUE (tenant_id, id)` appeared inline and again as `ALTER TABLE` | §13.3 consolidates every constraint inline |
| `trim` required a full range while the example sent only `source.out` | Appendix B.1 splits the type: `opTrim` takes a partial range |
| Effect vocabulary drifted — IR used `fade_in`/`fade_out`, the tool schema used `fade` | §6.4 and Appendix B.1 share one enum; the machine-readable file is authoritative |
| `additionalProperties` claimed but not applied | Every input and output schema sets it at every level |
| P010 frame sizes wrong — 2 bytes/pixel instead of 3 | §12.1 corrected: 4K 24.88 MB, 1080p 6.22 MB, 8K 99.53 MB; 4K60 bandwidth 3.98 → 5.97 GB/s |
| NVENC figures presented as established vendor specifications | §12.3 adds an evidence-status table separating specification, estimate, assumption and target |
| Preview cost understated — 0.11× ignored that a 480p preview still decodes 1080p | §12.5 recomputes at 0.60×, or 0.22× with a dedicated 540p preview proxy, which is now required |
| RLS threat model undocumented — `current_setting('app.tenant_id')` is settable by any role that can run SQL | §14.2 documents the trust boundary, injection path, pooled-connection leakage and four containing controls |
| Missing endpoints — `answer`, `cancel`, `delete`, upload completion described but not routed | §15.2 adds all four, with the multipart completion flow |
| Tone-map example conflated HLG and PQ | §12.6 gives two separately tested chains with explicit primaries, transfer and matrix |
| Worked example mixed planned and post-roll positions, and used one source rate for a mixed-rate manifest | §A shows planned and final midpoints side by side and five clips at four native rates |
| Reproducibility under-specified — "same manifest, same bytes" ignored mux metadata | §11.6 defines determinism as same manifest and same GPU/driver, with `-bitexact` and metadata stripping; cross-GPU bit-identity is explicitly not promised |

**Still open after v1.3:** ten findings, recorded in `docs/reviews/v1.4-candidates.md`.

---

## v1.2 — earlier

**Basis:** second technical review. Verdict: much better, not yet executable.
**Theme:** contract-level defects that survive review and surface as bugs in week six.

Resolved: the speed formula ignored rate mismatch (`round(R × s)` assumed source and project rates were identical, so a 25 fps clip on a 29.97 timeline consumed the wrong number of frames); the audio sample count contradicted itself between §5.5 and Appendix A; exactness was claimed while the type signatures used JavaScript numbers; sequence duration ignored parallel tracks; gaps existed in the object model but not the schema; `cut` sat in the transition enum while transitions required `frames ≥ 1`; foreign keys did not carry the tenant, so a row in tenant A could reference an asset in tenant B; `citext` was used without being created; RLS was shown on one table out of fifteen; the MCP op schema omitted most fields the examples used; `would_be_revision` and `new_revision` named the same field differently; the tool count was ambiguously seventeen, eighteen or nineteen; tenancy was scheduled for P4 while the requirement demanded P1; phase naming was inconsistent; an identity constraint could fail silently; identity had no accuracy criteria; the chunked-audio crossfade was verified only against video frames; the renderer was not reproducible from the filter graph alone; the preview was described as pixel-identical to the final; `plan_url` had no endpoint; the webhook policy contradicted itself; Appendix A printed a literal `undefined`; and the cost headline mixed recurring and first-edit cost.

Added: §12, the 4K60 capacity model — proxy strategy, HDR pipeline, and unit economics with arithmetic rather than adjectives.

---

## v1.1 — earlier

**Basis:** first technical review. Verdict: sound architecture, not implementation-ready.
**Theme:** making the design specific enough to build.

Resolved four classes of problem: arithmetic in the time model, schema that did not match the object model, tenancy described rather than enforced, and prose that promised properties the code could not have. Added the time and frame model, the full IR schema, database design, API contracts, enforced multi-tenancy with row-level security, and the recovery and cancellation model.

---

## v1.0 — earlier

**Basis:** first draft.
**Theme:** the architecture.

Established the five decisions the specification has carried since: a canonical timeline IR; three-stage separation of plan, compile and render; tools over free text; content-addressed, per-tenant analysis caching; and an IR independent of everything downstream. Chose the engine: an ffmpeg filter graph driven by a compiler, with Remotion scoped to motion graphics and OTIO for professional handoff.
