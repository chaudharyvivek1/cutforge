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
| v1.9 | Ninth technical review | "Rules and artefact proved; now the implementation" | LUTs compiled (§11.4), colour in both directions (§12.6), a mixed audio bus (§11.1), golden provenance (§19.1), the break-even as a formula (§20.3), and a layout check that cannot pass by skipping |
| v2.0 | Tenth technical review | "The rules are right; now produce a frame" | A renderer under frame hashes (§19.1), the template planner (§7.6), the identity state machine (§8.5), an OTIO round trip (§11.7), colour in both directions (§11.4), and document/IR versions separated |
| v2.1 | Eleventh technical review | "The engine must run, not just compile" | A job service (§15, §17, §18), the repair loop (§7.4), the compiler's own fixtures rendered (§19.1), accuracy and colour harnesses (§8.6, §11.4), and §11.7 narrowed to what is built |
| v2.2 | Twelfth technical review | "The engine must survive a restart" | A durable store and worker (§18), content-sensitive render fixtures (§19.1), the repair band closed (§7.7), a corpus contract (§8.6), a perceptual fallback (§11.8), and overlays scheduled (§21) |
| v2.3 | Thirteenth technical review | "The engine must stop cleanly" | Retry by class and quarantine (§18), acrossfade measured to the sample (§11.5), a corpus pipeline that runs (§8.6), a recorded fingerprint (§11.8), and the duplicate state machine deleted (§15) |
| v2.4 | Fourteenth technical review | "The queue must behave" | Fairness across tenants (§17), backoff with jitter (§18), the DDL state fixed and checked (§13.3), the acrossfade content pinned (§11.5), overlays withdrawn (§11.7), the synthetic corpus guarded (§8.6) |
| v2.5 | Fifteenth technical review | "The surface must be defended" | Authorisation from a token (§14.5), Prometheus metrics (§17), signed webhooks (§15.3), a GPU benchmark workflow (§12.9), a plan corpus (§7.1) |
| v2.6 | *Not started* | — | The six open findings in `docs/reviews/v2.6-candidates.md` — tokens never expire |

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

## 2g. The v1.9 round

v1.9 is the first version where the list contained nothing but verification debt — the rule was right and the reference implementation had not reached it. The work was therefore mostly code, and two of the six were real bugs rather than coverage.

| # | Commit | What it did |
|---|---|---|
| 58 | `feat(test): colour in both directions, LUTs, and a mixed audio bus` | `lut3d`, an inverse map for SDR-on-HDR, tone-map settings from the manifest, `amix` + `loudnorm` |
| 59 | `test: three more goldens and a provenance table` | `lut`, `audio_mix`, `sdr_to_hdr`, and `tests/golden/README.md` with a test that keeps it complete |
| 60 | `ci: fail when the layout job skips` | The skip reason names what did not run, and the job greps for it |
| 61 | `docs(spec): add the v1.9 source` | 21 anchored edits |
| 62 | `docs(spec): build v1.9 and archive v1.8` | 61 pages, 43 tables, 85 tests |
| 63 | `docs: release notes for v1.9` | Changelog, version line, this section |

**The audio bug was the one worth catching.** v1.8's compiler emitted one chain per audio item and never mixed them, so a timeline with a music bed and dialogue produced two streams and the renderer would take the first. That ships as "the music is missing" and gets diagnosed as a file problem. The fix is four lines and the test is a two-track fixture — but nothing would have found it without a fixture that had two tracks, which is the same lesson as the Appendix A compiler test one version earlier.

**The tone-map constants were the second.** `_tonemap` held `hable` and 100 nits as literals, which contradicts the reason §11.6 records them: a render is reproducible only if the tone map it used is recorded, and a constant in the compiler is not a record. The settings now come from `metadata.tonemap`, and a test asserts the manifest wins.

**Where the repository now stands.** The document has no known contradiction in it, the tooling proves the document, and the reference implementation reaches the filter graph. What it does not reach is a pixel. That is the whole of the v2.0 list, and it is the right next thing: eight golden graphs prove that the compiler says what it means, and nothing yet proves that ffmpeg does what the graph says.

## 2h. The v2.0 round

v2.0 is the first version whose reference implementation produces frames. Everything before it proved a string; a filter graph can be syntactically perfect and semantically wrong, and four versions of checking had no way to tell.

