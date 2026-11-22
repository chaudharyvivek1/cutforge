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
| v1.5 | Fifth technical review | "Rules right; edge cases untested" | VFR map proved (§5.9.4), atempo to the sample (§5.11), transition handles at speed (§5.7), tempo grids that scale (§5.10), erasure release paths (§16.6.1), storage and egress costed (§20.3) |
| v1.6 | Sixth technical review | "Rules right; now run them" | A 29-test conformance suite (`tests/`), audio handles to the sample (§5.7), the VFR map under speed (§5.9.5), one duration field instead of two (§6.2), jurisdictional erasure deadlines (§16.6.1), tiered egress (§20.3) |
| v1.7 | Seventh technical review | "Rules executed; now prove the translation" | A reference compiler under golden files (§19.1), the VFR threshold either side (§5.4), the erasure schema (§13.3, §16.6.1), `speed` bounded in the schema (§6.4), the 95th-percentile example (§20.3), and a static migration check (§13.5) |
| v1.8 | Eighth technical review | "Rules and translation proved; now the artefact" | Five golden graphs (§19.1), a byte-reproducible build (§11.6), a round-trip test, a rendered-page check, the commitment break-even (§20.3), and 16× stated as four stages (§5.11) |
| v1.9 | *Not started* | — | The six open findings in `docs/reviews/v1.9-candidates.md` |

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
| 16 | `docs(spec): add v1.4 source` | The markdown, edited from v1.3 with 35 anchored replacements and four new sections |
| 17 | `build: add the docx builder` | `build/build_docx.py` — house style reproduced: A4, Calibri, navy captions, tinted table headers, code on a pale slab |
| 18 | `build: extend the figure checker to 48 assertions` | Appendix A's five clips through the conform map, and the third cost operating point |
| 19 | `docs(spec): build v1.4 and archive v1.3` | The `.docx`, and the superseded version moved to `archive/` |
| 20 | `docs(review): v1.5 candidates` | Eight open findings, three of them created by v1.4's own resolutions |
| 21 | `docs: changelog for v1.4` | Twelve rows, each naming the section that resolves it |
| 22 | `docs: update README, index and worklog` | The version table, the reading order and this section |

What the figure checker proved, beyond the arithmetic: extracting the built `.docx` back to markdown and re-running all 48 checks passes, which is the round-trip test that the document contains what its source says.

## 2b. The review pass over v1.4 itself

Every version gets reviewed; v1.4 got a second look before it was announced, on the principle that a document whose §0 accuses three previous versions of count drift should survive the same test. Six defects were found in my own work, which is roughly the rate the taxonomy predicts.

| Defect | How it survived the build | Fix |
|---|---|---|
| `speed.num` and `speed.den` were integers | The schema validated; only §5.1's wire format said rates are decimal strings. Two sections, one contract, no cross-check. | Both are `$ref rateString`, and the 16× bound moved to the validator, where §5.11 already enforced it |
| Three overlapping determinism rows in §2.2 | The new rows were appended without reading the rows already there | Collapsed to two: compiler determinism on raw frames, delivered-byte reproducibility on the pinned path |
| Front matter claimed 10 findings, the table had 12 | Two candidate findings split into an arithmetic error and the invariant that hid it, and only the table was updated | Count corrected to 12, with the split explained in the §0 lead |
| The requirement table had two FR-15 rows | The new rows were anchored to FR-14 and inserted before the existing FR-15 | Renumbered to FR-16 and FR-17, placed after it, and the two references updated |
| `check_figures.py` defaulted to a deleted file | The default path was never exercised because every call passed an argument | Default corrected, and the consistency check now tests that no script points at a missing document |
| The running header hardcoded v1.4 | The builder was written for one version | Derived from the eyebrow line, so a v1.5 build cannot lie about itself |

Five of the six were found by rendering the document and reading it, not by the checks — which is the argument for `build/check_consistency.py`, added afterwards so the sixth and its siblings fail the build next time.

## 2c. The v1.5 round

v1.5 is the first version with no structural change: no new requirement, no new tool, no new schema field. It exists because every rule v1.4 added had a case it had not been exercised on, and three of the eight findings were created by v1.4's own resolutions.

The work was 27 anchored edits to the v1.4 source, then renumbering, then 28 new figure assertions. Two of the new assertions failed on first run and both were right to.

