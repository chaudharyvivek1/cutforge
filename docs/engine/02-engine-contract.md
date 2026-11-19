# 02 — The engine contract

The specification describes the engine's internals. This document describes its **surface**: the part the platform and the other engines are allowed to depend on. Everything in the specification that is not named here is an implementation detail and may change between minor versions.

The rule that governs the whole document: **the contract is additive-only within a major version.** A field may be added. A field may not change meaning, change type, become required, or disappear without a `/v2` path and a deprecation window.

## 1. The job envelope

Every operation the engine performs is a job. A job is the only unit of work the platform submits, and the only unit it polls.

```json
{
  "job_id": "job_2m4",
  "tenant_id": "tnt_6f1c",
  "kind": "render",
  "engine": "video",
  "engine_version": "1.3.0",
  "idempotency_key": "7c1e-9a",
  "input": { "...": "kind-specific, see §3" },
  "budget": { "deadline_s": 900, "max_calls": 40, "max_tokens": 120000 },
  "callback_url": "https://platform.internal/hooks/video",
  "created_at": "2026-11-19T09:14:03Z"
}
```

Four properties the platform may rely on:

**Idempotent by key.** The same `idempotency_key` from the same tenant returns the original job, not a second one. A retried submission cannot double-charge or double-insert.

**Bounded by budget.** A job that exceeds its deadline, call ceiling or token ceiling fails with a budget error naming which ceiling was hit. It never runs unbounded and it never fails silently.

**Cancellable at a boundary.** A cancellation is honoured at the next safe boundary — never mid-write — and reaches `cancelled` within 30 seconds or the worker is terminated and the job reconciled.

**Terminal states are final.** `succeeded`, `failed`, `cancelled` and `expired` are terminal. `awaiting_input` is not: it is a hold with a deadline, and an unanswered hold expires to `failed`, never to a delivered degraded result.

## 2. States

```text
queued ──▶ running ──▶ verifying ──▶ succeeded
   │          │  ▲          │
   │          │  └──────────┘  (repair loop, at most twice)
   │          ├──▶ awaiting_input ──▶ running      (answer received)
   │          │          └────────▶ failed         (deadline expires)
   │          └──▶ failed | cancelled
   └──▶ cancelled
```

`awaiting_input` exists because a hard constraint that cannot be resolved must block rather than degrade (spec §8.5). The deadline is stored on the job and reported on every read, so a client can render a countdown without a second call.

## 3. Input shapes

Five kinds. Each is a distinct envelope because each fails differently and each has its own budget profile.

| Kind | Input | Returns | Typical budget |
|---|---|---|---|
| `ingest` | upload reference, project id | asset id, probe facts, conform map version, derivatives | 10 min, no model calls |
| `analyse` | asset ids | shot list, transcript, embeddings, audio features, quality | 30 min, no model calls |
| `plan` | prompt, asset ids, aspect, duration target | Edit Plan, candidate evidence, tool trace | 8 s median, model-bounded |
| `render` | sequence id, revision, quality | output object, manifest, verification report | 15 min preview, 2 h final |
| `export` | sequence id, revision, target | OTIO or FCPXML document, plus flattened effects | 5 min, no render |

`render` requires a prior `plan` or a hand-authored IR. The engine will not render a sequence that has never been validated: a `render` whose revision has no passing `timeline.validate` result is rejected with `SEQUENCE_NOT_VALIDATED`, because rendering an invalid timeline spends GPU time to produce a file that will fail verification.

## 4. Output artefacts

Every output is an artefact with a type, a content hash and a provenance record. The platform stores them; the engine never assumes it is the only copy of anything user-visible.

| Artefact | Type | Guarantees |
|---|---|---|
| `video` | mp4 / mov | frame count, sample count, frame hash, PCM hash, manifest id |
| `timeline` | json | valid against `timeline/1.3.json`; immutable at a revision |
| `plan` | yaml | human-readable; re-compilable without the model |
| `manifest` | json | complete enough to reproduce the render (§11.6) |
| `report` | json | verification results, warnings, conform deltas, cache statistics |
| `captions` | ass / srt / vtt | cue boundaries in record time, within ±1 frame of word timing |

