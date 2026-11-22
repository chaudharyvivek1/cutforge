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
    vm = re.search(r"VERSION (\d+\.\d+)", text)
    version = vm.group(1) if vm else None
    if not version:
        fail("no VERSION string in the eyebrow line")
    else:
        esc = re.escape(version)
        for pattern, label in [
            (rf'"\$id": "https://spec\.example/timeline/{esc}\.json"', "$id"),
            (rf'"schema": \{{ "const": "timeline/{esc}" \}}', "schema const"),
            (rf'"schema": "timeline/{esc}"', "Appendix A schema"),
            (rf"schema: timeline/{esc}\b", "Appendix A validation line"),
            (rf"v{esc} \(supersedes v\d+\.\d+\)", "front-matter document row"),
        ]:
            if not re.search(pattern, text):
                fail(f"version {version}: {label} missing or mismatched")
        for other in set(re.findall(r"timeline/(\d+\.\d+)", text)):
            if other != version:
                fail(f"IR version drift: timeline/{other} appears in a {version} document")

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
