# Changelog

All versions of the specification are full standalone documents, not patches. A reader can open any one of them and understand the whole system; the changelog records what each version changed and why.

The change basis is always an external technical review. Every version carries a §0 table mapping each finding to the section that resolves it, and that table is the authority for what a version claims.

---

## v2.9 — 22 November 2026

**Basis:** nineteenth technical review.
**Theme:** the render can be resumed. Chunks are byte-identical to a single pass, segments are published, and a VFR source is refused rather than mapped wrongly.

| Finding | Resolved by |
|---|---|
| The store had six tables the migration lacked | `check_sql.py` now diffs table sets; five tables published with RLS — 22 in the migration |
| Rendering at scale untested | `render_chunked()` — splits only where no transition spans, publishes segments, reuses on resume; chunked bytes equal the single pass |
| Transcription had no engine | `Transcriber` interface and `RecordedTranscriber`, with a test from transcript to remapped captions |
| Three GPU signals | Unchanged and stated |
| VFR ingest emitted an affine map | `build_conform_map()` returns a table with timestamps and **raises** without them |
| Identity corpus | Procurement |

Also: the skill `technical-spec-versioning` gained `references/version-cadence.md` — the loop distilled from nineteen versions — and `scripts/audit.py`, which runs the pre-version audit against any repository.

**Still open after v2.9:** six findings, in `docs/reviews/v2.10-candidates.md`. Two are now blocked on hardware rather than on work.

---

## v2.8 — 22 November 2026

**Basis:** eighteenth technical review.
**Theme:** assets exist. Upload is probed and deduplicated, the conform map is produced where it belongs, and shots are detected rather than assumed.

| Finding | Resolved by |
|---|---|
| No asset table and no ingest | `assets`/`asset_derivatives` tables and `ingest.Ingest` — probe, deduplicate, proxy, conform with its map beside the file |
| Storage quota unenforceable | `stored_bytes()` and `consume_storage()`, refusing rather than truncating |
| Analysis unimplemented | `analysis.shots()` from ffmpeg's scene score; `Transcript.remap()` through the conform map |
| Three GPU signals | Unchanged and stated |
| Webhook ordering unstated | §15.3 now says ordering is not guaranteed |
| No usage rollover test | A test over two periods |

Also fixed: the probe stored a decimal frame rate (`29.97` as `2997/100`), which §5.1 forbids. It now snaps to the rational the decimal rounds — the test asserts `30000/1001` comes back as itself.

**Still open after v2.8:** six findings, in `docs/reviews/v2.9-candidates.md`. The first is that the reference store has six tables the published migration does not.

---

## v2.7 — 22 November 2026

**Basis:** seventeenth technical review.
**Theme:** state is shared. A token issued in one process is visible in another, a bucket is one row rather than one dictionary, and a webhook is finally posted.

| Finding | Resolved by |
|---|---|
| Nothing sent a delivery | `dispatcher.Dispatcher` — drains, signs, posts, records; tested over a socket against a receiver that fails twice |
| Quotas covered submissions, not cost | `consume_render_minutes()` — a monthly limit that refuses without consuming; stored bytes deferred with a note |
| Revocation was per-process | `revocations` and `tokens` tables, consulted per request; survives a restart |
| The rate limiter had no shared state | `take_token()` — one row per tenant, refilled on read |
| Three GPU signals unemitted | Unchanged and stated: no GPU runner, and a constant would be worse than an absence |
| Identity corpus has no data | Unchanged: procurement |

Also added: `ROADMAP.md`, which turns the open list into an order of work with effort ranges — the first document in this repository that answers "how long".

**Still open after v2.7:** six findings, in `docs/reviews/v2.8-candidates.md`. The first is that the engine has no assets at all.

---

## v2.6 — 22 November 2026

**Basis:** sixteenth technical review.
**Theme:** the credential has a life. Tokens expire, rotate and revoke; a rate limit refuses rather than delays; a delivery that fails is retried and then dead-lettered.

| Finding | Resolved by |
|---|---|
| Tokens never expired, rotated or revoked | `expires_at`/`issued_at` on the principal, revocation per request, rotation in one step |
| No rate limiting | `ratelimit.Buckets` — a per-tenant token bucket, 429 with `Retry-After` |
| Metrics covered the store, not the worker | `cutforge_worker_heartbeat_age_seconds` from claim timestamps |
| No delivery loop, retry or dead-letter | Events on terminal state, idempotent by unique constraint; backoff; dead letter after five |
| The benchmark workflow had no runner | Manual-only, with the reason in the workflow and the docs |
| The identity corpus has no data | Unchanged, and stated as such |

