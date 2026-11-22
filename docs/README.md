# Documentation index

Every document in this repository, what question it answers, and when to read it. If you only read one thing, read the README; if you only read one thing inside the spec, read §5.

## The specification

| Document | Answers | Read when |
|---|---|---|
| [`spec/AI_Video_Editor_Architecture_v1.4.docx`](spec/AI_Video_Editor_Architecture_v1.4.docx) | The whole design, as the artefact of record | You are reviewing or building against it |
| [`spec/v1.4.md`](spec/v1.4.md) | The source the document is built from, so it is diffable | You want to read it on GitHub or comment on a line |
| [`spec/figures/`](spec/figures) | The three diagrams, extracted from the document | You are placing the spec in a deck or a wiki |

From v1.4 the markdown is the source and the `.docx` is built from it by `build/build_docx.py`. Edit the markdown, rebuild the document, and never edit the `.docx` by hand — the next build overwrites it.

**Where the risk lives.** §5 (time and frame model), §6 (the IR) and §11 (the render engine) carry almost all of the risk. If the time model is wrong, every downstream section inherits the error. §12 (capacity) and §20 (cost) are arithmetic that can be re-run; §13 and §14 are schema and isolation that can be tested.

## The engine boundary

| Document | Answers | Read when |
|---|---|---|
| [`engine/01-platform-map.md`](engine/01-platform-map.md) | Where this engine sits among the others, what each owns, and the four rules of composition | You are integrating a second or third engine |
| [`engine/02-engine-contract.md`](engine/02-engine-contract.md) | The exact surface the platform may depend on: jobs, states, artefacts, events, failure codes | You are writing the platform side, or the next engine |

The distinction that matters: the specification describes the engine's **internals**, which may change between minor versions. The contract describes its **surface**, which may only grow. When the two disagree, the contract wins and the specification has a bug.

## Review history and open work

| Document | Answers | Read when |
|---|---|---|
| [`reviews/v1.5-candidates.md`](reviews/v1.5-candidates.md) | What is still wrong, with severity and a proposed fix | You are planning v1.5, or deciding how much to trust a section |
| [`../CHANGELOG.md`](../CHANGELOG.md) | What each version changed, and which finding it answered | You want to know why something is the way it is |
| [`../archive/`](../archive) | The superseded versions, unedited | A claim was withdrawn and you want to see it as written |
| [`worklog.md`](worklog.md) | How this repository was assembled, step by step | You are taking over the repository |

Open findings are deliberately kept **out** of the specification. A spec that lists its own unresolved defects teaches a reader to distrust every claim in it; a separate candidates list lets the spec stay firm and the debt stay countable.

## Scripts

| Script | Does | Run when |
|---|---|---|
| `build/check_figures.py` | Recomputes 48 of the spec's figures from first principles and fails on any drift | Before every commit that touches a number |
| `build/build_docx.py` | Builds the `.docx` from `spec/v1.4.md` in the house style | After any markdown change |
| `build/extract_spec.py` | Recovers markdown from a `.docx`, for round-trip verification and for the archived versions | After a build, to prove the document matches its source |

## Reading order by role

**Reviewing the design.** README, then §1 and §4 of the spec, then `engine/01-platform-map.md`, then §5 and §6. Stop and read `reviews/v1.5-candidates.md` before you form a verdict — the largest open defect is in the time model, not in the architecture.

**Building the compiler.** §5, §6, Appendix A, then `build/check_figures.py` to see which arithmetic is already pinned. The conform map is now in §5.9 of the spec; its VFR half is finding 1 of `reviews/v1.5-candidates.md` and is the first thing to build a fixture for.

**Building the platform side.** `engine/02-engine-contract.md`, then §15 (API), then §17 (observability). The contract document is short on purpose; the four prohibitions in §9 of it are the ones that break guarantees quietly.

**Writing the next version.** `skills/technical-spec-versioning/SKILL.md`. It is the routine this repository was built with, including the four review passes and the twelve recurring defect classes.
