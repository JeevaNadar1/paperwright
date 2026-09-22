#!/usr/bin/env python3
"""Render a markdown document to a print-ready A4 PDF.

Usage:
    python3 build_pdf.py draft.md --type contract --out draft.pdf
    python3 build_pdf.py report.md --type report --title "Vendor review"

Type presets pick the typeface and body size:
    contract  sans-serif (Arial metric), 14pt   — continuous reading, legal
    report    serif (Times metric), 12pt        — proposals, business reports
    memo      serif, 12pt                       — official memos and letters
    technical sans headings + serif body, 12pt
    print     sans-serif, 12pt                  — flyers, notices for the wall

Palette is Modern Minimalist: #5DADE2 headings, #708090 secondary text and
rules, #D3D3D3 dividers, with a dark slate body colour so a printed contract
stays legible. Override with --accent / --body-colour.

Markdown subset: ATX headings, numbered and dashed lists, **bold**, *italic*,
pipe tables, --- rules, and `> ` quote lines rendered as indented text.

Requires reportlab (pip install reportlab). Python 3.9+.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable, PageTemplate,
                                    Paragraph, Spacer, Table, TableStyle)
except ImportError:  # pragma: no cover
    print("reportlab is required: pip install reportlab", file=sys.stderr)
    raise SystemExit(2)

ACCENT = "#5DADE2"
SECONDARY = "#708090"
DIVIDER = "#D3D3D3"
BODY = "#333A40"

PRESETS = {
    "contract": {"head": "Helvetica", "body": "Helvetica", "size": 14, "leading": 19, "align": TA_JUSTIFY},
    "report": {"head": "Times-Bold", "body": "Times-Roman", "size": 12, "leading": 17, "align": TA_JUSTIFY},
    "memo": {"head": "Times-Bold", "body": "Times-Roman", "size": 12, "leading": 17, "align": 0},
    "technical": {"head": "Helvetica-Bold", "body": "Times-Roman", "size": 12, "leading": 17, "align": 0},
    "print": {"head": "Helvetica-Bold", "body": "Helvetica", "size": 12, "leading": 17, "align": 0},
}

BOLD_OF = {"Helvetica": "Helvetica-Bold", "Times-Roman": "Times-Bold",
           "Times-Bold": "Times-Bold", "Helvetica-Bold": "Helvetica-Bold"}

# "Date: [Date]" / "**Name:** X" lines are header or signature-block fields, not
# prose. Merging them into a justified paragraph is the single ugliest thing a
# naive markdown renderer does to a contract.
LABEL_RE = re.compile(r"^(?:\*\*[^*]{1,45}?:\*\*|[A-Z][A-Za-z /]{0,30}:)(\s|$)")

INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<b>\1</b>"),
    (re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)"), r"<i>\1</i>"),
    (re.compile(r"`([^`]+?)`"), r"<font face='Courier'>\1</font>"),
    (re.compile(r"~~(.+?)~~"), r"<strike>\1</strike>"),
]


def inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for pattern, repl in INLINE:
        text = pattern.sub(repl, text)
    return text


def styles(preset: dict, accent: str, body_colour: str) -> dict:
    body_font = preset["body"]
    bold = BOLD_OF.get(preset["head"], "Helvetica-Bold")
    base = dict(fontName=body_font, fontSize=preset["size"], leading=preset["leading"],
                textColor=colors.HexColor(body_colour))
    return {
        "h1": ParagraphStyle("h1", fontName=bold, fontSize=preset["size"] + 7,
                             leading=preset["size"] + 11, textColor=colors.HexColor(accent),
                             spaceBefore=0, spaceAfter=10),
        "h2": ParagraphStyle("h2", fontName=bold, fontSize=preset["size"] + 2,
                             leading=preset["size"] + 6, textColor=colors.HexColor(accent),
                             spaceBefore=14, spaceAfter=6),
        "h3": ParagraphStyle("h3", fontName=bold, fontSize=preset["size"],
                             leading=preset["size"] + 4, textColor=colors.HexColor(body_colour),
                             spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("body", alignment=preset["align"], spaceAfter=7, **base),
        "list": ParagraphStyle("list", alignment=0, leftIndent=16, spaceAfter=4, **base),
        "quote": ParagraphStyle("quote", alignment=0, leftIndent=20, rightIndent=12,
                                spaceAfter=7, fontName=body_font, fontSize=preset["size"] - 1,
                                leading=preset["leading"], textColor=colors.HexColor(SECONDARY)),
        "cell": ParagraphStyle("cell", fontName=body_font, fontSize=preset["size"] - 2,
                               leading=preset["size"] + 2, textColor=colors.HexColor(body_colour)),
        "cellhead": ParagraphStyle("cellhead", fontName=bold, fontSize=preset["size"] - 2,
                                   leading=preset["size"] + 2, textColor=colors.HexColor("#FFFFFF")),
        "meta": ParagraphStyle("meta", fontName=body_font, fontSize=preset["size"] - 3,
                               leading=preset["size"], alignment=TA_CENTER,
                               textColor=colors.HexColor(SECONDARY)),
    }


def parse_table(block: list, st: dict, accent: str) -> Table:
    rows = []
    for line in block:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    if not rows:
        return None
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    data = [[Paragraph(inline(c), st["cellhead"]) for c in rows[0]]]
    data += [[Paragraph(inline(c), st["cell"]) for c in r] for r in rows[1:]]
    avail = A4[0] - 50 * mm
    table = Table(data, colWidths=[avail / width] * width, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(accent)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor(DIVIDER)),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(DIVIDER)),
    ]))
    return table


def to_flowables(text: str, st: dict, accent: str) -> list:
    flow, i = [], 0
    lines = text.splitlines()
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and "|" in lines[i + 1]:
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            table = parse_table(block, st, accent)
            if table:
                flow += [Spacer(1, 4), table, Spacer(1, 9)]
            continue

        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            flow.append(Spacer(1, 4))
            flow.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor(DIVIDER)))
            flow.append(Spacer(1, 8))
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            key = "h1" if level == 1 else ("h2" if level == 2 else "h3")
            flow.append(Paragraph(inline(m.group(2)), st[key]))
            if level == 1:
                flow.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor(DIVIDER)))
                flow.append(Spacer(1, 8))
            i += 1
            continue

        m = re.match(r"^(\d+)[.)]\s+(.*)$", stripped)
        if m:
            flow.append(Paragraph(f"{m.group(1)}.&nbsp;&nbsp;{inline(m.group(2))}", st["list"]))
            i += 1
            continue

        if re.match(r"^[-*+]\s+", stripped):
            flow.append(Paragraph("&ndash;&nbsp;&nbsp;" + inline(stripped[2:]), st["list"]))
            i += 1
            continue

        if stripped.startswith("> "):
            flow.append(Paragraph(inline(stripped[2:]), st["quote"]))
            i += 1
            continue

        if LABEL_RE.match(stripped):
            flow.append(Paragraph(inline(stripped), st["body"]))
            i += 1
            continue

        para = [stripped]
        i += 1
        while (i < len(lines) and lines[i].strip()
               and not re.match(r"^\s*(#{1,6}\s|\||\d+[.)]\s|[-*+]\s|>\s|-{3,})", lines[i])
               and not LABEL_RE.match(lines[i].strip())):
            para.append(lines[i].strip())
            i += 1
        flow.append(Paragraph(inline(" ".join(para)), st["body"]))
    return flow


def build(src: Path, out: Path, preset_name: str, title: str, accent: str, body_colour: str,
          footer: str) -> None:
    preset = PRESETS[preset_name]
    st = styles(preset, accent, body_colour)
    text = src.read_text(encoding="utf-8", errors="replace")

    doc = BaseDocTemplate(str(out), pagesize=A4,
                          leftMargin=25 * mm, rightMargin=25 * mm,
                          topMargin=22 * mm, bottomMargin=20 * mm,
                          title=title or src.stem, author="")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")

    def decorate(canvas, _doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor(DIVIDER))
        canvas.setLineWidth(0.5)
        y = doc.bottomMargin - 6 * mm
        canvas.line(doc.leftMargin, y, A4[0] - doc.rightMargin, y)
        canvas.setFont(preset["body"], 8)
        canvas.setFillColor(colors.HexColor(SECONDARY))
        if footer:
            canvas.drawString(doc.leftMargin, y - 4.5 * mm, footer)
        canvas.drawRightString(A4[0] - doc.rightMargin, y - 4.5 * mm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="body", frames=[frame], onPage=decorate)])
    doc.build(to_flowables(text, st, accent))


def main() -> int:
    ap = argparse.ArgumentParser(description="Markdown to print-ready A4 PDF.")
    ap.add_argument("path")
    ap.add_argument("--type", default="contract", choices=sorted(PRESETS))
    ap.add_argument("--out")
    ap.add_argument("--title", default="")
    ap.add_argument("--footer", default="", help="left-hand footer text; empty by default")
    ap.add_argument("--accent", default=ACCENT)
    ap.add_argument("--body-colour", default=BODY)
    args = ap.parse_args()

    src = Path(args.path).expanduser()
    if not src.exists():
        print(f"no such file: {src}", file=sys.stderr)
        return 2
    out = Path(args.out).expanduser() if args.out else src.with_suffix(".pdf")
    build(src, out, args.type, args.title, args.accent, args.body_colour, args.footer)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
