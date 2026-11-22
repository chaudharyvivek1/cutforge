# Completion plan

What remains before this engine can turn a prompt into a rendered file, in order, with honest time. Every estimate is a **range in focused sessions** — one session is roughly a working day by one person already familiar with the repository — and every range is dominated by whether the step needs a purchase.

Current state: specification complete for P0 on contracts (28 reviews, no known contradiction), reference implementation at **365 tests**, and four of five open findings gated on money rather than effort.

---

## 1. The steps, in order

| # | Step | Version | Sessions | Gated on | What it produces |
|---|---|---|---|---|---|
| 1 | **A GPU hour** — run `build/benchmark.py`, fill §12's matrix | v2.19 | 1 | **~₹500–2,000** | Real capacity numbers; findings 1 and 2 close |
| 2 | **A model budget** — one provider adapter behind `ModelClient`, run the two passes on the §19.2 prompts | v3.0 | 3–5 | **Budget** | The first plan a model has ever made here, scored twice |
| 3 | **An evaluation corpus** — 40 prompts, 20 plans labelled by a second person | v3.1 | 2–3 | **A second person, an afternoon** | The 80% first-attempt target becomes measurable |
| 4 | **Ingest to render, end to end** — upload → probe → conform → plan → compile → render → file | v3.2 | 4–6 | — | The first complete path a customer could use |
| 5 | **A face corpus** — buy or build, then measure accuracy | v3.3 | 3–4 | **Procurement, weeks of lead time** | Identity enabled behind a flag |
| 6 | **Designed titles** — Remotion to an alpha intermediate | v3.4 | 3–4 | A decision to fund it | Currently a stated non-goal |
| 7 | **Platform integration** — `origin`/`params_hash` against the 3D and dubbing engines | v3.5 | 2–3 | Those engines' owners | Engine 3 of 4 actually composing |

**Total to a usable product (steps 1–4): 10–15 sessions.**
**Total to the full specification (steps 1–7): 18–26 sessions**, plus procurement lead time that runs in parallel.

---

## 2. What that means in calendar terms

| Pace | To a usable product | To the full specification |
|---|---|---|
| One session a day | **2–3 weeks** | **4–5 weeks** |
| Three sessions a week | 3–5 weeks | 6–9 weeks |
| One session a week | 10–15 weeks | 18–26 weeks |

The calendar is **not** set by the work. It is set by step 1: without a GPU, steps 1 and 2 cannot start, and steps 2–4 all depend on the model path being real.

---

## 3. The critical path, stated plainly

```
GPU hour (1 session)
      ↓
model adapter + two passes (3–5 sessions)
      ↓
end-to-end path (4–6 sessions)  →  usable product
      ↓
corpus + second author (2–3 sessions)  →  80% target measured
      ↓
faces (3–4 sessions + procurement)
```

Everything left of "usable product" is engineering. Everything at or below "corpus" needs a person or a contract, and the procurement steps have lead time measured in weeks, so they should be started **now** even though their versions are later.

---

## 4. What is already done and will not need repeating

Worth stating, because it is most of the work and it is finished:

- The time model, the conform map, speed and audio — computed, not asserted
- The timeline IR and the compiler — eight golden graphs, two hashed on decoded frames
- The planner, the repair loop, the rubric and two judges — calibrated against labels
- The store, the service, auth, quotas, webhooks, metrics — 365 tests
- Ingest, proxies, conforming, shot detection, transcript remap
- Chunked render proved byte-identical, segments published and expired
- The database schema, its migration and its row-level security — statically checked

A new team picking this up inherits a specification with no known contradictions and a reference implementation that executes the claims in it.

---

## 5. The three things to buy, with what each unlocks

| Purchase | Approximate cost | Unlocks | Lead time |
|---|---|---|---|
| **One GPU hour** (rented) | ₹500–2,000 | §12's capacity model becomes real; two findings close | Same day |
| **Model budget** (API credit) | ₹5,000–20,000 for evaluation | The product's premise is tested | Same day |
| **Face corpus** | ₹0–50,000 depending on build vs buy | Identity feature, behind consent | 2–6 weeks |

The first two are the difference between a specification and a product, and both are smaller than a week of anyone's salary.

---

## 6. How to read these numbers

They are ranges because the low end assumes nothing surprising and the high end assumes one thing is worse than expected. In this repository's history the thing that was worse than expected has been, every time, **the layer nobody had executed** — the extractor that truncated code blocks, the compiler that never emitted a final label, the requeue that let two workers write the same job, the repair that shortened a film by 584 frames.

The cheapest way to keep the low end is the rule the repository already follows: **execute the new layer in the version that specifies it.** Every version that did that closed its findings; every version that deferred it created the next version's list.
