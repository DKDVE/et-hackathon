"""Shared PDF/image rendering helpers (fpdf2 + Pillow).

Deterministic by construction: a fixed PDF creation date so the same input
yields byte-identical output for a given fpdf2 version. Core-font (Helvetica)
only — no bundled TTF — so text is sanitized to Latin-1 first.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw

# ponytail: fixed timestamp → deterministic PDF bytes (see module docstring).
_FIXED_DATE = datetime(2024, 1, 1, tzinfo=timezone.utc)

_UNICODE_MAP = {
    "\u2192": "->", "\u2190": "<-", "\u2265": ">=", "\u2264": "<=",
    "\u00d7": "x", "\u20b9": "Rs", "\u2013": "-", "\u2014": "-",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u00b0": " deg", "\u2022": "-", "\u00b3": "3", "\u00b2": "2",
    "\u2011": "-", "\u00a0": " ",
}


def s(text: object) -> str:
    """Sanitize arbitrary text to Latin-1-safe ASCII for the core fonts."""
    out = str(text)
    for uni, rep in _UNICODE_MAP.items():
        out = out.replace(uni, rep)
    return out.encode("latin-1", "replace").decode("latin-1")


class OcePDF(FPDF):
    def __init__(self, doc_no: str = "") -> None:
        super().__init__(format="A4")
        self.doc_no = doc_no
        self.set_creation_date(_FIXED_DATE)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(20, 18, 20)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120)
        label = self.doc_no or ""
        self.cell(0, 8, s(f"{label}    Page {self.page_no()}"), align="C")
        self.set_text_color(0)

    # --- structured content -------------------------------------------------
    def title_block(self, title: str, subtitle: str = "") -> None:
        self.add_page()
        self.set_font("Helvetica", "B", 18)
        self.multi_cell(0, 9, s(title))
        if subtitle:
            self.ln(2)
            self.set_font("Helvetica", "", 11)
            self.set_text_color(90)
            self.multi_cell(0, 6, s(subtitle))
            self.set_text_color(0)
        self.ln(4)

    def h1(self, number: str, title: str) -> None:
        self.add_page()
        self.set_font("Helvetica", "B", 15)
        self.multi_cell(0, 8, s(f"{number}. {title}"))
        self.ln(2)

    def h2(self, number: str, title: str, new_page: bool = True) -> None:
        # Formal manuals allocate a page per numbered clause; this also gives the
        # M3 chunker clean, well-separated section_ref boundaries.
        if new_page:
            self.add_page()
        else:
            self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.set_x(self.l_margin)
        self.multi_cell(0, 7, s(f"{number} {title}"))
        self.ln(2)

    def para(self, text: str) -> None:
        self.set_font("Helvetica", "", 11)
        self.set_x(self.l_margin)
        self.multi_cell(0, 6, s(text))
        self.ln(2)

    def toc_line(self, text: str, indent: int = 0) -> None:
        self.set_font("Helvetica", "", 11)
        self.set_x(self.l_margin + indent)
        self.multi_cell(0, 7 if not indent else 6, s(text))

    def numbered_steps(self, steps: list[str]) -> None:
        self.set_font("Helvetica", "", 11)
        for i, step in enumerate(steps, 1):
            self.set_x(self.l_margin)
            self.multi_cell(0, 6, s(f"{i}. {step}"))
            self.ln(1)
        self.ln(1)

    def kv_table(self, rows: list[tuple[str, str]], headings: tuple[str, str]) -> None:
        self.set_font("Helvetica", "", 10)
        with self.table(
            col_widths=(40, 60), first_row_as_headings=True, text_align="LEFT"
        ) as table:
            hr = table.row()
            hr.cell(s(headings[0]))
            hr.cell(s(headings[1]))
            for k, v in rows:
                r = table.row()
                r.cell(s(k))
                r.cell(s(v))
        self.ln(3)

    def wide_table(
        self, headings: list[str], rows: list[list[str]], col_widths: tuple[int, ...]
    ) -> None:
        self.set_font("Helvetica", "", 9)
        with self.table(
            col_widths=col_widths, first_row_as_headings=True, text_align="LEFT"
        ) as table:
            hr = table.row()
            for h in headings:
                hr.cell(s(h))
            for row in rows:
                r = table.row()
                for cell in row:
                    r.cell(s(cell))
        self.ln(3)


def save_pdf(pdf: OcePDF, rel_or_abs_path: Path) -> int:
    rel_or_abs_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(rel_or_abs_path))
    return rel_or_abs_path.stat().st_size


def render_text_image(title: str, lines: list[str], out_path: Path) -> None:
    """Render text as a raster image (a 'scanned' page with no text layer).

    Used for the honest OCR-demo SOP page (TDD §8): pypdf will extract <30 chars.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    w, h = 1240, 1754  # ~150 dpi A4
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    # Default bitmap font (no external TTF) — deliberately low-fi like a scan.
    y = 90
    draw.text((90, y), s(title), fill="black")
    y += 60
    for line in lines:
        draw.text((90, y), s(line), fill=(30, 30, 30))
        y += 34
    # Faint border to look like a scanned sheet.
    draw.rectangle([40, 40, w - 40, h - 40], outline=(180, 180, 180), width=2)
    img.save(out_path, "PNG")