Also fixed: a duplicate `__init__` in `auth.py` that silently shadowed the first — the same defect the v2.4 audit found in the planner, appearing again in the file written to fix a different problem.

**Still open after v2.6:** six findings, in `docs/reviews/v2.7-candidates.md`. The first is that nothing actually sends a webhook.

---

## v2.5 — 22 November 2026

**Basis:** fifteenth technical review.
**Theme:** the surface is defended. The tenant comes from a token rather than a header, the signals are emitted rather than described, and a webhook cannot be replayed.

| Finding | Resolved by |
|---|---|
| The service trusted a tenant header | `auth.resolve()` — tenant from a bearer token, a header may only narrow it, 403 on a non-admin override, 401 with no credential |
| §17's signals were never emitted | `metrics.render()` — five signals in Prometheus text, served at `/metrics` |
| Webhooks were specified and not implemented | HMAC over `timestamp.body`, with a five-minute replay window in both directions |
| Every render in CI is CPU | `build/benchmark.py` and a weekly GPU workflow that records throughput beside the GPU, driver and ffmpeg build |
| The model path had no reference implementation | `golden/plan_corpus.json` and a replay test; the corpus declares it is not evidence about a model |
| The identity corpus had no data | Unchanged, and stated as such — the contract is what this repository can produce before the data exists |

Also fixed: §0 had accumulated a paragraph per version and by v2.5 was explaining v1.1. It now carries the current version only, and the table below it carries the history.

**Still open after v2.5:** six findings, in `docs/reviews/v2.6-candidates.md`. The first is that tokens never expire.

---

## v2.4 — 22 November 2026

**Basis:** fourteenth technical review, plus a full audit of the code and the tests.
**Theme:** the queue behaves. Many workers without starvation, retries that back off instead of stampeding, and a schema that finally knows the state the code writes.

| Finding | Resolved by |
|---|---|
| No scheduler, concurrency or fairness | `claim()` caps a tenant at two running jobs; several workers drain a queue without double-claiming |
| No backoff or jitter | `retry_after` with exponential delay and a per-job jitter; claims respect the due time |
| `quarantined` missing from the state CHECK | Added, and `check_sql.py` now compares the DDL against the states the code sets |
| The acrossfade asserted length, not content | The decoded audio is hashed and pinned beside the count |
| Overlays scheduled for a second version | Withdrawn: §11.7 states v1 overlays are text only, and §21 drops the item |
| A synthetic corpus could be mistaken for a measurement | The fixture declares itself and `load()` refuses it without `synthetic=True` |

**The audit that preceded it** found seven more defects, all fixed: a duplicate function definition that silently shadowed the first; an orphan requeue with a zero lease that would let two workers render the same job; a test that asserted `"frame="` appeared on stderr and therefore could not fail; a `render_raw` that returned a hash where a caller needed bytes; four unused imports and parameters; a dead `expired` state with no path to it; and an ordinal map keyed on the minor digit, which called v2.4 the fourth review instead of the fourteenth.

**Still open after v2.4:** six findings, in `docs/reviews/v2.5-candidates.md`. The first is a security defect: the service trusts a tenant header.

---

## v2.3 — 22 November 2026

**Basis:** thirteenth technical review.
**Theme:** the engine stops. A poison job quarantined instead of retried forever, an audio crossfade measured to the sample, and one state machine instead of two.

| Finding | Resolved by |
|---|---|
| The worker had no retry policy | `Store.fail()` retries by failure class, gives up on permanent and budget failures, and quarantines after three identical transient ones |
| No audio transition in any fixture | `acrossfade` compiled per track; the test asserts the decoded sample count equals the frame-derived total exactly — 941,741 samples for 588 frames |
| The corpus had no data | A committed synthetic corpus exercises the loader, validator and rates end to end |
| The perceptual fallback had no golden | The Appendix A fingerprint is recorded beside its hash |
| Overlays scheduled and absent | Unchanged, and unchanged on purpose: §21 keeps it as phase three |
| The service and worker implemented one state machine twice | `JobStore` deleted; the service runs on the durable `Store` |

Also: 165 tests. The duplicate state machine was the third instance of the repository's recurring defect — two implementations of one contract, each correct, never introduced to each other — and the first whose fix was a deletion.

**Still open after v2.3:** six findings, in `docs/reviews/v2.4-candidates.md`. The sharpest is that `quarantined` is missing from the schema's state CHECK.