| # | Commit | What it did |
|---|---|---|
| 23 | `docs(spec): add the v1.5 source` | 27 anchored edits, five new subsections and tables |
| 24 | `build: extend the figure checker to 76 assertions` | VFR mapping, atempo sample counts, handle domains, storage ratio, beat scaling |
| 25 | `docs(spec): build v1.5 and archive v1.4` | 54 pages, 42 tables |
| 26 | `docs(review): v1.6 candidates` | Six open findings, two of them verification debt |
| 27 | `docs: changelog, README, index and worklog for v1.5` | Version line, reading order, this section |

**The check caught a false claim in the prose.** §5.9.4 originally said the VFR map is "non-decreasing but not strictly increasing". On the worked example it is strictly increasing — each successive native frame maps to a larger conformed frame. What is true is narrower and more interesting: the map is *injective but not surjective*, so the image skips a conformed index, and the map is only non-decreasing in general because two packets can share a timestamp. The assertion now tests both facts, including the shared-timestamp case, and the paragraph says what is true.

That is the second time a figure check has found an error in the sentence it was written to support rather than in the number. The first was Python's `round()` being half-to-even.

## 2d. The v1.6 round

v1.6 is the first version with an executable counterpart. Two things drove it: the document asserts behaviour and nothing executed it, and the sixth review asked for the fixture §5.9.4 had named but never produced.

`tests/` is deliberately not the engine. It is the smallest code that can be wrong in the same way the document can be — exact rationals, both conform maps, the speed cascade, the handle conversions, the source-to-record transform, the duration ladder, the erasure deadline, tiered egress — and 29 tests that assert every worked example in the document, each naming its section.

| # | Commit | What it did |
|---|---|---|
| 34 | `test: add the conformance suite` | `spec_rules.py`, `test_conformance.py`, `vfr_fixture.py` — 29 tests, no dependencies, under a quarter of a second |
| 35 | `docs(spec): add the v1.6 source` | 28 anchored edits; two new subsections (§5.9.5, §19.1) |
| 36 | `build: extend both checkers` | 85 figure assertions; four consistency checks including code-fence balance |
| 37 | `docs(spec): build v1.6 and archive v1.5` | 59 pages, 43 tables |
| 38 | `docs(review): v1.7 candidates` | Six findings, three created by this version |
| 39 | `docs: release notes for v1.6` | Changelog, version line, reading order, this section |

**Three defects the suite and the render caught, in the order they appeared.**

The audio handle rule was invisible until a test converted the same boundary twice: `samplesFor(12)` is 19,219 and `2 × samplesFor(6)` is 19,220. One sample, one truncated fade, no error. §5.7 now states the rule and the test asserts both numbers, so a future simplification that reintroduces the double rounding breaks a test rather than a render.

An insertion in §5.7 closed one code fence and opened another without consuming the original closing fence. The document still parsed as markdown; the build produced nine tables instead of forty-three, and every page after that point rendered as monospace. The consistency checker now fails on an unbalanced fence, and on a "code" block that contains a heading — the precise signature of a fence that went missing.

The §0 caption had been reading "Fourth-review findings" since v1.5, because the caption and the rows were replaced by separate edits and only one of them moved. The checker now derives the expected ordinal from the version number.

**One test expectation was wrong and one claim was imprecise.** A duration-ladder case labelled "-2.0%" was actually 2.0015% and belonged in the repair band; and the precision rule quoted a specific ratio's drift (3.7 is exact at two decimals, so it drifts zero) where it needed the bound — 10⁻ᵈ × N samples. Both are recorded because they are the same lesson: a test that agrees with a wrong number is worse than no test.

## 2e. The v1.7 round

v1.7 is where the document's own example was compiled rather than described, and the compiler disagreed with the document within the hour.

| # | Commit | What it did |
|---|---|---|
| 40 | `test: add the reference compiler and golden graph` | `tests/compiler.py`, `tests/golden/appendix_a.graph`, 12 tests |
| 41 | `test: test the VFR threshold either side` | `near_threshold()` and the 0.9/1.0/1.1 per cent cases |
| 42 | `ci: run all four checks on every push` | `.github/workflows/verify.yml`, including the round trip from the `.docx` |
| 43 | `docs(spec): add the v1.7 source` | 19 anchored edits; §5.9.5's sibling work, the erasure schema, the scoped composite-key rule |
| 44 | `build: add the migration checker` | `build/check_sql.py` — parses the DDL, checks tenant keys and RLS coverage |
| 45 | `fix(build): a blank line ended a code block on extraction` | The extractor had truncated every listing with a blank line since v1.1 |
| 46 | `docs(spec): build v1.7 and archive v1.6` | 59 pages, 43 tables, 17 tables in the migration |
| 47 | `docs: release notes for v1.7` | Changelog, version line, this section |