| # | Commit | What it did |
|---|---|---|
| 65 | `feat(test): render a graph and hash its frames` | `tests/renderer.py` — ffmpeg execution, pre-encode hashing, the build recorded beside the hash |
| 66 | `feat(test): the template planner` | `tests/planner.py`, three golden plans, eight tests |
| 67 | `feat(test): the identity state machine and the OTIO round trip` | `tests/identity.py`, `tests/otio_export.py` |
| 68 | `build: separate the document version from the IR version` | Two versions, two checks — conflating them was a tooling defect |
| 69 | `docs(spec): add the v2.0 source` | 17 anchored edits |
| 70 | `ci: install ffmpeg and refuse silent skips` | No test may skip; layout runs on pull requests |
| 71 | `docs(spec): build v2.0 and archive v1.9` | 61 pages, 114 tests |
| 72 | `docs: release notes for v2.0` | Changelog, version line, this section |

**The renderer cost an afternoon and answered the question the last four versions could not.** Two fixtures — a cut and a dissolve — execute through ffmpeg and hash to `7d9ee871…` and `5239025b…`. The hash is taken on raw frames *before* the encoder, which is the split §11.8 makes: compiler determinism is a property of the graph, delivered-byte reproducibility is a property of a pinned encoder. Each hash is stored beside the ffmpeg build that produced it, so a mismatch reports both builds rather than a mystery — §11.6's rule applied to the repository itself.

**The version split was a defect worth naming.** Every checker until v2.0 required the document version and the IR version to be equal. That is wrong, and it forced a choice between shipping a misleading major number and breaking a schema that did not need breaking. The two are now separate: `VERSION 2.0` and `timeline/1.9`, stated in the front matter, checked for internal consistency and not for equality.

**What is still not proven.** The renderer hashes two graphs written as literals in the test, not the compiler's own output — the golden fixtures reference assets the repository does not carry. And nothing has ever run as a service: no API, no queue, no worker, no cancellation. Both are at the top of the v2.1 list, and both are the same kind of honesty this repository has been practising since v1.4 — name the gap precisely enough that someone can close it.

## 2i. The v2.1 round

v2.1 made the engine run. Two things had never happened before it: a graph had never been opened by ffmpeg from the compiler's own output, and a job had never been submitted to anything.

| # | Commit | What it did |
|---|---|---|
| 73 | `fix(compiler): fold the track into a final output label` | The graph had no `[v_out]`; transitions were emitted and never joined |
| 74 | `test: generate conformed assets and render the fixtures` | `tests/assets.py`; Appendix A and the audio bus compiled and hashed |
| 75 | `feat(test): a job service with a hold and a cancellation` | `tests/service.py` — HTTP, idempotency, tenant-scoped 404, terminal states |
| 76 | `feat(test): the repair loop and its budgets` | `tests/repair.py` — three named outcomes |
| 77 | `feat(test): accuracy and colour harnesses` | `tests/accuracy.py`, `tests/colour.py` |
| 78 | `docs(spec): add the v2.1 source` | 17 anchored edits; §11.7 narrowed to what is built |
| 79 | `docs(spec): build v2.1 and archive v2.0` | 61 pages, 140 tests |
| 80 | `docs: release notes for v2.1` | Changelog, version line, this section |

**The render found the bug in the first minute.** v2.0's renderer hashed two graphs written as string literals, both ending in `[v_out]`. The compiler's own output ended in `[xf_4]` — it emitted one xfade per transition and never joined them, so ffmpeg refused to open the graph: "Output with label 'v_out' does not exist". Eight golden files, 114 tests and three checkers had nothing to say about it, because a graph is only wrong when something executes it.

The fix exposed a second thing worth recording. With the fold in place the render failed again, on an xfade timebase mismatch — because the fixtures were at native rates and §5.9.2 says the compiler consumes *conformed* frames. Generating the assets at project rate was not a workaround; it was the model, and getting it wrong put ingest's job inside the compiler.

**The service is a reference, not a product.** One dictionary, one thread, no queue, no persistence, no worker that can die. What it proves is the part that costs a customer when it is wrong: that a retried submission returns the original job, that another tenant gets a 404 rather than a 403, that an unanswered hold expires to failed, that an accepted degraded result is recorded, and that a cancellation cannot be revived.

**Two tolerances became functions.** §8.6's accuracy targets now have a harness that a test can prove is looking at something, and §11.4's colour matching has a number — ΔE 2.0 — with a test that a two per cent gain passes and a twenty per cent one fails.

## 2j. The v2.2 round

v2.2 is the first version whose state survives a process. Everything before it lived in memory, which meant §18's claims about checkpointing and cooperative cancellation were descriptions of a design nobody had run.

| # | Commit | What it did |
|---|---|---|
| 81 | `feat(test): a durable job store and a worker that resumes` | SQLite, exclusive claim, per-segment checkpoint, orphan requeue |
| 82 | `test: make the render fixtures content-sensitive` | Four distinct animated patterns, and a test that swapping inputs changes the hash |
| 83 | `feat(test): the repair band, the corpus contract and a perceptual fallback` | `plan_short`, `corpus.py`, `renderer.perceptual()` |
| 84 | `docs(spec): add the v2.2 source` | 17 anchored edits |
| 85 | `docs(spec): build v2.2 and archive v2.1` | 61 pages, 157 tests |
| 86 | `docs: release notes for v2.2` | Changelog, version line, this section |