---

## v2.2 — 22 November 2026

**Basis:** twelfth technical review.
**Theme:** the engine survives. A job that outlives its worker, a repair band closed by a real shortfall, and a corpus contract waiting for data.

| Finding | Resolved by |
|---|---|
| The service had no queue, worker or persistence | `tests/store.py` — SQLite with an exclusive claim, per-segment checkpoints, orphan requeue and final terminal states; a restart resumes from the checkpoint |
| The render fixtures used one pattern per asset | Four distinct animated patterns, and a test that swapping two inputs changes the hash |
| The repair loop was tested against a stub planner | `plan_short()` under-delivers by a known amount; the validator now flags the repair band, and the loop closes it in two attempts |
| The Remotion path was still absent | §21 schedules it as phase three with an acceptance test, so the spec stops implying a capability and starts scheduling one |
| Identity accuracy had a harness and no corpus | `tests/corpus.py` — required fields, unique ids, distances in range, and coverage of all four conditions |
| The renderer could not say what changed across builds | `renderer.perceptual()` — a downscaled greyscale fingerprint and a mean absolute difference |

Also: 157 tests. The durability layer is the first thing in this repository that survives a process.

**Still open after v2.2:** six findings, in `docs/reviews/v2.3-candidates.md`. The sharpest is the last: the service and the worker now implement the same state machine twice.

---

## v2.1 — 22 November 2026

**Basis:** eleventh technical review.
**Theme:** the engine runs. A job service with a hold and a cancellation, the repair loop, and the compiler's own fixtures rendered rather than described.

| Finding | Resolved by |
|---|---|
| The engine had never run as a service | `tests/service.py` — HTTP job service with idempotency, tenant-scoped 404, a hold that expires to failed, an answer that resumes, a recorded degraded result, and a terminal cancellation |
| Frame hashes covered hand-written graphs | `tests/assets.py` generates conformed assets; the Appendix A graph and the audio bus are compiled and rendered. The first run found the graph had no `[v_out]` at all |
| The repair loop was unimplemented | `tests/repair.py` — repair within two attempts, `REPAIR_EXHAUSTED`, and a named budget code including on the first call |
| Identity accuracy was unmeasured | `tests/accuracy.py` computes the rates from labelled distances, and a test proves a bad threshold fails |
| The Remotion path was `drawtext` | §11.7 now states what is built and what is not, rather than implying a capability |
| Per-shot matching had no acceptance test | `tests/colour.py` implements CIE76; a two per cent gain lands under ΔE 2.0 and a twenty per cent one does not |

Also: the compiler now folds the primary track into a `[v_out]` label. Before this, it emitted one xfade per transition and never joined them, so the graph could not be opened by ffmpeg — invisible to eight golden files and found by the first real render.

**Still open after v2.1:** six findings, in `docs/reviews/v2.2-candidates.md`.

---

## v2.0 — 22 November 2026

**Basis:** tenth technical review. All six findings were verification debt: the rule was right and the reference implementation had not reached it.
**Theme:** the first version that produces frames. The major number is not a schema break — `timeline/1.9` is unchanged, and the front matter now says so.

| Finding | Resolved by |
|---|---|
| No pixels were ever produced | `tests/renderer.py` executes a graph with ffmpeg and hashes decoded frames before the encoder; `golden/frame_hashes.json` records the hash beside the ffmpeg build |
| Working-space colour and per-shot matching were not compiled | Both colour conversions compile; per-shot matching moves to the roadmap as an analysis feature with its own acceptance test |
| The planner had no reference implementation | `tests/planner.py` implements the §7.6 template planner, three golden plans, eight tests |
| The identity path had no reference implementation | `tests/identity.py` implements the hold state machine with no biometrics: uncertainty holds, and a timeout is not consent |
| OTIO export was specified and not compiled | `tests/otio_export.py` round-trips tracks, clips, durations, assets and gaps |
| The layout check ran on main only | It runs on pull requests with a cached install, and no test may skip silently |

Also: the document version and the IR version are now separate, and the tooling enforces it. Conflating them was itself a defect — a document can ship a major version without breaking a schema, and a checker that forbids it forces the wrong decision.

**Still open after v2.0:** six findings, in `docs/reviews/v2.1-candidates.md`. The largest is that the engine has never run as a service.

---

## v1.9 — 22 November 2026

**Basis:** ninth technical review. Four of the six findings were verification debt — the rule was right and the reference implementation had not reached it.
**Theme:** the implementation catching up. Colour in both directions, a mixed audio bus, and golden files that record why they changed.