**Four defects found, none by the checks that existed before this round.**

The compiler multiplied the source span by speed instead of the record duration — the exact confusion §5.9.3 exists to prevent, in code written from the section that prevents it. It produced 538 frames where 626 was right, and every rule-level test in the suite passed throughout.

The migration header still said "schema, v1.4", three versions after it stopped being true, because the string lived inside a code block where no version check looked.

The `erasures` table was added to §13.3 and not to the RLS loop in §14.1 — the exact failure §14.1 warns about, introduced by the version that quotes it. The SQL checker now fails on any table with a `tenant_id` that the loop does not name.

And the extractor ended a code block at its first blank line, so every listing with a blank line had been silently truncated since v1.1. Six versions of round-trip checks were weaker than they appeared, and the migration check found it by reporting zero tables where the source had seventeen.

**The lesson is the same one, one layer out.** v1.6's suite tested the rules and said nothing about the translation. v1.7's compiler tests the translation and says nothing about the packaging. Each layer of checking makes the next layer's absence visible, and the visible absence is always the one that was shipping.

## 2f. The v1.8 round

v1.8 is about the artefact. Three of the last four versions shipped a defect that only a rendered page or a round trip could see — a split table row, a build that produced nine tables instead of forty-three, a caption two versions stale — and each was found by looking rather than by checking. This round turned looking into checking.

| # | Commit | What it did |
|---|---|---|
| 50 | `test: extend the compiler to the operations Appendix A omits` | Transform, fade, title, tone-map, wipe alignment; four goldens, nine tests |
| 51 | `build: make the .docx byte-reproducible` | Normalised package: fixed timestamps, sorted parts |
| 52 | `test: add the packaging suite` | Round trip, build determinism, rendered page — 10 tests |
| 53 | `docs(spec): add the v1.8 source` | 15 anchored edits; the break-even, the 16× decision, §19.1 covering the new layers |
| 54 | `ci: run the layout check on main` | A second job, because LibreOffice costs two minutes |
| 55 | `docs(spec): build v1.8 and archive v1.7` | 59 pages, 43 tables, 69 tests |
| 56 | `docs: release notes for v1.8` | Changelog, version line, this section |

**What the new layers found immediately.** The migration checker caught its own header drift — the SQL comment said v1.7 while the document said v1.8, which is the defect that checker was written for, on the first version that used it. And the first golden file had to be regenerated because the wipe work changed `offset=0` to `offset=0.000000`; that is the golden mechanism working as designed, and it is also finding 3 of the v1.9 list, because nothing records *why* a golden changed beyond a commit message.

**The proportion has shifted.** v1.6 and v1.7 closed defects — wrong rules, wrong code. v1.8 closed the distance between a document and its artefact. Four of the six remaining findings are verification debt: the rule is right and the reference implementation does not yet reach it. That is a different kind of unfinished, and the list says so rather than calling everything a bug.

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
| Colour management and LUTs are specified and not compiled | `reviews/v1.9-candidates.md` §1 | Any IR carrying a `lut` effect — it raises rather than rendering |
| The layout check skips silently without LibreOffice | §2 | A contributor's machine reporting success while running nothing |
| The golden files have no reviewer | §3 | Knowing why a graph changed, not just that it did |
| The break-even uses one rate for committed capacity | §4 | Pricing at any other commitment rate |
| `_tonemap` assumes an SDR project and an HLG or PQ source | §5 | SDR source on an HDR timeline |
| The compiler emits no `amix` for a multi-track audio bus | §6 | Any timeline with music and dialogue |

Nothing in that list is architectural. Four are verification debt — the rule is right and the reference implementation does not yet reach it — and two are consequences of v1.7's own work — the compiler covers what the golden file exercises, and the migration check found the extractor bug. Roughly half of every list since v1.4 has been created by the previous fix, which remains the strongest argument in this repository for keeping the list separate from the specification.

## 5. Conventions this repository follows

- One commit per step, imperative mood, a body that says why rather than what.
- The `.docx` is authoritative; the markdown is generated and never hand-edited.
- A superseded version is archived, never deleted.
- A withdrawn claim is withdrawn in the text, not removed.
- Open findings live outside the specification.
- Every figure is computed or labelled an assumption. Nothing is typed twice.
