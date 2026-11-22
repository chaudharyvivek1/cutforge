#!/usr/bin/env python3
"""Build the specification .docx from its markdown source.

The document's visual language, matched from the earlier versions: A4, 2 cm
margins, Calibri throughout, navy (#2F5D8C) for captions and second-level
headings, near-black (#1F2933) for body, tables with a tinted header row,
and code on a pale slab in Consolas.

Usage:
    python build/build_docx.py <source.md> <output.docx> [figures_dir]
"""
import re
import sys
from pathlib import Path

from docx import Document

from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

NAVY = RGBColor(0x2F, 0x5D, 0x8C)
INK = RGBColor(0x1F, 0x29, 0x33)
MUTED = RGBColor(0x5A, 0x6A, 0x7A)
CODE_BG = "F4F6F9"
HEADER_BG = "E8EEF5"
RULE = "D5DCE4"

CAPTION_RE = re.compile(r"^(Table|Listing|Figure) ([0-9A-Z]+)\s+\|")
IMAGE_RE = re.compile(r"^!\[[^\]]*\]\(([^)]+)\)$")


# --------------------------------------------------------------------- helpers
def shade(element, fill):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    element.append(shd)


def cell_shade(cell, fill):
    shade(cell._tc.get_or_add_tcPr(), fill)


def para_border(par, color=RULE, size=6, side="bottom", space=4):
    pPr = par._p.get_or_add_pPr()
    borders = pPr.find(qn("w:pBdr"))
    if borders is None:
        borders = OxmlElement("w:pBdr")
        pPr.append(borders)
    el = OxmlElement(f"w:{side}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(size))
    el.set(qn("w:space"), str(space))
    el.set(qn("w:color"), color)
    borders.append(el)


def keep_with_next(par):
    par.paragraph_format.keep_with_next = True


def add_field(par, instr):
    run = par.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), instr)
    run._r.addnext(fld)


def style_run(run, size=9.5, bold=False, color=INK, font="Calibri", italic=False):
    run.font.name = font
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color
    return run


INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")


def add_rich(par, text, size=9.5, color=INK):
    """Render **bold** and `code` spans inside a body paragraph."""
    for piece in INLINE_RE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            style_run(par.add_run(piece[2:-2]), size=size, bold=True, color=color)
        elif piece.startswith("`") and piece.endswith("`") and len(piece) > 2:
            style_run(par.add_run(piece[1:-1]), size=size - 0.5, color=color,
                      font="Consolas")
        else:
            style_run(par.add_run(piece), size=size, color=color)


# ------------------------------------------------------------------ document
def setup(doc, footer_text, version):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.0)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(1.8)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = INK
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.22

    # header
    hdr = sec.header.paragraphs[0]
    hdr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    style_run(hdr.add_run(f"Prompt-Driven AI Video Editor  ·  v{version}"),
              size=7.5, color=MUTED)
    para_border(hdr, color=RULE, size=4, space=2)

    # footer with page numbers
    ftr = sec.footer.paragraphs[0]
    ftr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_run(ftr.add_run(footer_text + "   ·   page "), size=7.5, color=MUTED)
    add_field(ftr, "PAGE")
    style_run(ftr.add_run(" of "), size=7.5, color=MUTED)
    add_field(ftr, "NUMPAGES")


def title_page(doc, eyebrow, title, subtitle, meta_rows):
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    style_run(p.add_run(eyebrow), size=9, bold=True, color=NAVY)
    p.paragraph_format.space_after = Pt(10)

    p = doc.add_paragraph()
    style_run(p.add_run(title), size=28, bold=True, color=INK)
    p.paragraph_format.space_after = Pt(8)

    p = doc.add_paragraph()
    style_run(p.add_run(subtitle), size=12, color=MUTED)
    para_border(p, color="2F5D8C", size=12, space=12)
    p.paragraph_format.space_after = Pt(24)

    table = doc.add_table(rows=0, cols=2)
    table.autofit = True
    for label, value in meta_rows:
        row = table.add_row()
        c0, c1 = row.cells
        c0.width, c1.width = Cm(4.0), Cm(13.0)
        style_run(c0.paragraphs[0].add_run(label), size=8.5, bold=True, color=NAVY)
        style_run(c1.paragraphs[0].add_run(value), size=8.5, color=INK)
        for c in row.cells:
            c.paragraphs[0].paragraph_format.space_after = Pt(2)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def h1(doc, text):
    p = doc.add_paragraph()
    style_run(p.add_run(text), size=15, bold=True, color=INK)
    para_border(p, color="2F5D8C", size=8, space=6)
    p.paragraph_format.space_before = Pt(20)
    p.paragraph_format.space_after = Pt(10)
    keep_with_next(p)


def h2(doc, text):
    p = doc.add_paragraph()
    style_run(p.add_run(text), size=11.5, bold=True, color=NAVY)
    p.paragraph_format.space_before = Pt(13)
    p.paragraph_format.space_after = Pt(5)
    keep_with_next(p)


