#!/usr/bin/env python3
"""Consistency checks that are not arithmetic.

check_figures.py proves the numbers. This proves the things that are wrong
in a different way: a version string in one place and not another, an enum
in the schema that the appendix disagrees with, a count in the front matter
that the table below it contradicts, numbering that skips or repeats.

Every check here exists because that defect has actually occurred.

Usage:
    python build/check_consistency.py [<spec.md>]
"""
import re
import sys
from pathlib import Path

def newest_spec():
    """The current specification, found rather than hardcoded.

    A hardcoded default goes stale the moment a version is archived, and a
    default that is never exercised because every call passes an argument is
    a default nobody notices is wrong. This one is checked by
    check_consistency.py, which fails if any script points at a missing file.
    """
    candidates = sorted(Path("docs/spec").glob("v*.md"),
                        key=lambda p: [int(x) for x in p.stem.lstrip("v").split(".")])
    if not candidates:
        raise SystemExit("no specification found in docs/spec")
    return candidates[-1]


FAILURES = []


def fail(msg):
    FAILURES.append(msg)


def is_separator(line):
    return set(line.replace("|", "").strip()) <= set("-: ")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else newest_spec()
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    repo = path.resolve().parent.parent.parent

    # ---------------------------------------------------------- version strings
    # The document version and the IR version are different things, and
    # conflating them was a tooling defect: a document can ship a major
    # version without breaking the schema. The IR version must be consistent
    # with itself and stated in the front matter; it need not equal the
    # document version.
    vm = re.search(r"VERSION (\d+\.\d+)", text)
    version = vm.group(1) if vm else None
    if not version:
        fail("no VERSION string in the eyebrow line")

    stated_ir = re.search(r"\| IR version \| timeline/(\d+\.\d+)", text)
    ir_versions = set(re.findall(r"timeline/(\d+\.\d+)", text))
    if not stated_ir:
        fail("front matter does not state an IR version")
    elif len(ir_versions) != 1 or ir_versions != {stated_ir.group(1)}:
        fail(f"IR version drift: front matter says {stated_ir.group(1)}, "
             f"document uses {sorted(ir_versions)}")
    else:
        irv = stated_ir.group(1)
        esc = re.escape(irv)
        for pattern, label in [
            (rf'"\$id": "https://spec\.example/timeline/{esc}\.json"', "$id"),
            (rf'"schema": \{{ "const": "timeline/{esc}" \}}', "schema const"),
            (rf'"schema": "timeline/{esc}"', "Appendix A schema"),
            (rf"schema: timeline/{esc}\b", "Appendix A validation line"),
        ]:
            if not re.search(pattern, text):
                fail(f"IR {irv}: {label} missing or mismatched")

    if version:
        esc_v = re.escape(version)
        if not re.search(rf"v{esc_v} \(supersedes v\d+\.\d+\)", text):
            fail(f"front-matter document row does not say v{version}")

    # ----------------------------------------------------------- count agreement
    stated = re.search(r"(\d+) findings resolved", text)
    rows, in_table = 0, False
    for line in lines:
        if line.startswith("| Finding | What was wrong |"):
            in_table = True
            continue
        if in_table:
            if line.startswith("|"):
                if not is_separator(line):
                    rows += 1
            elif not line.strip():
                break
    if not stated:
        fail("front matter does not state a finding count")
    elif int(stated.group(1)) != rows:
        fail(f"front matter claims {stated.group(1)} findings; the table has {rows} rows")

    # --------------------------------------------------------------- enum drift
    def enum_near(anchor, window=600):
        i = text.find(anchor)
        if i < 0:
            return None
        mm = re.search(r'"enum":\s*\[([^\]]+)\]', text[i:i + window], re.S)
        if not mm:
            return None
        return {v.strip().strip('"') for v in mm.group(1).split(",") if v.strip()}

    schema_effects = enum_near('"effect": { "type":"object"')
    b_start = text.find("# Appendix B")
    appendix_effects = None
    if b_start > 0:
        mm = re.search(r'"effect"[^\n]*\n?[^\n]*"enum":\s*\[([^\]]+)\]', text[b_start:], re.S)
        if mm:
            appendix_effects = {v.strip().strip('"') for v in mm.group(1).split(",") if v.strip()}
    if schema_effects and appendix_effects and schema_effects != appendix_effects:
        fail(f"effect enum drift: schema {sorted(schema_effects)} vs appendix {sorted(appendix_effects)}")

    # speed_curve may only appear as history inside §0; the body must not use it.
    body_start = text.find("\n# 1  Executive summary")
    body = text[body_start:] if body_start > 0 else text
    for n, line in enumerate(body.split("\n"), 1):
        if "speed_curve" in line:
            fail(f"speed_curve still used in the body at body line {n}")

    # speed is a rate on the wire, so it must not be a bare integer pair
    if re.search(r'"speed":\s*\{[^}]*"num":\s*\{\s*"type":"integer"', text, re.S):
        fail("speed.num is an integer; §5.1 requires rates to be decimal strings")

    # ------------------------------------- the §0 caption names its own review
    # v1.5 shipped a table captioned "Fourth-review findings" because the
    # caption was replaced separately from the rows and only one of them moved.
    # Keyed on the full version, not the minor digit. v1.0 was the draft, so
    # v1.1 is the first review and v2.4 the fourteenth; a map keyed on "4"
    # called 2.4 the fourth.
    ORDINALS = {
        "1.1": "First", "1.2": "Second", "1.3": "Third", "1.4": "Fourth",
        "1.5": "Fifth", "1.6": "Sixth", "1.7": "Seventh", "1.8": "Eighth",
        "1.9": "Ninth", "2.0": "Tenth", "2.1": "Eleventh",
        "2.2": "Twelfth", "2.3": "Thirteenth", "2.4": "Fourteenth",
    }
    if version:
        want = ORDINALS.get(version)
        if want:
            cap = re.search(r"Table 0  \|  (\w+)-review findings", text)
            if not cap:
                fail("§0 table caption does not name a review ordinal")
            elif cap.group(1) != want:
                fail(f"§0 caption says {cap.group(1)}-review; version {version} is {want}")

    # ------------------------ a derived field must not be stored or accepted
    # §6.2 derives include_trailing_audio; v1.5 stored it as well.
    for n, line in enumerate(lines, 1):
        if "include_trailing_audio" in line:
            if "NOT NULL" in line or '"type":"boolean"' in line.replace(" ", ""):
                fail(f"include_trailing_audio is stored or accepted at line {n}; §6.2 derives it")

    # ------------------------------------------- code fences must balance
    # An insertion that closes a fence and opens another, without consuming
    # the original closing fence, silently turns the rest of the document
    # into one code block. The docx build then reports nine tables instead
    # of forty-three and everything after it renders as monospace.
    fences = [n for n, l in enumerate(lines, 1) if l.strip() == "```"]
    if len(fences) % 2:
        fail(f"unbalanced code fences: {len(fences)} markers, so the document "
             f"has one unclosed block starting at line {fences[-1]}")
    else:
        # A long block is legitimate — the migration is ~280 lines. A block
        # that swallows a heading or a table is not: neither ever appears
        # inside code, so seeing one means a fence went missing.
        for start, end in zip(fences[::2], fences[1::2]):
            for n in range(start, end - 1):
                body = lines[n]
                if body.startswith("# ") or body.startswith("## ") or body.startswith("### "):
                    fail(f"code block from line {start} to {end} contains the heading "
                         f"'{body.strip()[:40]}' at line {n + 1}; a closing fence is missing")
                    break

    # ------------------------------------------------ requirement ID integrity
    # A row inserted in the wrong place once produced two FR-15 rows and a
    # dangling reference. Cheap to check, and it fails loudly.
    fr_ids = [m.group(1) for m in
              (re.match(r"^\| (FR-[0-9]+[ab]?) \|", l) for l in lines) if m]
    if not fr_ids:
        fail("no requirement rows found")
    else:
        dupes = {i for i in fr_ids if fr_ids.count(i) > 1}
        if dupes:
            fail(f"duplicate requirement IDs: {sorted(dupes)}")
        mentioned = set(re.findall(r"\bFR-[0-9]+[ab]?\b", text))
        dangling = mentioned - set(fr_ids)
        if dangling:
            fail(f"references to requirements that do not exist: {sorted(dangling)}")

    # ------------------------------------------------------- numbering integrity
    def check_sequence(pattern, first, label):
        nums = []
        for line in lines:
            mm = re.match(pattern, line)
            if mm:
                nums.append(int(mm.group(1)))
        if not nums:
            fail(f"{label}: none found")
            return []
        expected = list(range(first, first + len(nums)))
        if nums != expected:
            for got, want in zip(nums, expected):
                if got != want:
                    fail(f"{label}: found {got}, expected {want}")
                    break
        return nums

    check_sequence(r"^Table (\d+)  \|", 0, "table numbering")
    check_sequence(r"^Listing (\d+)  \|", 1, "listing numbering")
    figs = check_sequence(r"^Figure (\d+)  \|", 1, "figure numbering")

    for n, line in enumerate(lines):
        if line.startswith("!["):
            nxt = next((l for l in lines[n + 1:] if l.strip()), "")
            if not re.match(r"^Figure \d+  \|", nxt):
                fail(f"image at line {n + 1} is not followed by a Figure caption")

    # --------------------------------------------------- no dead references
    for ref in set(re.findall(r"docs/spec/(v[\d.]+\.md)", text)):
        if not (repo / "docs/spec" / ref).exists():
            fail(f"text references docs/spec/{ref}, which does not exist")
    for script in ("build/check_figures.py", "build/build_docx.py", "build/extract_spec.py"):
        f = repo / script
        if f.exists():
            for ref in set(re.findall(r"docs/spec/(v[\d.]+\.md)", f.read_text())):
                if not (repo / "docs/spec" / ref).exists():
                    fail(f"{script} defaults to docs/spec/{ref}, which does not exist")

    # ---------------------------------------------------------------- report
    print(f"{path.name}: version {version}, {rows} finding rows, {len(figs)} figures")
    if FAILURES:
        print("FAILED:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("Consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