| Finding | Resolved by |
|---|---|
| Colour management and LUTs were specified and not compiled | `lut` compiles to `lut3d` with the file as a manifest reference, never a path, and a golden proves the chain and its ordering. Working-space conversion remains unimplemented and is named |
| The layout check skipped silently without LibreOffice | The skip names what did not run, and the CI job fails if the layout tests skip rather than execute |
| The golden files had no reviewer | `tests/golden/README.md` records the fixture, approving version and last change per file; a test fails if a golden is undocumented |
| The break-even used one rate for committed capacity | §20.3 states it as `g* = 1000 + (provisioned × R_c − 90) / 0.05`, linear in the peak, with the worked point as one instance |
| `_tonemap` assumed an SDR project and an HLG or PQ source | Both directions implemented; operator, reference white and desaturation read from `metadata.tonemap` |
| The compiler emitted no `amix` for a multi-track bus | `amix` with `normalize=0` and `loudnorm`, skipped for a single track, with a two-track fixture and golden |

Also: 91 figure assertions, 85 tests, eight golden graphs. The audio bug is worth naming: v1.8's compiler produced one stream per audio track and never mixed them, so music and dialogue would have shipped as whichever stream the renderer took first.

**Still open after v1.9:** six findings, in `docs/reviews/v2.0-candidates.md` — all verification debt, and the first list with nothing else.

---

## v1.8 — 22 November 2026

**Basis:** eighth technical review, and the first look at the artefact rather than the source.
**Theme:** the artefact tested. A compiler under five golden files, a build that reproduces byte for byte, and a layout check that reads the rendered page.

| Finding | Resolved by |
|---|---|
| The compiler covered only Appendix A's operations | `tests/compiler.py` gains transform, fade, title, tone-map and wipe alignment; four new goldens, nine new tests. An unimplemented effect raises rather than being skipped |
| The extractor truncated code blocks for six versions | `tests/test_packaging.py` asserts fenced blocks, `CREATE TABLE` counts, captions and figure strings survive the round trip, and that the migration is not truncated |
| The document build was not checked for determinism | `build_docx.py` normalises the package — fixed timestamps, sorted parts — and a test asserts two builds are byte-identical |
| Nothing rendered the document to check its layout | A layout smoke test renders to PDF and asserts page count, no blank pages, the running header and that the migration rendered |
| The 95th-percentile example used one rate | §20.3 adds the break-even: $155.52 committed against volume pricing crossing at 2,310 GB |
| `speedTerm` allowed 16 but the cascade may not reach it | §5.11 states 16× is four atempo stages and supported; a test asserts the count and the 0.5–2.0 range |

Also: 88 figure assertions, 69 tests, five golden graphs. The migration checker caught its own header drift — the defect it was built for — before the version shipped.

**Still open after v1.8:** six findings, in `docs/reviews/v1.9-candidates.md`, four of them verification debt.

---

## v1.7 — 22 November 2026

**Basis:** seventh technical review, plus the first migration checker.
**Theme:** the translation proved. A reference compiler under golden files, a boundary tested either side, and every field the prose named now in the schema.

| Finding | Resolved by |
|---|---|
| The conformance suite covered the rules, not the compiler | `tests/compiler.py` compiles the Appendix A timeline; `tests/golden/appendix_a.graph` is the approved graph. It found a domain bug within the hour |
| The `jurisdiction` field was named and not specified | §16.6.1 specifies ISO 3166-2, a deadline table counsel owns as data, and the stricter default; §13.3 adds the `erasures` table that holds it |
| Nothing ran the tests automatically | `.github/workflows/verify.yml` runs four checks on every push and pull request, including the round trip from the `.docx` |
| The VFR fixture never sat near the 1% threshold | `near_threshold()` generates 0.9%, 1.0% and 1.1% cases; exactly 1% is not yet VFR |
| `speed` bounds lived only in the validator | §6.4 adds a `pattern` admitting 1–16 to the rate string; the validator rule stays as the backstop |
| The CDN commitment was mentioned and unpriced | §20.3 works one 95th-percentile example: 40 Mbps provisions 12.96 TB for 3 TB delivered |
| The composite-key rule was broader than its own migration | §13.2 scopes it to tables that can be referenced; `build/check_sql.py` asserts it against the published migration |
| A new table was added and the isolation loop was not | `erasures` is in both RLS loops, and the SQL check fails if any table with a `tenant_id` is missing |