def h3(doc, text):
    p = doc.add_paragraph()
    style_run(p.add_run(text), size=10, bold=True, color=INK)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    keep_with_next(p)


def caption(doc, text):
    p = doc.add_paragraph()
    style_run(p.add_run(text), size=8.5, bold=True, color=NAVY)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    keep_with_next(p)


def body(doc, text):
    p = doc.add_paragraph()
    add_rich(p, text)
    p.paragraph_format.space_after = Pt(7)
    return p


def code_block(doc, lines):
    for i, line in enumerate(lines):
        p = doc.add_paragraph()
        style_run(p.add_run(line if line.strip() else " "), size=7.6, font="Consolas")
        pf = p.paragraph_format
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing = 1.0
        pf.left_indent = Cm(0.3)
        pf.keep_together = True
        if i < len(lines) - 1:
            pf.keep_with_next = True
        shade(p._p.get_or_add_pPr(), CODE_BG)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def pipe_table(doc, rows):
    header, data = rows[0], rows[1:]
    table = doc.add_table(rows=1, cols=len(header))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for i, text in enumerate(header):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(1)
        style_run(p.add_run(text.replace("**", "")), size=7.8, bold=True)
        cell_shade(cell, HEADER_BG)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for row in table.rows:                       # a row split across a page
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))   # reads as two
    for row in data:
        new_row = table.add_row()
        new_row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        cells = new_row.cells
        for i, text in enumerate(row[:len(header)]):
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            add_rich(p, text, size=7.8)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# ---------------------------------------------------------------------- main
def normalise_package(path, when=b"2026-11-22T00:00:00Z"):
    """Make the .docx byte-reproducible.

    python-docx stamps the package with the wall clock and writes the zip in
    whatever order the parts were created, so two builds of the same source
    differ. §11.6 defines reproducibility as "same manifest, same bytes"; the
    document should meet its own standard, or a reviewer cannot tell a content
    change from a packaging one.
    """
    import re
    import zipfile

    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as zin:
        parts = [(i.filename, zin.read(i.filename)) for i in zin.infolist()]

    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in sorted(parts, key=lambda p: p[0]):
            if name == "docProps/core.xml":
                for tag in (b"created", b"modified"):
                    data = re.sub(
                        rb"<dcterms:" + tag + rb"[^>]*>[^<]*</dcterms:" + tag + rb">",
                        b"<dcterms:" + tag + b' xsi:type="dcterms:W3CDTF">' + when
                        + b"</dcterms:" + tag + b">",
                        data)
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(info, data)
    tmp.replace(path)


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    fig_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else dst.parent
    lines = src.read_text(encoding="utf-8").split("\n")

    doc = Document()
    version = lines[0].split("VERSION")[-1].strip() if "VERSION" in lines[0] else "1.4"
    setup(doc, "Prompt-Driven AI Video Editor — technical design specification", version)

    # front matter: everything before "# Contents"
    idx = next(i for i, l in enumerate(lines) if l.strip() == "# Contents")
    head = [l for l in lines[:idx] if l.strip()]
    meta_start = next(i for i, l in enumerate(head) if l.startswith("|"))
    meta_rows = []
    for line in head[meta_start:]:
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if set("".join(cells)) <= set("- "):
            continue
        meta_rows.append((cells[0], cells[1]))
    title_page(doc, head[0], head[1], head[2], meta_rows)

    i = idx
    in_code = False
    code_buf = []
    while i < len(lines):
        line = lines[i]

        if line.strip() == "```":
            if in_code:
                code_block(doc, code_buf)
                code_buf, in_code = [], False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        if stripped.startswith("### "):
            h3(doc, stripped[4:])
        elif stripped.startswith("## "):
            h2(doc, stripped[3:])
        elif stripped.startswith("# "):
            h1(doc, stripped[2:])
        elif IMAGE_RE.match(stripped):
            path = fig_dir / IMAGE_RE.match(stripped).group(1)
            if path.exists():
                doc.add_picture(str(path), width=Cm(15.6))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not set("".join(cells)) <= set("- "):
                    rows.append(cells)
                i += 1
            if rows:
                pipe_table(doc, rows)
            continue
        elif CAPTION_RE.match(stripped):
            caption(doc, stripped)
        elif stripped.startswith("- ") and len(stripped) < 200 and "  " in stripped:
            p = doc.add_paragraph()
            style_run(p.add_run("· " + stripped[2:]), size=9, color=INK)
            p.paragraph_format.left_indent = Cm(0.5)
            p.paragraph_format.space_after = Pt(2)
        else:
            body(doc, stripped)
        i += 1

    dst.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(dst))
    normalise_package(dst)
    print(f"{dst}  ({len(doc.paragraphs)} paragraphs, {len(doc.tables)} tables)")


if __name__ == "__main__":
    main()
