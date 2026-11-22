# Work log

How this repository was assembled, in the order it was done, so that whoever picks it up next knows what exists, why, and what is still open.

Two things are recorded here that are easy to lose: the **input → version mapping** (which review produced which version), and the **commit-by-commit construction** of the repository itself.

## 1. The version line

Each version is a full standalone specification answering one external technical review. The input is always a review; the output is always a document whose §0 table maps every finding to the section that resolves it.

| Version | Input | Verdict on the previous version | What the version did |
|---|---|---|---|
| v1.0 | First draft | — | Established the architecture: IR, three-stage separation, tool layer, engine choice |
| v1.1 | First technical review | "Sound architecture, not implementation-ready" | Time and frame model, full IR schema, database design, API and tool contracts, enforced multi-tenancy |
| v1.2 | Second technical review | "Much better, not yet executable" | Mixed-rate speed arithmetic, multi-track duration, composite tenant keys, the 4K60 capacity model |
| v1.3 | Third technical review | "Architecture approved, complete P0 readiness withheld" | Executable contracts: BigInt wire format, complete migration, P010 figures, preview cost, RLS threat model, missing endpoints |
| v1.4 | Fourth technical review | "Architecture settled; a boundary remained" | The conform map (§5.9), sound that follows its picture (§5.11), remapped captions (§5.10), tolerances in milliseconds (§5.12), op inverses (§6.6), reconciled unit economics (§12.11), erasure propagation (§16.6), asset provenance (§6.8) |
| v1.5 | *Not started* | — | The eight open findings in `docs/reviews/v1.5-candidates.md` |

The pattern across the four versions is worth stating, because it predicts the fifth: **each review found the previous version arithmetically correct inside its sections and inconsistent between them.** v1.1's defect was a speed formula that assumed two rates were equal; v1.2's was a duration rule that worked on one track; v1.3's was a set of figures that assumed two bytes per pixel. The class of defect does not change; the layer it hides in does.

## 2. What was built, and in what order

Twelve commits, each one a coherent step. The order is the order the work was actually done, which is why the specification precedes the scripts that check it: the document came first, then the tooling that proves it.

| # | Commit | What it added |
|---|---|---|
| 1 | `chore: initialise repository` | `.gitignore`. The specification is the product; the repository keeps it reviewable |
| 2 | `docs(archive): add v1.0, v1.1 and v1.2` | The superseded versions, unedited, so a withdrawn claim stays inspectable |
| 3 | `docs(spec): add v1.3 (artefact of record)` | The canonical `.docx` |
| 4 | `build: add docx to markdown extractor` | `build/extract_spec.py` — recovers headings, tables, code and figures from the document's own formatting |
| 5 | `docs(spec): generate markdown and figures` | `docs/spec/v1.3.md` and three figures, generated rather than transcribed |
| 6 | `build: add figure checker` | `build/check_figures.py` — 32 assertions, exact arithmetic |
| 7 | `docs(engine): platform map` | Where this engine sits among the others, and the four rules of composition |
| 8 | `docs(engine): engine contract` | The surface the platform may depend on |
| 9 | `docs(review): v1.4 candidates` | Ten open findings with severity and proposed fix |
| 10 | `docs: CHANGELOG` | Per version: the review it answers, the theme, the finding-to-section map |
| 11 | `docs: README` | Orientation for three readers: fifteen minutes, two hours, a day |
| 12 | `skill: technical-spec-versioning` | The routine this repository is built with, including the twelve-class defect taxonomy |
| 13 | `docs: documentation index` | `docs/README.md` — every document, the question it answers, and the reading order by role |
| 14 | `docs: contributing guide` | `CONTRIBUTING.md` — how a version is cut, how a finding is proposed, the conventions |
| 15 | `docs: work log` | This file |

## 2a. The v1.4 round, and how it was built

v1.4 was built from the previous version's markdown rather than re-authored, because the findings were localised: one new section block, one corrected schema field, three new tables and a set of paragraph rewrites. Each edit asserted that its anchor matched exactly once, so an edit that silently failed to apply failed the build instead of shipping a document claiming a resolution it did not contain.

The order matters and is worth repeating: the §0 table was written first, then the sections that had to justify each row, then the figures were extended to cover the new arithmetic, then the document was built.

Commits, in order:

| # | Commit | What it did |
|---|---|---|
| 16 | `docs(spec): add v1.4 source` | The markdown, edited from v1.3 with 34 anchored replacements and three new sections |
| 17 | `build: add the docx builder` | `build/build_docx.py` — house style reproduced: A4, Calibri, navy captions, tinted table headers, code on a pale slab |
| 18 | `build: extend the figure checker to 48 assertions` | Appendix A's five clips through the conform map, and the third cost operating point |
| 19 | `docs(spec): build v1.4 and archive v1.3` | The `.docx`, and the superseded version moved to `archive/` |
| 20 | `docs(review): v1.5 candidates` | Eight open findings, three of them created by v1.4's own resolutions |
| 21 | `docs: changelog for v1.4` | Twelve rows, each naming the section that resolves it |
| 22 | `docs: update README, index and worklog` | The version table, the reading order and this section |

What the figure checker proved, beyond the arithmetic: extracting the built `.docx` back to markdown and re-running all 48 checks passes, which is the round-trip test that the document contains what its source says.

## 3. What the verification actually checks

`build/check_figures.py` derives each figure from first principles rather than comparing it to a stored constant, so it keeps working when the document changes. Thirty-two checks across five groups:

**Time.** 1349 frames at 30000/1001 is 45.011633 s and 2,160,558 samples — and the sample count is *rounded*, not exact, which is the point §5.5 now makes. The conform arithmetic: 300 record frames at 25 fps consume 250.25 native frames and 300 conformed frames; the double-rounding case turns 501 native into 601 against a correct 600; a 59.94 source consumes 600 native frames for 300 record frames. Sped audio: 600 conformed frames at 29.97 is exactly 960,960 samples.

**Memory.** P010 is 4:2:0 at 10 bits in 16-bit containers, so a frame is `w × h × 1.5 × 2` bytes: 6.22 MB at 1080p, 24.88 MB at 4K, 99.53 MB at 8K. Four passes of 4K60 is 5.97 GB/s, which implies 50 streams at a 300 GB/s ceiling. The luma-only figure v1.2 printed, 16.59 MB, is asserted too, so the correction stays visible.

**Capacity.** Two L4 encoders at 128 fps is 256 fps at 4K, 4.27× realtime, 2.77 streams after the 65% allowance, and four GPUs for ten concurrent finals.

**Cost.** The three 4K60 operating points — dedicated $0.00556, headroom $0.00417, packed $0.00301 — and the 1.85× ratio between the first and the last.

**Units.** 480p is 0.20× the pixel work of 1080p and 360p is 0.11×, which is how the three-way preview inconsistency was found. 120 ms is 4 frames at 29.97 and 7 at 59.94, which is why tolerances moved to milliseconds.

Writing the check found two real defects in the checking itself, both worth recording: Python's `round()` is half-to-even and disagrees with the specification's half-away-from-zero on exactly the boundary cases this document cares about; and a fleet-size calculation that truncates the stream count before dividing gives five GPUs where the correct answer is four.

## 4. What is open

| Item | Where | Blocking what |
|---|---|---|
| The VFR half of the conform map is unproven | `reviews/v1.5-candidates.md` §1 | A fixture, before any VFR customer |
| The atempo cascade has no awkward-ratio fixture | §2 | Speed fidelity at ratios that do not decompose |
| Erasure quarantine has no owner or release path | §3 | A product and legal decision, not an engine one |
| `origin.params_hash` is undefined per engine | §4 | Cross-engine provenance comparisons |
| A transition beside a sped clip has no handle rule | §5 | Dissolves against 2× clips |
| The 540p preview proxy is required but not costed | §6 | Storage and ingest figures |
| Beat snapping from a sped music bed is undefined | §7 | Musical edits over time-stretched tracks |
| Storage and egress stay outside the cost model | §8 | Any 4K60 business case |

Nothing in that list is architectural. All eight are contract and fixture work, which is the honest position for a design that has survived four reviews without a structural change — and three of them exist because v1.4 changed something, not because v1.4 missed something.

## 5. Conventions this repository follows

- One commit per step, imperative mood, a body that says why rather than what.
- The `.docx` is authoritative; the markdown is generated and never hand-edited.
- A superseded version is archived, never deleted.
- A withdrawn claim is withdrawn in the text, not removed.
- Open findings live outside the specification.
- Every figure is computed or labelled an assumption. Nothing is typed twice.
