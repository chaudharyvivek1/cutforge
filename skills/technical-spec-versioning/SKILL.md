---
name: technical-spec-versioning
description: Take a technical design specification through a review cycle and produce the next version — building the finding-to-resolution table, writing the sections that close each finding, verifying every figure by computation, and maintaining the specification repository (docx of record plus generated markdown, changelog, open-findings list). Use when a user hands over a spec, design doc or architecture document and asks for a review, a corrected version, a vN+1, or a repository around it.
---

# Technical spec versioning

A recurring job: a design document has been reviewed, and the next version must answer the review. The output is not a rewrite. It is a **new full document whose §0 table maps every finding to the section that resolves it**, plus evidence that the figures in it are true.

## When this applies

- "Here is v1.2, here is the review, produce v1.3."
- "Review this architecture doc" — which means: produce findings, then a version.
- "Put this spec in a repo and make it reviewable."
- Any request for a corrected version of a document whose numbers matter (time, capacity, cost, schema).

Not for: writing a first draft from nothing, or editing prose style.

## The loop

### 1. Read the whole document before finding anything

Extract to text first (`python-docx` for .docx; keep tables as pipe rows, keep code listings separate). Read every section. **A finding drawn from a partial read is a false finding**, and one false finding discredits the table.

Record, as you read: every number, every cross-reference (§x.y), every schema field, every count ("nineteen tools"), every claim of a property ("deterministic", "exact", "identical").

### 2. Find defects in four passes

Work the passes in order; each one catches what the previous cannot.

**Pass A — arithmetic.** Recompute every figure in exact arithmetic (`fractions.Fraction`, never float). Compare against the printed value. Check derived quantities against their inputs, and check that a stated conclusion still follows from a corrected input.

**Pass B — domain and units.** For each quantity ask: *which space is this number in?* frames or seconds; native or conformed; per stream or per GPU; bytes or pixels; per output minute or per GPU minute. Most serious spec bugs are two correct numbers in different spaces, never joined. Also check rounding: how many times, and where.

**Pass C — contract against mechanism.** Every promise needs a mechanism in the same document. "The API reports a deadline" needs a column. "Every op has an inverse" needs the data the inverse is computed from. "Deterministic given the manifest" needs the manifest to pin every input that varies. Grep for promise verbs — *guarantees, identical, always, never, exact, free, reproducible* — and for each one find the artefact that makes it true.

**Pass D — cross-reference and count drift.** A count stated in three places ("17/18/19 tools"). A field named two ways (`would_be_revision` vs `new_revision`). A rule asserted in prose and violated in the document's own listing — the strongest kind of finding, because the evidence is in the same file. An enum value with no implementation. A phase name that changes between sections.

See `references/finding-taxonomy.md` for the full catalogue with examples.

### 3. Build the §0 table before writing any prose

One row per finding: **Finding | What was wrong | Resolution in vN**. This table is the version's contract with its reviewer, and writing it first prevents the two failure modes — a resolution that never gets written, and a section that changes something nobody asked about.

Sort rows by severity, not by section order. A reader wants to know what nearly broke.

### 4. Write the new version as a full document

Carry forward every section, including unchanged ones. A version that is a patch set forces the reader to hold two documents.

For each changed section: state the old behaviour, state why it was wrong, state the new rule, and show the arithmetic. The reviewer's counter-example goes in as a worked case — it is the most valuable paragraph in the section, because it is the one case already known to break.

### 5. Verify before delivery

Every figure the document asserts gets recomputed by a script that fails loudly. Keep it in `build/check_figures.py` in the repository, and make the checks read the values out of the document where practical, so prose and appendix cannot drift apart.

Run it. Fix the document, not the check — unless the check itself is wrong, in which case say so and fix both.

### 6. Maintain the repository

Layout that works:

```
docs/spec/<version>.docx      artefact of record — never hand-edited markdown
docs/spec/<version>.md        generated from the docx, so the doc is diffable
docs/engine/                  boundary and contract, if it is an engine not an app
docs/reviews/vN+1-candidates.md   open findings, with severity and proposal
archive/                      superseded versions
build/                        extract_spec.py, check_figures.py
CHANGELOG.md                  per version: basis, theme, finding -> section
```

Keep open findings **out of the specification**. A spec that lists its own unresolved defects teaches readers to distrust every claim in it; a separate candidates list lets the spec be firm and the debt be counted.

## Quality bar

A version is done when all of these hold:

- Every row of §0 names a section, and that section contains the stated rule.
- Every number in the document is either computed by the check script or explicitly labelled an assumption with a source.
- No count, field name or enum appears in two forms.
- Every promise verb has a mechanism within the same document.
- The worked example uses the reviewer's own counter-example, and adds up.
- Nothing is claimed as measured that was not measured; use an evidence-status column instead of confident prose.
- Withdrawn claims are withdrawn in the text, not silently deleted — a reader who saw v1.2 needs to know that v1.3 no longer promises it.

## Pitfalls that have actually bitten

- **Fixing a number in one section and leaving its consequence in another.** Correct the frame size, then recheck the bandwidth, the stream count and the cost per minute.
- **Rounding twice.** Any pipeline that converts units twice and rounds each time is one frame wrong. Round once, at the boundary.
- **Half-to-even versus half-away-from-zero.** Python's `round()` is not the spec's rule. Implement the stated rule explicitly.
- **Trusting a document's own consistency.** The listing that violates the rule is the fastest finding available, and it is invisible to a reader who skims prose.
- **Treating an unchanged section as verified.** It was verified against the previous review's concerns, not this one's.
- **A resolution that adds a field to a schema without saying it is a version bump.** Flag every IR or API change explicitly; those need a version, not an edit.

## Scripts

`scripts/extract_docx.py` — docx to faithful markdown (headings, pipe tables, fenced code by monospace detection, figures extracted to `figures/`). Run it before reading anything.

`scripts/check_figures_template.py` — the shape of a figure-check: compute from first principles, compare to the value the document prints, fail with a list. Copy it into the repo's `build/` and fill it with that document's constants.
