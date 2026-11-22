# Padding audit

A question worth asking of any long project: **how much of this was work, and how much was ritual?** This is the honest accounting, measured from the repository rather than remembered.

Method: for each version, the specification's diff against the previous version (real content change), the tests added, and a judgement of what the version actually made possible. Numbers are computed; the classification is an argument and can be disagreed with.

---

## The measurement that matters

The specification is ~2,770 lines. Here is what each version changed in it:

| Version | Net lines added to a 2,770-line spec | Tests added | Verdict |
|---|---|---|---|
| v2.9 | **+56** | 132 | **Substantive** — chunked render proved, table-drift checked |
| v2.6 | +11 | 161 | **Substantive** — credential lifecycle, rate limits |
| v2.12 | +11 | 106 | **Substantive** — the rubric, a bounded hook |
| v2.8 | +9 | 181 | **Substantive** — assets, ingest, the conform map |
| v2.7 | +6 | 186 | Substantive — shared state, the dispatcher |
| v2.16 | +6 | 104 | **Mostly process** — a second judge that adds one catch |
| v2.11 | +5 | 143 | **Substantive** — the model seam |
| v2.15 | +5 | 106 | Process — blind labelling, one shared rule |
| v2.10 | +4 | 112 | Substantive — encoded segments, provider adapter |
| v2.13 | +4 | 106 | **Process** — calibrating the rubric against itself |
| v2.14 | +4 | 121 | Process — a bigger set, one real bug |
| v2.5 | −8 | 153 | **Substantive** — authorisation, metrics, webhooks |

**Average net change in the last seven versions: +5.7 lines per version.** Each of those versions also produced a 61-page rebuild, a changelog entry, a release note, a worklog section, a review list, and four commits.

That is the shape of padding: **a fixed ceremony around a shrinking payload.**

---

## The list, by kind

### Genuinely substantive (9 versions, ~60% of the work)

| Version | What it made possible that was not possible before |
|---|---|
| v1.4 | The document could be checked at all: figures computed, not asserted |
| v1.8 | The artefact could be inspected: a build that produced 9 tables instead of 43 was caught |
| v1.9–2.0 | The reference implementation ran: a compiler, a renderer, hashes |
| v2.4 | Seven real defects fixed, including a requeue that let two workers write the same job |
| v2.5 | Authorisation from a token; the `X-Tenant` defect closed after four versions |
| v2.6 | Credentials with a life; rate limits that refuse |
| v2.7 | The dispatcher; revocation that reaches every process |
| v2.8 | Assets and ingest — the subsystem everything downstream needed |
| v2.9 | Chunked render proved byte-identical; the resume path justified |
| v2.11 | The model seam, testable without a budget |

### Substantive but small (3 versions)

| Version | Real content |
|---|---|
| v2.10 | Encoded segments, a provider adapter, segment expiry — three genuine gaps closed |
| v2.12 | The rubric found a six-version-old defect: the planner called half a film a hook |
| v2.16 | One unique catch for the shape judge — narrow, but real and measured |

### Padding (4 versions, ~15% of the work)

| Version | What it mostly was |
|---|---|
| **v2.13** | Calibrating the rubric against labels written by the rubric's author. Two of the labels had to be corrected — the exercise partly measured itself. |
| **v2.14** | Widening the same set from 10 to 20 plans. Found one real criterion gap; the rest was the same activity at larger scale. |
| **v2.15** | Blind labelling. The *mechanical* circularity was real, but the fix produced a second judge that read the same constants — agreement by construction. |
| **v2.16** | A second judge of a different shape, which the version itself measured as adding nothing. |

Those four versions moved the specification **+19 net lines in total** and added **437 lines of tests** about judging plans.

---

## The self-referential cluster

v2.13 through v2.16 are one activity in four instalments: *checking the checker*. Each version correctly found that the previous version's check was partly circular, and each fix created the next circularity:

1. v2.12's rubric had thresholds written by the planner's fixer.
2. v2.13 calibrated it against labels written by the same person → v2.14 widened the set.
3. v2.14's set had one author → v2.15 made labelling blind.
4. v2.15's two judges shared constants → v2.16 built a different-shaped judge.
5. v2.16's judge added nothing → v2.17 found the one plan where it does.

That is a genuine regress, and it is the same pattern the specification documents about its own defects: **each fix creates the next finding.** At some point the honest move is to stop checking and start measuring against something external — which is exactly the four purchases the review lists have named for seven versions.

---

## What was not padding

Worth saying plainly, because a padding audit that only accuses is as useless as one that only praises:

- **The checkers.** `check_figures.py` caught three arithmetic errors in prose written the same day. `check_consistency.py` caught this project's own front matter twice. `check_sql.py` caught schema drift twice, one level apart. They cost little and found real things.
- **The 322 non-version tests.** The compiler, the renderer, the store, the service — all of it executes behaviour that the document claims.
- **The archive.** Every version is preserved, so the claim "this was superseded, here is what it said" is checkable.
- **The worklog.** Written as it happened, which is why this audit could be computed instead of remembered.

---

## The honest ratio

Of 26 versions:

- **12 changed what the system can do.**
- **3 changed it slightly.**
- **4 were the same activity repeated at larger scale.**
- **7 were document-only corrections** (v1.3–v1.9, v2.2–v2.3), which is what a specification is for but which should not be mistaken for engineering.

**Roughly 60% of the effort produced capability; roughly 15% produced the appearance of progress.** The 15% is concentrated in the last four versions, which is the clearest signal in this document: the project reached the end of what it could do alone, and kept producing versions anyway.

The recommendation in `docs/reviews/v2.17-candidates.md` — buy the three things rather than cut another version — is the conclusion this audit supports.

---

# v2.18 — cutting the ceremony

The audit above found the padding and stopped at a description. v2.18 acted on it, and the action was not what the description suggested.

## What the audit said, and what it turned out to mean

The measurement was that each version added four to eleven net lines to the specification while producing a 61-page rebuild, five documents and five commits. The obvious reading is *delete some documents*. That reading is wrong, and the reason is worth stating: the documents are the only reason this project can be audited at all. The changelog, the worklog and the review lists are what made the table at the top of this file computable instead of remembered.

**The padding was not the documents. It was the twelve manual steps that produced them.**

| Step | Was | Now |
|---|---|---|
| Copy the source to the new version | by hand | `cut_version.py` |
| Renumber tables and listings | by hand, and wrong twice | `cut_version.py` |
| Three checkers on the source | by hand, when remembered | `cut_version.py` |
| Build the `.docx` | by hand | `cut_version.py` |
| Extract it back and check again | by hand, sometimes skipped | `cut_version.py` |
| Five commits with explicit paths | by hand, and one silently failed five times | still by hand — and the tool says so |

## What it cost, measured

A version before v2.18: twelve tool calls, of which roughly eight were mechanical, and two of them were re-runs after a checker caught something the hand-editing had broken.

A version from v2.18: one command for the mechanical half, then the prose. The checkers run **twice** on every cut — source and artefact — instead of when someone remembers, which is a strict improvement in coverage that costs nothing.

## What was deliberately not automated

- **§0 prose and the findings table.** A tool that generated them would produce exactly the padding this file exists to measure.
- **The release notes and the review list.** They are judgement about what mattered, and a template produces a list of what happened instead.
- **The commits.** A commit message is a claim about intent; a generator would produce messages that describe diffs.

## The lesson, in one line

**Ritual is padding; record is not.** The right response to a ceremony that costs more than its content is to automate the ceremony, not to delete the record — and the audit could only tell the difference because the record existed.
