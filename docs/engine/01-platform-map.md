# 01 — The platform map: where the video engine sits

A platform built as a set of engines rather than as an application is a platform that can grow without rewriting. Each engine owns one hard problem completely, exposes a typed contract, and knows nothing about the others' internals. The platform composes them.

This document records the composition as it stands, so that the video engine's specification can be read in the right context — and so that the boundary is written down before it is crossed.

## The engine inventory

| # | Engine | Owns | Consumes | Produces |
|---|---|---|---|---|
| 1 | **3D engine** | Scene description, geometry, materials, lighting, offline rendering | Prompts, asset libraries, camera direction | Rendered clips, alpha overlays, stills, camera metadata |
| 2 | **Dubbing engine** | Translation, voice synthesis, timing, lip-sync | Video or audio, target language, voice profile | Dubbed audio tracks, timed word data, optionally a refaced video track |
| 3 | **Video engine** (this repository) | Editorial assembly: selection, cutting, timing, captions, compositing, delivery | Assets from every engine, a declared intent | A frame-accurate video, the IR, a render manifest, quality report |
| 4+ | Figure / character platform | Persistent characters, identity, appearance, voice binding | Reference media, approvals | Identity and appearance artefacts other engines address by id |

The order matters only in one direction: engines 1, 2 and 4 produce assets; engine 3 assembles them. The video engine is the only one that produces a finished timeline, which makes it the integration point for all the others — and therefore the engine whose contract must be the most conservative.

## Why engines, not features

A monolith that grows a renderer, then a dubbing feature, then a 3D scene tool acquires three schedulers, three caches, three retry policies and one database schema that all three mutate. Each addition makes the previous ones harder to reason about.

An engine boundary buys four things that a feature boundary does not:

**Independent failure.** A 3D render that takes eleven minutes and fails does not hold a video render's queue. The platform sees a failed job from an engine and a healthy one from another.

**Independent scaling.** 4K60 encoding is encode-bound; dubbing is inference-bound; 3D is memory-bound. One GPU pool sized for the average of three workloads is sized correctly for none.

**Independent versioning.** The video engine can move from IR 1.3 to 1.4 without the dubbing engine knowing. This is why the IR is versioned and why the contract in `02-engine-contract.md` is additive-only.

**A testable contract.** An engine that exposes a typed interface can be exercised by a conformance suite. A feature cannot.

## The composition, end to end

A request that uses all three engines:

```text
platform
  │
  ├─ user intent + source media
  │
  ├─▶ 3D engine        "make a 3-second animated logo sting"
  │      └─ returns asset ast_sting (ProRes 4444, alpha, 90 frames @ 30)
  │
  ├─▶ dubbing engine   "same edit, Hindi"
  │      └─ returns audio track + word timings + optional refaced V2
  │
  └─▶ video engine     intent + all assets
         ├─ plan      → Edit Plan
         ├─ compile   → Timeline IR 1.3 + filter graph
         ├─ render    → preview, then final
         └─ returns   video, IR, manifest, quality report, C2PA credential
```

The video engine never asks the 3D engine to re-render at a different frame rate, and never asks the dubbing engine to re-time a take. It **conforms** what it is given, records where it came from, and treats a mismatch as a constraint to satisfy rather than a problem to solve upstream. That rule is what keeps the composition acyclic.

## The rules of composition

Four rules, and each one exists because breaking it is the obvious thing to do.

**1. An engine's output is an asset, never a sub-job.** The video engine receives `ast_sting` as a registered asset with a checksum, not as a handle that can be asked to change. If the sting is 30 fps and the project is 29.97, the video engine conforms it and records the conform. It does not send a message back asking for 29.97, because that would make the video engine's render depend on another engine's queue.

**2. Provenance travels with the asset.** Every asset carries `origin: {engine, job_id, version, params_hash}`. The render manifest records it (§11.6 of the spec), so a disputed output can be traced to the exact 3D or dubbing job that produced each input. Without this field, a video that looks wrong because a sting was rendered with the wrong camera is indistinguishable from a video that looks wrong because it was cut badly.

**3. Timed data is converted at the boundary, not inside the engine.** The dubbing engine returns word timings in its own timebase. The video engine converts them through its conform map on entry and stores them in record time. An engine that accepts a foreign timebase and converts it lazily, in three places, will convert it three different ways.

**4. No engine reads another engine's storage.** Access is by signed URL or by an asset id resolved through the platform. A shared bucket is a shared schema, and a shared schema is a coupling that survives every attempt to remove it.

## What the platform owns, and must keep owning

The video engine enforces tenant isolation inside its own data layer — row-level security, composite foreign keys, tenant-namespaced caches. That is a security property of the engine and it is not negotiable.

But the following stay in the platform, because two engines enforcing them independently is two answers to one question:

- Tenant registry, plans, quotas, entitlements.
- User identity, roles and the mapping from user to tenant.
- Billing, metering and the price of a render.
- The global asset catalogue and cross-engine provenance graph.
- Notification, email and the product surface.

The engine exposes *what it did* — GPU-seconds, output minutes, tokens, cache hits — as a metering event. It does not decide what that costs.

## Where the next engines attach

The video engine's contract is additive-only precisely so that later engines can attach without a breaking change. The two attachments already foreseeable:

**A generative engine** producing synthesised clips. The IR already accepts any asset; a generated clip is an asset whose `origin.engine` is `generative` and whose licence field records the model and the terms. No IR change is required, which is the test of whether the abstraction was drawn at the right level.

**A music engine** producing scored tracks with a tempo map. The video engine already consumes beats for snapping; a scored track arrives with a tempo map in its metadata, and the existing `media.audio_features` path is bypassed rather than replaced.

Neither attachment needs a new tool on the MCP surface. If either did, that would be evidence that the surface was drawn around the current implementation rather than around the capability.
