# Roadmap

Where the project stands, what is left, and how long the remainder plausibly takes. The estimates are **ranges in focused sessions** — one session is roughly a working day of one person with the repository already loaded — and they assume the conditions in §4 hold. They are estimates, not commitments, and the two places they are most likely to be wrong are named.

---

## 1. Where it stands

The repository has two products and they are at different stages.

| | Status |
|---|---|
| **The specification** | Complete for P0 on contracts. 61 pages, seventeen reviews, no known internal contradiction. Every figure computed by a checker. |
| **The reference implementation** | Covers the deterministic core and the service surface. **231 tests.** Does not render at scale, has never run on a GPU, and has no ingest pipeline. |

The specification is what you would hand a team to build from. The reference implementation is what proves the specification is buildable — it is not the product, and the gap between them is what §3 lists.

### What is done

| Area | Status | Evidence |
|---|---|---|
| Time model, conform map, speed, audio | Done | §5, `tests/spec_rules.py`, Appendix A's five clips |
| Timeline IR and ops | Done | §6, `tests/compiler.py` |
| Filter-graph compilation | Done for cuts, gaps, transitions, speed, colour, LUTs, captions, audio | eight golden graphs, two rendered to frame hashes |
| Prompt to plan | Done for the deterministic template planner | `tests/planner.py`, three golden plans |
| Repair loop | Done | `tests/repair.py`, three named outcomes |
| Identity state machine | Done; accuracy unmeasured | `tests/identity.py` |
| Data model, migration, RLS | Done and statically checked | §13, `build/check_sql.py` |
| Multi-tenancy, auth | Done | `tests/auth.py`, token lifecycle |
| Job service, worker, scheduler | Done at reference scale | `tests/service.py`, `tests/store.py` |
| Webhooks | Done | `tests/dispatcher.py`, delivered over a socket |
| Observability | Six of nine signals | `tests/metrics.py` |

### What is not done

| Area | Missing |
|---|---|
| **Ingest** | No upload, no probing, no proxy generation, no conforming. The compiler assumes conformed assets exist. |
| **Analysis** | No shot detection, no transcription, no object tags, no face embeddings — §10 entirely. |
| **Rendering at scale** | No NVENC, no chunked render, no segment publishing. One 320×180 graph has been hashed. |
| **Model path** | No language model anywhere. The planner is templates. |
| **Overlays** | `drawtext` only. Designed titles were withdrawn in v2.4. |
| **Assets and storage** | No asset table, so no storage quota and no derivative bookkeeping. |

---

## 2. Future version list

Each version is one review cycle and one coherent piece of work. The estimate is the *implementation*, not the review that follows it.

| Version | Theme | Scope | Estimate | Blocked on |
|---|---|---|---|---|
| **v2.7** | State is shared | Dispatcher, revocation and buckets in the store, render-minute quota | **Done** | — |
| v2.8 | Assets exist | Asset table, ingest, probing, proxies, conforming, storage quota; §10's analysis pipeline skeleton | 4–6 sessions | — |
| v2.9 | It renders at 4K | NVENC path, chunked render with segment publishing, the §12.9 matrix measured, benchmarks filled | 5–8 sessions | A GPU machine |
| v3.0 | P0 complete | Model-driven planner (two passes), the prompt→file path end to end, evaluation corpus, the 80% target measured | 8–12 sessions | Model budget, v2.8 and v2.9 |
| v3.1 | Faces | Labelled corpus, accuracy measured, the feature enabled behind a flag | 2–3 sessions | **Procurement**, legal review |
| v3.2 | Designed titles | Remotion to an alpha intermediate, composited at record frames, golden hash | 3–4 sessions | A decision to fund it |
| v3.3 | The platform | `origin`/`params_hash` contract exercised against the 3D and dubbing engines | 2–3 sessions | Those engines' owners |
| v4.0 | Product surface | Whatever the platform needs — accounts, billing, UI | Not estimated here | Platform decisions |

**Rough total to a system that turns a prompt into a rendered file at 1080p:** v2.8 + v2.9 (1080p only) + v3.0 ≈ **17–26 sessions**, before faces, titles or the platform.

**To the full specification as written:** add v3.1, v3.2, v3.3 ≈ **24–36 sessions**, plus procurement and hardware.

---

## 3. The critical path

In order, because each one changes what the next can assume:

1. **Assets and ingest (v2.8).** Nothing downstream is testable without conformed media. This is the single largest unblocker and it is ordinary work — no research, no decisions.
2. **A GPU and the NVENC path (v2.9).** §12.3's entire capacity model is unmeasured. Until it is measured, every cost figure in §20 is a target.
3. **The model path (v3.0).** The planner, the two passes, and the evaluation corpus. This is where the product either works or does not.
4. **Faces (v3.1).** Gated on a corpus that has to be bought or built under consent.

Steps 1 and 2 are engineering. Step 3 is engineering plus a model budget. Step 4 is procurement.

---

## 4. Conditions these estimates assume

If any of these fails, the numbers move:

- **One person, full time, already familiar with the repository.** The reference implementation is dense; a new contributor loses a week to it.
- **The specification stays stable.** Each review cycle that changes a contract adds rework downstream — v1.4's conform map touched the compiler, the planner and every fixture.
- **A GPU machine is available by v2.9.** Without one, v2.9 becomes "write code that cannot be measured", which is how §12.3's numbers became targets in the first place.
- **No new engines land in parallel.** A platform of four engines multiplies the integration work in v3.3.
- **The licence question is settled before anyone else touches the code.** It is currently all rights reserved.

---

## 5. What is blocked on you, not on work

| Decision | Blocks | Cost of not deciding |
|---|---|---|
| **Grant the App `administration: write`** | Repository metadata — description, topics | Ten minutes; the copy is in `docs/repo/ABOUT.md` |
| **Licence: keep all-rights-reserved, or MIT/Apache-2.0** | Anyone else contributing, and every engine you add | One line, but it gates collaboration |
| **Buy or build a labelled face corpus** | v3.1 entirely | Weeks of lead time; start early if faces matter |
| **Fund a GPU machine or runner** | v2.9 and every capacity number | The cost model stays theoretical |
| **Decide whether designed titles matter** | v3.2 | Currently a stated non-goal, which is at least honest |

---

## 6. How to read the estimates

They are ranges because the low end assumes nothing surprising and the high end assumes one thing is worse than expected — usually the GPU driver, the model's plan quality, or the corpus's condition coverage. In this repository's history the thing that was worse than expected has been, every time, **the layer nobody had executed**: the extractor that truncated code blocks, the compiler that never emitted a final label, the requeue that let two workers write the same job.

The cheapest way to keep the low end is the rule this repository already follows: **execute the new layer in the same version that specifies it.** Every version that did that closed its findings; every version that deferred it created the next version's list.
