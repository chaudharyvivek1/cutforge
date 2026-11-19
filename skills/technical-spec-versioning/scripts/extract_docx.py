#!/usr/bin/env python3
"""Render a specification .docx to faithful markdown for diffing and review.

The .docx is the artefact of record. This script exists so that the same
content is reviewable in a pull request: headings, tables, code listings
and figures are recovered from the document's own formatting rather than
guessed from the text.

Usage:
    python build/extract_spec.py <input.docx> <output.md> [figures_dir]
"""
import re
import sys
import zipfile
from pathlib import Path

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

CODE_FONTS = {"consolas", "courier new", "cascadia mono", "menlo", "monospace"}
HEAD_RE = re.compile(r"^(\d{1,2})\s{2,}\S")
SUB_RE = re.compile(r"^(\d{1,2}\.\d{1,2})\s{2,}\S")
SUBSUB_RE = re.compile(r"^(\d{1,2}\.\d{1,2}\.\d{1,2})\s{2,}\S")
APPX_RE = re.compile(r"^(Appendix [A-C])\b")


def is_code(par):
    runs = [r for r in par.runs if r.text.strip()]
    if not runs:
        return False
    mono = [r for r in runs if (r.font.name or "").lower() in CODE_FONTS]
    return len(mono) == len(runs)


def heading_level(text):
    if text in ("Contents",):
        return 1
    if APPX_RE.match(text):
        return 1
    if SUBSUB_RE.match(text):
        return 3
    if SUB_RE.match(text):
        return 2
    if HEAD_RE.match(text):
        return 1
    return 0


def iter_blocks(doc):
    for child in doc.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, doc)
        elif child.tag.endswith("}tbl"):
            yield Table(child, doc)


def table_to_md(table):
    rows = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            text = " ".join(cell.text.split())
            cells.append(text.replace("|", "\\|"))
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |",
           "|" + "|".join(["---"] * width) + "|"]
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def extract_media(docx_path, figures_dir):
    """Pull embedded images out of the package, in document order."""
    names = []
    with zipfile.ZipFile(docx_path) as z:
        media = sorted(n for n in z.namelist() if n.startswith("word/media/"))
        for i, n in enumerate(media, 1):
            suffix = Path(n).suffix.lower() or ".png"
            target = figures_dir / f"figure-{i}{suffix}"
            target.write_bytes(z.read(n))
            names.append(target.name)
    return names


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    figures_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else dst.parent / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    media = extract_media(src, figures_dir)

    doc = docx.Document(str(src))
    lines = []
    code_buf = []
    fig_index = 0

    blocks = list(iter_blocks(doc))
    # A table of contents is a run of many consecutive heading-shaped
    # paragraphs. Emit it as a list so it does not collide with the real
    # headings that follow it.
    toc_flags = [False] * len(blocks)
    i = 0
    while i < len(blocks):
        if isinstance(blocks[i], Paragraph) and (HEAD_RE.match(blocks[i].text.strip())
                                                or APPX_RE.match(blocks[i].text.strip())):
            j = i
            while j < len(blocks) and isinstance(blocks[j], Paragraph) and (
                    HEAD_RE.match(blocks[j].text.strip())
                    or APPX_RE.match(blocks[j].text.strip())):
                j += 1
            if j - i >= 5:
                for k in range(i, j):
                    toc_flags[k] = True
            i = j
        else:
            i += 1

    toc_started = False
    for idx, block in enumerate(blocks):
        if toc_flags[idx]:
            if not toc_started:
                lines += ["# Contents", ""]
                toc_started = True
            lines.append("- " + block.text.strip())
            if idx + 1 < len(blocks) and not toc_flags[idx + 1]:
                lines.append("")
            continue

        if isinstance(block, Table):
            if code_buf:
                lines += ["```"] + code_buf + ["```", ""]
                code_buf = []
            lines += [table_to_md(block), ""]
            continue

        text = block.text.strip()
        # an inline picture lives in a run, not in the text
        has_picture = "graphicData" in block._p.xml

        if not text and not has_picture:
            if code_buf:
                lines += ["```"] + code_buf + ["```", ""]
                code_buf = []
            continue

        if is_code(block):
            code_buf.append(block.text.rstrip())
            continue
        if code_buf:
            lines += ["```"] + code_buf + ["```", ""]
            code_buf = []

        if has_picture:
            if fig_index < len(media):
                lines += [f"![Figure {fig_index + 1}](figures/{media[fig_index]})", ""]
                fig_index += 1
            continue

        if text == "Contents":
            continue          # emitted by the TOC block below
        level = heading_level(text)
        if level:
            lines += ["#" * level + " " + text, ""]
            continue

        lines += [text, ""]

    if code_buf:
        lines += ["```"] + code_buf + ["```", ""]

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"{dst}  ({len(lines)} blocks, {fig_index} figures, {len(media)} media files)")


if __name__ == "__main__":
    main()
