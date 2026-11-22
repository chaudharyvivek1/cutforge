"""Tests for the document's own build, not for the system it describes.

Three defects in the last two versions were found by looking at the built
document rather than at the source: a table row split across a page, a build
that produced nine tables instead of forty-three, and a caption two versions
stale. None was visible to a text check. These tests look at the artefact.
"""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = sorted((REPO / "docs/spec").glob("v*.md"),
              key=lambda p: [int(x) for x in p.stem.lstrip("v").split(".")])[-1]


def build(target):
    subprocess.run([sys.executable, str(REPO / "build/build_docx.py"),
                    str(SPEC), str(target), str(SPEC.parent)],
                   check=True, capture_output=True)
    return target


class TestRoundTrip(unittest.TestCase):
    """§19.1 — the extractor must not lose what the builder wrote.

    A blank line inside a listing used to end the fence on extraction, so
    every code block with a blank line was silently truncated. The figure
    checks never noticed because figures live in prose.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.docx = build(cls.tmp / "spec.docx")
        subprocess.run([sys.executable, str(REPO / "build/extract_spec.py"),
                        str(cls.docx), str(cls.tmp / "out.md"), str(cls.tmp / "figs")],
                       check=True, capture_output=True)
        cls.source = SPEC.read_text()
        cls.extracted = (cls.tmp / "out.md").read_text()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_fenced_blocks_survive(self):
        self.assertEqual(self.source.count("\n```"), self.extracted.count("\n```"))

    def test_every_create_table_survives(self):
        self.assertEqual(self.source.count("CREATE TABLE"), self.extracted.count("CREATE TABLE"))

    def test_the_migration_is_not_truncated(self):
        marker = "--  Prompt-Driven AI Video Editor"
        i = self.extracted.index(marker)
        start = self.extracted.rindex("```", 0, i)
        end = self.extracted.index("```", i)
        self.assertGreater(end - start, 10000, "the migration block is truncated")

    def test_every_table_caption_survives(self):
        src = set(re.findall(r"^Table [0-9A-Z]+  \|  (.+)$", self.source, re.M))
        out = set(re.findall(r"^Table [0-9A-Z]+  \|  (.+)$", self.extracted, re.M))
        self.assertEqual(src - out, set(), "captions lost in the round trip")

    def test_every_figure_string_survives(self):
        for figure in ("14.5016", "2,160,558", "19,219", "12,960"):
            self.assertIn(figure, self.extracted)


class TestBuildDeterminism(unittest.TestCase):
    """§11.6, applied to this repository: same source, same bytes."""

    def test_two_builds_are_identical(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            a = build(tmp / "a.docx").read_bytes()
            b = build(tmp / "b.docx").read_bytes()
            self.assertEqual(a, b, "the document build is not reproducible")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(shutil.which("soffice"),
                     "LibreOffice (soffice) is not on PATH — the rendered-page checks DID NOT RUN")
class TestLayout(unittest.TestCase):
    """A smoke test on the rendered page, which no text check can replace."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.docx = build(cls.tmp / "spec.docx")
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf",
                        "--outdir", str(cls.tmp), str(cls.docx)],
                       check=True, capture_output=True, timeout=300)
        import pymupdf
        cls.doc = pymupdf.open(cls.tmp / "spec.pdf")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_page_count_is_sane(self):
        self.assertGreater(len(self.doc), 40)
        self.assertLess(len(self.doc), 90)

    def test_no_blank_pages(self):
        for n, page in enumerate(self.doc, 1):
            self.assertGreater(len(page.get_text().strip()), 100, f"page {n} is blank")

    def test_every_page_carries_the_running_header(self):
        for n, page in enumerate(self.doc, 1):
            self.assertIn("Prompt-Driven AI Video Editor", page.get_text(), f"page {n}")

    def test_the_migration_rendered(self):
        text = "".join(p.get_text() for p in self.doc)
        self.assertIn("CREATE TABLE erasures", text.replace("\n", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