A `video` artefact is never returned without its `manifest` and `report`. A file that cannot be explained is not a deliverable; it is a bill.

## 5. Events

Push, at-least-once, signed HMAC-SHA256 over the raw body plus a timestamp. Receivers must be idempotent on `event_id`.

```json
{ "event_id": "evt_01J9F3K2", "job_id": "job_2m4", "tenant_id": "tnt_6f1c",
  "type": "job.progress", "at": "2026-11-19T09:16:41Z",
  "data": { "stage": "render", "progress": 0.62 } }
```

| Event | Emitted when |
|---|---|
| `job.accepted` | the job is durable and queued |
| `job.progress` | at most once per 2 s, monotone within a stage |
| `job.awaiting_input` | a hard constraint holds the job; carries the question and deadline |
| `job.warning` | a non-fatal deviation, e.g. a shortened transition or a conform delta |
| `job.succeeded` | terminal, carries artefact ids |
| `job.failed` | terminal, carries a machine code and an actionable sentence |
| `job.cancelled` | terminal |
| `metering.recorded` | GPU-seconds, output minutes, tokens, cache hits |

`job.progress` is throttled on purpose. A media pipeline that emits progress per frame floods a webhook receiver and turns an observability feature into an outage.

## 6. Failure contract

Errors carry a stable machine code, a message written for a human, structured details, and a request id. Three codes are contract-level and the platform may branch on them:

| Code | Meaning | Platform should |
|---|---|---|
| `CONSTRAINT_UNRESOLVED` | a hard constraint held the job and the hold expired | ask the user; resubmit with an answer |
| `BUDGET_EXCEEDED` | a deadline, call or token ceiling was hit | resubmit with a larger budget or a simpler intent |
| `VERIFICATION_FAILED` | the render completed but did not match its own IR | surface it; this is an engine bug, not a user error |

Every other code is informational. The distinction matters because these three are the only failures a retry with the same input cannot fix.

## 7. Version negotiation

```text
GET /v1/engine
{ "engine": "video", "version": "1.3.0", "ir_versions": ["1.2", "1.3"],
  "tools": 19, "mcp_protocol": "2025-06-18",
  "features": { "hdr": true, "identity": false, "overlay_remotion": true } }
```

The platform reads this once per deployment and caches it. Feature flags are how the platform discovers that identity matching is off for a tenant without probing for the error, and how a future engine advertises a capability the platform does not yet use.

The engine accepts an IR at any version it lists and upgrades it internally. It never emits an IR older than the version it was asked for.

## 8. The provenance field

One addition this repository proposes for IR 1.4, recorded here because it is a contract concern rather than an internal one.

```json
"asset": {
  "id": "ast_sting",
  "origin": { "engine": "3d", "job_id": "job_8x1", "version": "0.9.4",
              "params_hash": "sha256:..." },
  "licence": { "kind": "generated", "terms": "platform-owned" }
}
```

Without `origin`, a video that looks wrong because an upstream engine produced the wrong input is indistinguishable from a video that was cut badly, and the platform's only diagnostic is to ask the user what they expected. With it, the render manifest names the exact upstream job for every input, and a dispute resolves by inspection rather than by argument.

## 9. What the platform must not do

Four things that break the engine's guarantees, stated as prohibitions because each is convenient in the short term.

**Must not write to the timeline directly.** All mutation goes through `timeline.apply_ops`, which enforces invariants and records inverses. A direct database write produces a revision that cannot be undone and a diff that cannot be shown.

**Must not reuse a render manifest across revisions.** A manifest describes one render of one revision of one sequence. Copying it to save a render is how a deliverable ends up with the wrong audio.

**Must not assume a preview is a small final.** Edit decisions and timing are identical by contract; pixels are not, by design (spec §11.2). A platform that diffs a preview against a final will find differences and should expect to.

**Must not treat `awaiting_input` as a failure.** It is a hold with a deadline. A platform that cancels it on the first poll converts a solvable constraint into a lost job.
