"""Structure-aware chunking — split on numbered headings, preserve section_ref."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.config import get_settings
from app.memory.ingestion.pdf_parser import PageText

logger = logging.getLogger(__name__)

_NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+)$")
_SOP_HEADING = re.compile(r"^(SOP-\d+)\s*[—\-]\s*(.+)$", re.IGNORECASE)
_SOP_STEP = re.compile(r"^(SOP-\d+)\s+Step\s+(\d+)\s*[:\-]?\s*(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class TextChunk:
    content: str
    page: int
    section_ref: str | None


@dataclass
class _Line:
    text: str
    page: int


@dataclass
class _Block:
    lines: list[_Line]
    section_ref: str | None

    @property
    def text(self) -> str:
        return "\n".join(ln.text for ln in self.lines)

    @property
    def page(self) -> int:
        return self.lines[0].page if self.lines else 1

    def token_estimate(self) -> int:
        return len(self.text.split())


def _heading_ref(line: str) -> str | None:
    m = _NUMBERED_HEADING.match(line.strip())
    if m:
        return f"{m.group(1)} {m.group(2)}"
    m = _SOP_HEADING.match(line.strip())
    if m:
        return f"{m.group(1)} — {m.group(2)}"
    m = _SOP_STEP.match(line.strip())
    if m:
        return f"{m.group(1)} Step {m.group(2)} — {m.group(3)}"
    return None


def _split_into_blocks(pages: list[PageText]) -> list[_Block]:
    """Split on heading lines; each block is atomic (never split mid-block)."""
    lines: list[_Line] = []
    for pg in pages:
        for raw in pg.text.splitlines():
            if raw.strip():
                lines.append(_Line(text=raw.rstrip(), page=pg.page_number))

    if not lines:
        return []

    blocks: list[_Block] = []
    current: list[_Line] = []
    current_ref: str | None = None

    def flush() -> None:
        nonlocal current, current_ref
        if current:
            blocks.append(_Block(lines=current, section_ref=current_ref))
        current = []
        current_ref = None

    for ln in lines:
        ref = _heading_ref(ln.text)
        if ref and current:
            flush()
            current_ref = ref
            current.append(ln)
        elif ref:
            current_ref = ref
            current.append(ln)
        else:
            current.append(ln)
    flush()
    return blocks


def _split_block_oversized(block: _Block, max_tokens: int) -> list[_Block]:
    """Split a single clause block when it exceeds max_tokens (paragraph-aware)."""
    if block.token_estimate() <= max_tokens:
        return [block]
    paragraphs: list[list[_Line]] = []
    current: list[_Line] = []
    for ln in block.lines:
        if not ln.text.strip() and current:
            paragraphs.append(current)
            current = []
        else:
            current.append(ln)
    if current:
        paragraphs.append(current)

    if len(paragraphs) <= 1:
        # ponytail: line-wise split when no paragraph breaks — rare for authored manual
        out: list[_Block] = []
        batch: list[_Line] = []
        batch_tokens = 0
        for ln in block.lines:
            lt = len(ln.text.split())
            if batch and batch_tokens + lt > max_tokens:
                out.append(_Block(lines=batch, section_ref=block.section_ref))
                batch = []
                batch_tokens = 0
            batch.append(ln)
            batch_tokens += lt
        if batch:
            out.append(_Block(lines=batch, section_ref=block.section_ref))
        return out

    out = []
    batch: list[_Line] = []
    batch_tokens = 0
    for para in paragraphs:
        pt = sum(len(ln.text.split()) for ln in para)
        if batch and batch_tokens + pt > max_tokens:
            out.append(_Block(lines=batch, section_ref=block.section_ref))
            batch = []
            batch_tokens = 0
        batch.extend(para)
        batch_tokens += pt
    if batch:
        out.append(_Block(lines=batch, section_ref=block.section_ref))
    return out


def _merge_blocks(blocks: list[_Block], target: int) -> list[TextChunk]:
    """Reports/CSV path — merge blocks up to target token size."""
    out: list[TextChunk] = []
    batch: list[_Block] = []
    batch_tokens = 0
    batch_ref: str | None = None

    def emit() -> None:
        nonlocal batch, batch_tokens, batch_ref
        if not batch:
            return
        content = "\n".join(b.text for b in batch)
        out.append(TextChunk(content=content, page=batch[0].page, section_ref=batch_ref))
        batch = []
        batch_tokens = 0
        batch_ref = None

    for block in blocks:
        bt = block.token_estimate()
        if batch and batch_tokens + bt > target:
            emit()
        batch.append(block)
        batch_tokens += bt
        batch_ref = batch_ref or block.section_ref
    emit()
    return out


def _chunk_by_clause(blocks: list[_Block], max_tokens: int) -> list[TextChunk]:
    """Manual/SOP path — one chunk per numbered clause; max_tokens is a ceiling."""
    out: list[TextChunk] = []
    for block in blocks:
        for piece in _split_block_oversized(block, max_tokens):
            out.append(
                TextChunk(
                    content=piece.text,
                    page=piece.page,
                    section_ref=piece.section_ref,
                )
            )
    return out


def _plain_page_chunks(pages: list[PageText], target: int) -> list[TextChunk]:
    """Heading-agnostic fallback: page-grouped chunks, ~target tokens max.

    Never depends on heading detection, so it yields chunks for any document
    that has extractable text — the safety net when clause-boundary mode finds
    nothing to split on.
    """
    out: list[TextChunk] = []
    buf: list[str] = []
    buf_tokens = 0
    buf_page: int | None = None

    def flush() -> None:
        nonlocal buf, buf_tokens, buf_page
        if buf:
            out.append(TextChunk(content="\n".join(buf), page=buf_page or 1, section_ref=None))
        buf = []
        buf_tokens = 0
        buf_page = None

    for pg in pages:
        text = pg.text.strip()
        if not text:
            continue
        words = text.split()
        if len(words) > target:
            flush()
            for i in range(0, len(words), target):
                out.append(
                    TextChunk(
                        content=" ".join(words[i : i + target]),
                        page=pg.page_number,
                        section_ref=None,
                    )
                )
            continue
        if buf and buf_tokens + len(words) > target:
            flush()
        if buf_page is None:
            buf_page = pg.page_number
        buf.append(text)
        buf_tokens += len(words)
    flush()
    return out


def chunk_document(
    pages: list[PageText], *, clause_boundaries: bool, doc_id: int | str | None = None
) -> tuple[list[TextChunk], str]:
    """Chunk one document; return (chunks, mode) where mode is one of
    "plain", "clause", or "fallback".

    For clause docs (manual/SOP), if clause-boundary chunking yields nothing
    (e.g. formatting the heading regex can't see), fall back to page-grouped
    plain chunking so document content is never silently dropped.
    """
    target = get_settings().chunk_target_tokens
    blocks = _split_into_blocks(pages)

    if not clause_boundaries:
        return _merge_blocks(blocks, target), "plain"

    chunks = _chunk_by_clause(blocks, target)
    if chunks:
        return chunks, "clause"

    logger.warning(
        "clause-boundary chunking produced 0 chunks for doc_id=%s; "
        "falling back to page-grouped plain chunking",
        doc_id,
    )
    return _plain_page_chunks(pages, target), "fallback"


def chunk_pages(
    pages: list[PageText], *, clause_boundaries: bool = False
) -> list[TextChunk]:
    """Chunk parsed PDF pages. Manual/SOP: never cross clause headings."""
    chunks, _mode = chunk_document(pages, clause_boundaries=clause_boundaries)
    return chunks
