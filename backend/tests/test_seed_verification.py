"""M2 acceptance: run the seeder's structure phase and assert the planted data.

Requires the compose Postgres (migrated) and the rendered artifacts
(`make dataset`). Mounted at /dataset inside the backend/seed containers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pypdf
import pytest
from sqlalchemy import func, select

# Make scripts/seed.py importable (it adds dataset/generators to sys.path itself).
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import seed  # noqa: E402

from app.db.engine import SessionLocal  # noqa: E402
from app.db.models import Asset, Document, WorkOrder  # noqa: E402

# This module TRUNCATEs and reloads the whole substrate (structure phase). It is
# destructive and order-sensitive w.r.t. every DB-backed test, so it is excluded
# from the default `make test` and run in isolation via `make verify-seed`.
pytestmark = pytest.mark.destructive


@pytest.fixture(scope="module")
def seeded() -> tuple[bool, list[str]]:
    return seed.run_structure_phase()


def test_structure_phase_passes(seeded: tuple[bool, list[str]]) -> None:
    ok, lines = seeded
    assert ok, "verification block failed:\n" + "\n".join(lines)


def test_counts(seeded: tuple[bool, list[str]]) -> None:
    with SessionLocal() as s:
        assert s.scalar(select(func.count()).select_from(Asset)) == 40
        assert s.scalar(select(func.count()).select_from(WorkOrder)) == 500
        assert s.scalar(select(func.count()).select_from(Document)) == 60


def test_planted_pattern(seeded: tuple[bool, list[str]]) -> None:
    with SessionLocal() as s:
        rows = s.execute(
            select(WorkOrder.wo_number, Asset.tag, WorkOrder.downtime_hours, WorkOrder.closed_on)
            .join(Asset, WorkOrder.asset_id == Asset.id)
            .where(WorkOrder.wo_number.in_(seed.PLANTED_WOS))
        ).all()
    assert len(rows) == 3
    by_wo = {r.wo_number: r for r in rows}
    assert by_wo["WO-2024-0117"].tag == "P-3401"
    assert by_wo["WO-2025-0289"].tag == "P-3105"
    assert by_wo["WO-2026-0034"].tag == "P-3402"
    assert float(by_wo["WO-2024-0117"].downtime_hours) == 14.0
    assert float(by_wo["WO-2025-0289"].downtime_hours) == 16.0
    assert float(by_wo["WO-2026-0034"].downtime_hours) == 11.0
    assert sum(float(r.downtime_hours) for r in rows) == 41.0
    closed = sorted(r.closed_on for r in rows)
    span = (closed[-1].year - closed[0].year) * 12 + (closed[-1].month - closed[0].month)
    assert span == 22


def test_no_true_label_leaked(seeded: tuple[bool, list[str]]) -> None:
    """Do NOT: true_failure_mode must never reach the DB (M3 audit integrity)."""
    with SessionLocal() as s:
        leaked = s.scalar(
            select(func.count()).select_from(WorkOrder).where(
                (WorkOrder.failure_mode_id.isnot(None))
                | (WorkOrder.normalization_score.isnot(None))
            )
        )
    assert leaked == 0


def test_idempotent_reseed(seeded: tuple[bool, list[str]]) -> None:
    ok, _ = seed.run_structure_phase()
    assert ok
    with SessionLocal() as s:
        assert s.scalar(select(func.count()).select_from(WorkOrder)) == 500


def test_manual_pdf_extractable_with_troubleshooting() -> None:
    import catalogue  # available: seed inserted dataset/generators on sys.path

    manual = catalogue.manual_doc(catalogue.load_design()).abs_path
    reader = pypdf.PdfReader(str(manual))
    assert len(reader.pages) >= 35, f"manual only {len(reader.pages)} pages"
    text = "\n".join(p.extract_text() for p in reader.pages).lower()
    assert "troubleshooting" in text
    # seal leakage <-> flush plan / flush line row
    assert "flush plan" in text or "flush line" in text
    assert "seal" in text and "plan 11" in text
    # vibration <-> alignment / cavitation row
    assert "vibration" in text
    assert "alignment" in text and "cavitation" in text
    # seal cartridge replacement procedure present
    assert "cartridge" in text