**A fixture that cannot tell its inputs apart is measuring nothing.** v2.1's assets shared two patterns between four clips, so a compiler that swapped two inputs would have produced the same hash — and the hash is the only thing standing between a graph and a silent mis-edit. The fix is four distinct animated patterns, plus a test that asserts swapping two inputs *changes* the hash. That test is worth more than the hash it protects, because it is the one that would notice if the fixture went flat.

**The repair band had never been exercised.** The template planner is correct first time, so `repair.run` only ever saw a structure broken by hand — which proves the control flow and nothing about closing a 3% shortfall. `plan_short()` under-delivers by a known amount, and the validator now flags the repair band rather than only the fallback band: a 3% deficit is exactly what the loop exists for, and a validator that calls it acceptable leaves the loop with nothing to do.

**And the round created its own next finding.** `tests/service.py` still uses the in-memory `JobStore` while `tests/store.py` uses SQLite, so the same state machine now exists twice. That is the pattern this repository has documented since v1.4, stated in one line: *the fix creates the next finding, and the next finding is always a second copy of something that should have one.*

## 2k. The v2.3 round

v2.3 is the first version whose main change was a deletion. `service.JobStore` and `store.Store` each implemented the same state machine, so the HTTP layer — the one a client sees — was the one that did not survive a restart. Deleting the first fixed a divergence that no test could have caught while both existed.

| # | Commit | What it did |
|---|---|---|
| 87 | `feat(store): retry by failure class, then quarantine` | A permanent failure is not retried; three identical transient failures quarantine |
| 88 | `fix(service): run on the durable store and delete the duplicate` | One state machine, one set of invariants |
| 89 | `feat(compiler): acrossfade per audio track` | §5.7's audio handle rule meets ffmpeg |
| 90 | `test: measure the crossfade, load the corpus, record the fingerprint` | 941,741 samples asserted exactly; a synthetic corpus that runs end to end |
| 91 | `docs(spec): add the v2.3 source` | 14 anchored edits |
| 92 | `docs(spec): build v2.3 and archive v2.2` | 61 pages, 165 tests |
| 93 | `docs: release notes for v2.3` | Changelog, version line, this section |

**A retry counter is not a retry policy.** v2.2 requeued every orphan unconditionally, so a job that crashed the process would loop forever — the failure §18 names as poison. The fix distinguishes the classes: a transient failure may heal, a corrupt source does not, and a budget that is exhausted does not refill. Three identical transient failures quarantine the job, and a quarantined job is never claimed again.

**And the round produced the pattern again.** Adding `quarantined` to the store did not add it to §13.3's `jobs.state` CHECK, so a real Postgres deployment would reject the update the reference implementation now performs. That is precisely what v1.3's §0 accused v1.2 of — code and schema drifting apart — reappearing in the version that added a quarantine. It is finding 3 of the v2.4 list, and the proposed fix is to compare the two lists in CI rather than in review.

**What the crossfade proved.** Two clips, a 12-frame dissolve, 588 frames: the decoded audio is 941,741 samples, which is `samplesFor(588)` exactly. §5.7's handle rule and §11.5's acceptance test met in one fixture for the first time — and it is the only fixture where either can be wrong in a way a hash would miss.

## 2l. The v2.4 round, and the audit before it

v2.4 was preceded by a full audit of the code and the tests, which found seven defects that no version's review had caught. Six were small. One would have cost a render.

| # | Commit | What it did |
|---|---|---|
| 94 | `fix: seven defects from the audit` | Duplicate function, zero-lease requeue, a vacuous test, a hash where bytes were needed, dead imports, a dead state, a mis-keyed ordinal map |
| 95 | `feat(store): fairness, backoff and a lease` | Per-tenant cap, exponential delay with per-job jitter, 30-second lease |
| 96 | `fix(spec): the DDL learns the quarantined state` | And `check_sql.py` compares it against the code |
| 97 | `docs: licence, releases, and the repository's own description` | Three documents the repository was missing |
| 98 | `docs(spec): add the v2.4 source` | 15 anchored edits |
| 99 | `docs(spec): build v2.4 and archive v2.3` | 61 pages, 174 tests |
| 100 | `docs: release notes for v2.4` | Changelog, version line, this section |