Also: `build/check_sql.py` parses the migration with sqlglot and checks the tenant keys and the RLS coverage — the test §13.5 promised, run statically so it needs no database. And the extractor was fixed: a blank line inside a code block used to end it on extraction, so every listing with a blank line had been silently truncated since v1.1. The migration check found it by reporting zero tables where the source had seventeen.

**Still open after v1.7:** six findings, in `docs/reviews/v1.8-candidates.md`.

---

## v1.6 — 22 November 2026

**Basis:** sixth technical review, plus the first executable counterpart to the document.
**Theme:** the rules executed. A conformance suite now implements the deterministic rules and asserts every worked example; the six findings are what it and the review turned up.

| Finding | Resolved by |
|---|---|
| Audio transition handles on a sped clip were unstated | §5.7 gives the samples-domain rule: the handle is a record boundary converted once, never a rounded half-handle doubled. Worked: 19,219 samples, not 19,220 |
| A table-backed map under speed was walked non-uniformly | §5.9.5 fixes the order — record, ÷ speed, conformed, table, source timestamp — and works the 2× walk, which visits f0, f2, f3, f5 and skips f1 and f4 |
| `render_duration_frames` and `include_trailing_audio` overlapped | §6.2 makes the duration authoritative and the boolean derived; §6.4 and §13.3 drop the stored column; §6.5 asserts the derivation |
| Erasure deadlines were asserted without a jurisdictional basis | §16.6.1 states them as defaults and adds a `jurisdiction` field, so the deadline is a function of one |
| The VFR corpus fixture was specified and not built | `tests/vfr_fixture.py` generates it deterministically from a seed, and §5.9.4 points at it |
| Egress was priced at one flat rate | §20.3 gives two tiers and the blended rate: $90 for the first terabyte, $0.05 above, $63.33 per terabyte at three |

Also: `tests/` — a reference implementation of the deterministic rules (`spec_rules.py`) and 29 conformance tests (`test_conformance.py`), one per rule, each naming its section. The figure checker grew to 85 assertions and the consistency checker gained four: the §0 caption must name its own review, a derived field must not be stored, code fences must balance, and no script may point at a missing file.

**Still open after v1.6:** six findings, in `docs/reviews/v1.7-candidates.md`, three of them created by v1.6's own work.

---

## v1.5 — 22 November 2026

**Basis:** fifth technical review. Verdict: the rules are right; the cases at their edges are untested.
**Theme:** the edge cases. No new requirement, no new tool, no new architecture — every change makes an existing rule reachable where it had not been exercised.

| Finding | Resolved by |
|---|---|
| The VFR half of the conform map was specified but unproven | §5.9.4 works a six-frame VFR excerpt through the table map, shows the skipped conformed index and the one-frame delta, and states the property: non-decreasing, injective but not surjective, invertible within one frame |
| The atempo cascade had no awkward-ratio fixture | §5.11 states seven decimal places of precision (2.16 samples of drift at six on a 45 s output, 0.216 at seven) and works 3.7× and 1/3.7× to the sample, including a non-integral source count |
| A transition beside a sped clip had no handle rule | §5.7 measures the handle in record frames and derives the source requirement through the speed; worked at 1×, 2× and 0.5× |
| Beat snapping from a sped music bed was undefined | §5.10 stores tempo maps in source time and projects them through the full transform, so positions and intervals scale together; worked at 1.05× |
| Erasure quarantine had no owner and no release path | §16.6.1 gives three terminal outcomes with an actor and a deadline each; withdrawal is the default and lawful retention must be argued for |
| `origin.params_hash` was undefined per engine | §6.8 makes the hash opaque and namespaced: comparable only within one engine, and a cross-engine comparison is rejected with `ORIGIN_INCOMPARABLE` |
| The 540p preview proxy was required but not costed | §12.7 adds it at 2.7 GB per hour, half the 1080p proxy |
| Storage and egress were outside the cost model | §20 is retitled to compute and tokens, and §20.3 gives the arithmetic: storing an hour of 4K60 costs 2.76× analysing it, and egress is two orders of magnitude above render |

Also: the figure checker grew from 48 to 76 assertions, including the VFR mapping, the atempo sample counts and the storage ratio. One assertion caught a false claim in this version's own prose — the VFR map is strictly increasing on the example, not merely non-decreasing — which is the check doing its job on the version that added it.

**Still open after v1.5:** six findings, in `docs/reviews/v1.6-candidates.md`, two of them verification debt rather than specification defects.

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
