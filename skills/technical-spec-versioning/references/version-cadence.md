# The version cadence

Nineteen versions of one specification produced a repeatable loop. This is that loop, with the evidence for each step, so a long project can be run the same way without re-deriving it.

## The loop, in order

1. **Read the previous version's open list.** It is the only honest statement of what is wrong. If it does not exist, the project has no memory and every version is a rewrite.
2. **Audit before editing.** Static analysis, stale counts, duplicate definitions, tests that cannot fail. In one project this step found seven defects across four versions that no review had caught, including an orphan requeue that let two workers write the same file.
3. **Write the findings table first.** One row per finding: what was wrong, and the section that resolves it. The table is the contract for the version; prose is written to satisfy it, not the reverse.
4. **Apply edits with asserted anchors.** Every replacement asserts its anchor matched exactly once. A silent no-op is how a version ships claiming a fix it does not contain.
5. **Compute every figure.** A checker that re-derives each number from first principles and compares it to the prose. Thirty-two assertions became ninety-one over the project's life, and the checker caught three errors in prose written the same day.
6. **Renumber, then verify cross-references.** Tables, listings, figures and requirement IDs. Two IDs collided once because a row was inserted before an existing one.
7. **Build the artefact from the source.** Markdown is the source; the document is generated. Then extract the document back and re-run every check on the extracted text — that round trip caught an extractor that had been truncating code blocks for six versions.
8. **Render the artefact and look at it.** Split table rows, a build that produced nine tables instead of forty-three, a caption two versions stale. None was visible to a text check.
9. **Close by naming what is still open.** The next version's list, written before the current one ships.

## What the loop produces, in proportion

Over nineteen versions, the defects found split roughly:

| Class | Share | Example |
|---|---|---|
| A rule that was right and a code path that did not exist | ~40% | The conform map: specified for four versions, produced by none |
| Two correct numbers in different domains, never joined | ~20% | Native frames versus conformed frames |
| State in the wrong place — a process instead of a store | ~15% | Revocation, rate limiting, job state |
| The artefact disagreeing with its source | ~15% | The nine-table build, the stale caption |
| Schema and code drifting | ~10% | A state added to code and not to the DDL |

**Every single one was found by executing something**, not by reading. That is the strongest finding in the whole exercise.

## The rules that held

- **A number is computed or labelled an assumption.** No exceptions; the label is part of the sentence.
- **A finding leaves the list only when a version resolves it**, and the resolution is named in that version's table.
- **A version that resolves something creates the next finding.** The ratio held at roughly two of six for fifteen versions. Budget for it.
- **Never re-schedule an unimplemented feature more than twice.** Withdraw it and say so; a roadmap item nobody owns is a lie with a date on it.
- **Delete duplicates rather than reconciling them.** Two implementations of one contract, each correct, is the most expensive state to be in.

## Anti-patterns, with the cost

| Anti-pattern | What it cost |
|---|---|
| Editing the document by hand | Three figures silently diverged from their source in one version |
| Testing the rule but not the translation | A compiler emitted a graph with no output label; eight golden files passed |
| Fixtures whose inputs are interchangeable | A swapped input would have hashed identically — the test could not see the bug it existed for |
| A test that asserts something always true | `assert "frame=" in stderr` passed on every run including broken ones |
| A checker written against one instance of a pattern | The state-drift checker could not see table drift, twice |
| Deferring the layer you just specified | Six versions of "nearly done" on one subsystem |

## Sizing

A version that closes six findings and adds one subsystem: 4–8 focused sessions. A version that closes six findings and adds only prose and tests: 1–2. A version whose main change is a deletion: under one.

The estimate is dominated by whether the new layer is **executed** in the same version. Every version that executed it closed its findings; every version that deferred it created the next version's list.