**The audit found what review does not.** `pyflakes` reported eight things and seven were real, including a second definition of `_fps` in the planner that silently shadowed the first — the same function, written twice, which is the repository's recurring defect in miniature. The one that mattered most was `requeue_orphans(older_than=0.0)`: the default requeued *every* running job on every sweep, including one a live worker was rendering, so two workers could write the same output. The fix is a 30-second lease, and the test that would have caught it now exists.

**And a test that could not fail.** `test_the_graph_and_the_pixels_agree_on_length` asserted that `"frame="` appeared in ffmpeg's stderr — true of every run, including a broken one. It now counts frames from the decoded bytes, and asserts that a dissolve costs its overlap: 48 frames for two 24-frame clips, 36 with a 12-frame fade.

**The schema drift arrived on schedule.** v2.3 added `quarantined` to the store and not to §13.3's CHECK, so a real Postgres would reject the update. That is exactly what v1.3's §0 accused v1.2 of, and the fix is a checker rather than a resolution: `build/check_sql.py` now compares the DDL's state list against `store.TERMINAL`, so the next drift fails the build. The dead `expired` state was removed from the code rather than added to the schema — a state with no path to it is not a state.

**Three documents the repository lacked.** `LICENSE` (all rights reserved, with a note on how to switch to MIT or Apache-2.0), `RELEASES.md` (every version, its basis, and what a release means when there is no binary), and `docs/repo/description.md` (the description, topics, scope and the five claims worth checking — kept in the repository because metadata in a web form is metadata nobody reviews).

## 2m. The v2.5 round

v2.5 built the three things a service has that a library does not: authorisation, telemetry and signed delivery. It also fixed a documentation defect that had been growing since v1.4.

| # | Commit | What it did |
|---|---|---|
| 101 | `feat(auth): the tenant comes from a token` | `Principal`, `Tokens`, and `resolve()` with the narrow-never-widen rule |
| 102 | `feat(metrics): expose the five signals the store can produce` | Prometheus text at `/metrics`, no dependency |
| 103 | `feat(webhook): sign timestamp.body, not the body` | HMAC with a five-minute replay window in both directions |
| 104 | `feat: a plan corpus and a GPU benchmark workflow` | Replay for §7.1's target; a matrix job that records hardware beside throughput |
| 105 | `docs(spec): add the v2.5 source` | 13 anchored edits, including a §0 rewritten to describe this version |
| 106 | `docs(spec): build v2.5 and archive v2.4` | 61 pages, 197 tests |
| 107 | `docs: release notes for v2.5` | Changelog, version line, this section |

**The security defect was four versions old.** `X-Tenant` decided the tenant, which meant the isolation tests were a test between two values the client had chosen — and the test suite was a worked example of the wrong pattern. The fix is a principal derived from a bearer token, a header that may narrow and never widen, and two different answers: 403 for an authenticated override attempt, 404 for a cross-tenant read, because one is a refusal and the other must not disclose existence.

**§0 had become a changelog.** By v2.5 the "what changed in this version" section explained v1.1, the conform map and the audio handle rule — six versions of prose accumulating one paragraph at a time, burying the change a reader came for. It now carries the current version only; the table below it carries the history. That is a documentation defect the audit found, and the kind that no checker could: the numbers were right and the section was wrong.

**And the workflow reproduced a fixed failure.** `benchmark.yml` needs a runner labelled `gpu` that does not exist, so it queues and never runs — the same shape as a test that skips, which v1.8 fixed for the layout checks. It is listed as a finding rather than quietly left in CI.

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
| Tokens never expire, rotate or revoke | `reviews/v2.6-candidates.md` §1 | Any credential lifecycle — the store is a dictionary |
| No rate limiting or abuse controls | §2 | Back-pressure that refuses rather than delays |
| Metrics cover the store and not the worker | §3 | GPU memory, encoder utilisation, heartbeat age |
| Webhook delivery has no loop, retry or dead-letter | §4 | At-least-once delivery, which §15.3 promises |
| The benchmark workflow has no runner | §5 | Any measured throughput figure |
| The identity corpus has no real data | §6 | Any accuracy claim |

Nothing in that list is architectural. Three are consequences of v2.5's own work — the renderer proves a graph rather than the compiler's graph, and the planner exists without the loop that drives it — and the largest is that nothing has ever run as a service — the compiler covers what the golden file exercises, and the migration check found the extractor bug. Roughly half of every list since v1.4 has been created by the previous fix, which remains the strongest argument in this repository for keeping the list separate from the specification.

## 5. Conventions this repository follows

- One commit per step, imperative mood, a body that says why rather than what.
- The `.docx` is authoritative; the markdown is generated and never hand-edited.
- A superseded version is archived, never deleted.
- A withdrawn claim is withdrawn in the text, not removed.
- Open findings live outside the specification.
- Every figure is computed or labelled an assumption. Nothing is typed twice.
