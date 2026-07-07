"""Chunker unit tests — heading detection and section_ref without PDF I/O."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.memory.ingestion.chunker import chunk_document, chunk_pages
from app.memory.ingestion.pdf_parser import PageText


@pytest.fixture(autouse=True)
def _small_chunk_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.memory.ingestion.chunker.get_settings",
        lambda: Settings(chunk_target_tokens=12),
    )


def _fixture_pages() -> list[PageText]:
    return [
        PageText(
            page_number=1,
            text=(
                "1 Purpose\n"
                "This manual covers CP200 pumps.\n"
                "2 Troubleshooting\n"
                "General guidance for field technicians."
            ),
        ),
        PageText(
            page_number=2,
            text=(
                "6.2 Seal Leakage\n"
                "Check flush plan and gland follower torque.\n"
                "Inspect seal faces for scoring.\n"
                "6.3 High Vibration\n"
                "Verify alignment and NPSH before opening the coupling."
            ),
        ),
        PageText(
            page_number=3,
            text=(
                "SOP-001 — Isolation and seal replacement\n"
                "SOP-001 Step 1 — Isolate suction and discharge valves.\n"
                "Drain casing to safe level.\n"
                "SOP-001 Step 2 — Remove coupling guard."
            ),
        ),
    ]


def test_heading_blocks_produce_section_refs() -> None:
    chunks = chunk_pages(_fixture_pages())
    refs = {c.section_ref for c in chunks}
    assert "6.2 Seal Leakage" in refs
    assert any(r and "SOP-001" in r for r in refs)


def test_no_mid_block_split_on_seal_section() -> None:
    chunks = chunk_pages(_fixture_pages())
    seal_chunks = [c for c in chunks if c.section_ref and c.section_ref.startswith("6.2")]
    assert len(seal_chunks) == 1
    body = seal_chunks[0].content
    assert "flush plan" in body
    assert "scoring" in body
    assert "6.3" not in body


def test_no_cross_clause_boundary_for_manual() -> None:
    """Manual/SOP: each numbered heading starts its own chunk (M3.1)."""
    chunks = chunk_pages(_fixture_pages(), clause_boundaries=True)
    refs = [c.section_ref for c in chunks if c.section_ref]
    assert "1 Purpose" in refs
    assert "2 Troubleshooting" in refs
    assert "6.2 Seal Leakage" in refs
    assert "6.3 High Vibration" in refs
    # seal chunk must not include the next clause heading
    seal = next(c for c in chunks if c.section_ref == "6.2 Seal Leakage")
    assert "6.3" not in seal.content
    assert "Verify alignment" not in seal.content


def test_chunk_page_is_first_line_page() -> None:
    chunks = chunk_pages(_fixture_pages())
    seal = next(c for c in chunks if c.section_ref and c.section_ref.startswith("6.2"))
    assert seal.page == 2


def _headingless_pages() -> list[PageText]:
    """A document whose lines match none of the heading regexes."""
    return [
        PageText(
            page_number=1,
            text=(
                "Routine stroke and calibration check of control valves.\n"
                "Place the loop in manual and notify the control room.\n"
                "Stroke the valve and verify positioner response."
            ),
        ),
        PageText(
            page_number=2,
            text="Calibrate as required and return the loop to auto.",
        ),
    ]


def test_headingless_doc_still_produces_chunks_in_clause_mode() -> None:
    """Regression (M3.2 root cause B): clause mode must never drop content for a
    document with no matching headings — either directly or via fallback."""
    chunks, mode = chunk_document(_headingless_pages(), clause_boundaries=True)
    assert len(chunks) >= 1
    assert mode in {"clause", "fallback"}
    body = " ".join(c.content for c in chunks)
    assert "control valves" in body
    assert "return the loop to auto" in body
