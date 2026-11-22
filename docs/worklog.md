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
| v1.4 | *Not started* | — | The ten open findings in `docs/reviews/v1.4-candidates.md` |

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
| No conform map between native and conformed frames | `reviews/v1.4-candidates.md` §1 | The compiler's input format — this is the first decision of v1.4 |
| Speed says nothing about audio | §2 | The IR schema; needs a version bump |
| Captions and markers never remapped | §3 | Caption correctness on any edited clip |
| Capacity and cost disagree by 1.85× | §4 | The business case, not the build |
| Erasure does not propagate | §5 | Legal review before identity matching ships |
| Op inverses are not derivable as claimed | §6 | Undo and the repair loop |
| Tolerances expressed in frames | §7 | Behaviour differs between 30 and 60 fps projects |
| A held job has no deadline column | §8 | The `awaiting_input` contract |
| `speed_curve` in the enum, not in the compiler | §9 | A schema that promises an unimplemented capability |
| Assets carry no upstream provenance | §10 | Diagnosing cross-engine faults once a second engine ships |

Nothing in that list is architectural. All ten are contract work, which is the honest position for a design that has survived three reviews without a structural change.

## 5. Conventions this repository follows

- One commit per step, imperative mood, a body that says why rather than what.
- The `.docx` is authoritative; the markdown is generated and never hand-edited.
- A superseded version is archived, never deleted.
- A withdrawn claim is withdrawn in the text, not removed.
- Open findings live outside the specification.
- Every figure is computed or labelled an assumption. Nothing is typed twice.
