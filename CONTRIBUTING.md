# Working on this repository

The specification is the product. Everything here exists to keep it correct, reviewable and honest about what it has not solved.

## The one rule that governs everything

**A number in the document is either computed or labelled an assumption.** No figure is typed twice. If you change a number, change `build/check_figures.py` in the same commit, or the check will fail — which is the point.

```bash
python build/check_figures.py docs/spec/v1.4.md       # the arithmetic
python build/check_consistency.py docs/spec/v1.4.md  # everything that is not arithmetic
```

Run both before every commit. Together they take under a second, and between them they have caught six real defects: a rounding rule that disagreed with Python's `round()`, a fleet-size calculation that used truncated stream counts, a speed schema that contradicted the wire format, three overlapping determinism rows, a finding count that disagreed with its own table, and a requirement table with two FR-15 rows.

## How a version is cut

A version is not an edit; it is a response to a review. The order is fixed, and doing it in this order is what stops a version from changing things nobody asked about.

1. **Read the whole document.** Every section, before forming a finding. A finding drawn from a partial read is a false finding, and one false finding discredits the whole table.
2. **Find defects in four passes** — arithmetic, domain and units, contract against mechanism, cross-reference and count drift. `skills/technical-spec-versioning/references/finding-taxonomy.md` lists the twelve classes with examples.
3. **Write the §0 table first**, before any prose. One row per finding: finding, what was wrong, resolution in this version. Sort by severity, not by section order.
4. **Write the version as a full standalone document.** Carry forward unchanged sections; a patch set forces the reader to hold two documents. For each change, state the old behaviour, why it was wrong, the new rule, and the arithmetic.
5. **Verify.** Run the figure check. Withdraw claims explicitly rather than deleting them — a reader who saw the previous version needs to know the promise is gone.
6. **Update** `CHANGELOG.md`, move resolved rows out of `docs/reviews/vN-candidates.md`, and add the new `.docx` to `docs/spec/`.

## How a finding is proposed

A finding is welcome when it cites a section and either an arithmetic error or two rules that cannot both hold.

| Good finding | Not a finding |
|---|---|
| "§5.6's answer is in native frames; the compiler decodes conformed frames. For 25 fps on 29.97 that is 250 against 300." | "The time model is fragile." |
| "§13.2 requires `UNIQUE (tenant_id, id)` on every tenant table; §13.3 lists two that lack it." | "Tenancy could be better." |
| "§12.3 packs 2.77 streams per L4; §20 prices one job owning the card. The ratio is 1.85×." | "The cost model seems optimistic." |

The pattern: **a section number, plus something checkable.** Proposals are welcome in the same shape — what changes, and whether it changes the IR or the tool surface, because those need a version bump rather than an edit.

## Conventions

**Commits.** One step per commit, imperative mood, a scoped prefix, and a body that says why:

```
docs(spec): add v1.3 specification (artefact of record)

The canonical document. Executable contracts and corrected figures:
BigInt wire format, a complete migration, P010 frame sizes.
```

Prefixes in use: `docs(spec)`, `docs(engine)`, `docs(review)`, `docs`, `build`, `skill`, `chore`.

**The .docx is the artefact of record.** Never hand-edit `docs/spec/v1.3.md` and expect it to survive: regenerate it with `build/extract_spec.py`. If a change belongs in the spec, it goes into the `.docx` and is extracted from there.

**Archive, never delete.** A superseded version moves to `archive/` unedited. A withdrawn claim stays visible in the version that made it.

**Open findings stay out of the specification.** They live in `docs/reviews/`. This is a rule about trust: the spec must be firm, and the debt must be countable.

## What not to do

- Do not add a performance figure as though it were measured. Use the evidence-status column (§12.3 of the spec) and say which of measured, vendor-specified, derived, assumed or target it is.
- Do not add an enum value to the IR without a compiler implementation, a fixture and a test. An enum value is a promise the compiler keeps.
- Do not let a preview be described as pixel-identical to a final. Edit decisions and timing are identical by contract; pixels are not, by design.
- Do not resolve a hard constraint by proceeding without it. A timeout is not consent.

## Licence

All rights reserved. Contributions are accepted by invitation; open an issue rather than a pull request unless asked.
