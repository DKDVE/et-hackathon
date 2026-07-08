"""PDF text extraction with OCR fallback for scanned pages."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
import pytesseract
from pypdf import PdfReader

from app.config import get_settings

logger = logging.getLogger(__name__)

# Populated during parse_pdf; reset via reset_ocr_log() before each ingest run.
_ocr_pages: list[tuple[str, int]] = []


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str


def reset_ocr_log() -> None:
    _ocr_pages.clear()


def ocr_pages() -> list[tuple[str, int]]:
    return list(_ocr_pages)


def _ocr_page(pdf_path: Path, page_index: int) -> str:
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        page = doc[page_index]
        bitmap = page.render(scale=2)
        pil_image = bitmap.to_pil()
        return pytesseract.image_to_string(pil_image)
    finally:
        doc.close()


def parse_pdf(path: Path) -> list[PageText]:
    """Extract per-page text; OCR fallback when pypdf yields < OCR_MIN_CHARS."""
    settings = get_settings()
    min_chars = settings.ocr_min_chars
    reader = PdfReader(str(path))
    pages: list[PageText] = []

    for i, page in enumerate(reader.pages):
        page_no = i + 1
        text = (page.extract_text() or "").strip()
        if len(text) < min_chars:
            logger.info(
                "OCR fallback: %s page %d (%d chars from pypdf)",
                path.name,
                page_no,
                len(text),
            )
            text = _ocr_page(path, i).strip()
            _ocr_pages.append((str(path), page_no))
        pages.append(PageText(page_number=page_no, text=text))

    return pages
