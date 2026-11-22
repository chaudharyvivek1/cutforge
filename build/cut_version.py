#!/usr/bin/env python3
"""Cut a version in one command, instead of twelve steps by hand.

The padding audit found the real overhead of this project was not prose: it
was the ceremony around each version — copy the source, renumber the tables,
run three checkers, build the docx, extract it back and check it again, then
stage five commits by hand. Every one of those steps is mechanical, and
mechanical steps done by hand are how a history gets a commit that silently
did not happen.

Usage:
    python build/cut_version.py 2.18 --title "..."        # prepare and verify
    python build/cut_version.py 2.18 --commit             # then stage and commit

What it does not do: write the prose. §0, the findings table and the release
notes are judgement, and a tool that guessed them would produce exactly the
padding this exists to remove.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs" / "spec"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kw)


def latest_source():
    sources = sorted(SPEC.glob("v*.md"), key=lambda p: [int(x) for x in p.stem[1:].split(".")])
    if not sources:
        sys.exit("no spec source found in docs/spec")
    return sources[-1]


def renumber(text):
    """Tables and listings numbered from zero and one, in document order.

    A hand-inserted row shifts every number after it, and two versions shipped
    with a duplicate because of it. This is the fix, and it is why the step
    belongs in a tool.
    """
    lines = text.split("\n")
    table = listing = 0
    for i, line in enumerate(lines):
        m = re.match(r"^Table (\d+)  \|", line)
        if m:
            lines[i] = re.sub(r"^Table \d+  \|", f"Table {table}  |", line, count=1)
            table += 1
            continue
        m = re.match(r"^Listing (\d+)  \|", line)
        if m:
            listing += 1
            lines[i] = re.sub(r"^Listing \d+  \|", f"Listing {listing}  |", line, count=1)
    return "\n".join(lines), table, listing


def check(path, label):
    ok = True
    for script, args in (("check_figures.py", [str(path)]),
                         ("check_consistency.py", [str(path)]),
                         ("check_sql.py", [str(path)])):
        result = run([sys.executable, f"build/{script}", *args])
        if result.returncode != 0:
            ok = False
            print(f"  FAILED {label}: {script}")
            print("   " + (result.stdout or result.stderr).strip().splitlines()[-1])
        else:
            print(f"  ok {label}: {script}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("version")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--from", dest="source", default=None)
    args = ap.parse_args()

    source = Path(args.source) if args.source else latest_source()
    target = SPEC / f"v{args.version}.md"
    if target.exists():
        sys.exit(f"{target.name} already exists — nothing to cut")
    text = source.read_text(encoding="utf-8")
    text = text.replace(f"VERSION {source.stem[1:]}", f"VERSION {args.version}")
    # The front-matter row and the title line are mechanical; the checker
    # refuses a document whose row disagrees with its own version, which is
    # what caught a hand-cut version shipping with a stale row.
    text = re.sub(r"\| Document \| Technical design specification, v[\d.]+ "
                  r"\(supersedes v[\d.]+\) \|",
                  f"| Document | Technical design specification, v{args.version} "
                  f"(supersedes v{source.stem[1:]}) |", text)
    text, tables, listings = renumber(text)
    target.write_text(text, encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)} — {tables} tables, {listings} listings")

    if not check(target, "source"):
        sys.exit("source checks failed; the prose edits are not finished")

    docx = SPEC / f"AI_Video_Editor_Architecture_v{args.version}.docx"
    built = run([sys.executable, "build/build_docx.py", str(target), str(docx), "docs/spec"])
    if built.returncode != 0:
        sys.exit("docx build failed: " + built.stderr.strip()[-400:])
    print(f"built {docx.name}")

    extracted = ROOT / "work" / "roundtrip.md"
    extracted.parent.mkdir(exist_ok=True)
    run([sys.executable, "build/extract_spec.py", str(docx), str(extracted),
         str(extracted.with_suffix(".assets"))])
    if not check(extracted, "round trip"):
        sys.exit("the artefact does not match its source")

    print("\nready. Remaining, and deliberately not automated:")
    print("  §0 prose and the findings table")
    print("  CHANGELOG, RELEASES, README, docs/README, docs/worklog, ROADMAP")
    print("  docs/reviews/vX-candidates.md")
    if args.commit:
        print("\n--commit given, but the prose above is not written; commit by hand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
