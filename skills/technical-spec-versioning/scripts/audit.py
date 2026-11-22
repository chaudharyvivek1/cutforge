#!/usr/bin/env python3
"""Audit a repository before cutting a version.

Static analysis, duplicate definitions, stale counts, and tests that cannot
fail. Every check here has caught a real defect in at least one version.

Usage:
    python scripts/audit.py [repo_root]
"""
import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
problems = []


def add(kind, message):
    problems.append((kind, message))


def py_files():
    return [p for pattern in ("**/*.py",)
            for p in ROOT.glob(pattern)
            if ".git" not in p.parts and "archive" not in p.parts]


def check_pyflakes():
    try:
        out = subprocess.run([sys.executable, "-m", "pyflakes", *map(str, py_files())],
                             capture_output=True, text=True).stdout
    except FileNotFoundError:
        return add("skip", "pyflakes is not installed; unused imports were not checked")
    for line in out.strip().splitlines():
        add("static", line)


def check_duplicate_definitions():
    """A second definition of one function silently shadows the first."""
    for path in py_files():
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError as error:
            add("syntax", f"{path}: {error}")
            continue
        seen = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if node.name in seen:
                    add("duplicate", f"{path}:{node.lineno} {node.name} redefined "
                                     f"(first at line {seen[node.name]})")
                seen[node.name] = node.lineno
            if isinstance(node, ast.ClassDef):
                methods = {}
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if item.name in methods:
                            add("duplicate", f"{path}:{item.lineno} {node.name}.{item.name} "
                                             f"redefined (first at line {methods[item.name]})")
                        methods[item.name] = item.lineno


def check_stale_counts():
    """A README that says 197 tests when the suite has 265 is a small lie."""
    numbers = set()
    for md in ROOT.glob("*.md"):
        for m in re.finditer(r"\b(\d{2,4}) tests\b", md.read_text()):
            numbers.add(int(m.group(1)))
    if len(numbers) > 1:
        add("stale", f"documents disagree about the test count: {sorted(numbers)}")


def check_tests_that_cannot_fail():
    """assertTrue(True), assertIn(x, x + y) where y makes it always true."""
    for path in ROOT.glob("tests/**/test_*.py"):
        text = path.read_text()
        for pattern, why in [
            (r"assertTrue\(True\)", "asserts a constant"),
            (r'assertIn\("([^"]+)", [^)]*\+ "\1"\)', "appends the needle to the haystack"),
        ]:
            for m in re.finditer(pattern, text):
                add("vacuous", f"{path.name}: {why}: {m.group(0)[:60]}")


def check_skips():
    """A skipped test is not a pass; count them so they cannot hide."""
    for path in ROOT.glob("tests/**/test_*.py"):
        for m in re.finditer(r"skipUnless\(([^,]+),", path.read_text()):
            add("info", f"{path.name}: conditional on {m.group(1).strip()[:40]} — "
                        f"confirm it is not silently skipping in CI")


def main():
    check_pyflakes()
    check_duplicate_definitions()
    check_stale_counts()
    check_tests_that_cannot_fail()
    check_skips()

    kinds = {}
    for kind, message in problems:
        kinds.setdefault(kind, []).append(message)
    for kind in ("syntax", "duplicate", "vacuous", "static", "stale", "info", "skip"):
        for message in kinds.get(kind, []):
            print(f"[{kind}] {message}")
    blocking = sum(len(kinds.get(k, [])) for k in ("syntax", "duplicate", "vacuous", "static"))
    print(f"\n{len(problems)} findings, {blocking} blocking.")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
