"""Memory layer API tests (M12)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.config import get_settings
from app.db.engine import SessionLocal
from app.db.models import FailureMode, HumanVerdict, WorkOrder
from app.main import create_app

PLANTED_WOS = ("WO-2024-0117", "WO-2025-0289", "WO-2026-0034")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_memory_overview(client: TestClient) -> None:
    resp = client.get("/api/memory/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["work_order_count"] == 500
    assert data["taxonomy_size"] == 25
    assert data["wo_auto_classified"] + data["wo_unclassified"] == data["work_order_count"]


def test_memory_assets_coverage_footnote(client: TestClient) -> None:
    resp = client.get("/api/memory/assets")
    assert resp.status_code == 200
    body = resp.json()
    assert "coverage_footnote" in body
    assert len(body["assets"]) == 40
    tiers = {a["coverage_tier"] for a in body["assets"]}
    assert tiers <= {"Good", "Partial", "Thin"}


def test_memory_documents_and_taxonomy(client: TestClient) -> None:
    docs = client.get("/api/memory/documents").json()
    assert len(docs) >= 1
    assert "file_url" in docs[0]
    tax = client.get("/api/memory/taxonomy").json()
    assert len(tax) >= 1
    assert "modes" in tax[0]


def test_planted_wos_not_in_review_queue(client: TestClient) -> None:
    """Hero planted WOs score 0.642–0.817 — above low-margin band."""
    queue = client.get("/api/memory/review-queue").json()
    queued_numbers = {r["wo_number"] for r in queue}
    for wo in PLANTED_WOS:
        assert wo not in queued_numbers, f"{wo} should not appear in review queue"


def test_review_queue_band_logic(client: TestClient) -> None:
    settings = get_settings()
    thr = settings.norm_threshold
    band_top = thr + 0.05
    with SessionLocal() as session:
        # Pick a WO outside band with auto classification — should not queue
        high = session.scalar(
            select(WorkOrder)
            .where(WorkOrder.failure_mode_id.isnot(None))
            .where(WorkOrder.normalization_score >= band_top)
            .where(WorkOrder.human_reviewed_at.is_(None))
            .limit(1)
        )
        assert high is not None
        high_id = high.id
        low_margin = session.scalar(
            select(WorkOrder)
            .where(WorkOrder.failure_mode_id.isnot(None))
            .where(WorkOrder.normalization_score >= thr)
            .where(WorkOrder.normalization_score < band_top)
            .where(WorkOrder.human_reviewed_at.is_(None))
            .limit(1)
        )
        assert low_margin is not None
        low_id = low_margin.id

    queue_ids = {r["wo_id"] for r in client.get("/api/memory/review-queue").json()}
    assert high_id not in queue_ids
    assert low_id in queue_ids


def test_review_provenance_and_409(client: TestClient) -> None:
    with SessionLocal() as session:
        wo = session.scalar(
            select(WorkOrder)
            .where(WorkOrder.failure_mode_id.isnot(None))
            .where(WorkOrder.human_reviewed_at.is_(None))
            .where(WorkOrder.wo_number.notin_(PLANTED_WOS))
            .limit(1)
        )
        assert wo is not None
        wo_id = wo.id
        auto_mode = wo.failure_mode_id
        auto_score = float(wo.normalization_score) if wo.normalization_score else None

    # Confirm
    resp = client.post(f"/api/memory/review/{wo_id}", json={"verdict": "confirmed"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["human_verdict"] == "confirmed"
    assert body["failure_mode_id"] == auto_mode
    assert body["normalization_score"] == auto_score

    # 409 on re-review
    again = client.post(f"/api/memory/review/{wo_id}", json={"verdict": "confirmed"})
    assert again.status_code == 409

    # Reset human columns only (simulate accidental review on non-hero WO)
    with SessionLocal() as session:
        session.execute(
            update(WorkOrder)
            .where(WorkOrder.id == wo_id)
            .values(
                human_failure_mode_id=None,
                human_verdict=None,
                human_reviewed_at=None,
            )
        )
        session.commit()

    # Correct on a different WO
    with SessionLocal() as session:
        wo2 = session.scalar(
            select(WorkOrder)
            .where(WorkOrder.failure_mode_id.isnot(None))
            .where(WorkOrder.human_reviewed_at.is_(None))
            .where(WorkOrder.id != wo_id)
            .where(WorkOrder.wo_number.notin_(PLANTED_WOS))
            .limit(1)
        )
        assert wo2 is not None
        wo2_id = wo2.id
        before_mode = wo2.failure_mode_id
        before_score = wo2.normalization_score
        other_mode = session.scalar(
            select(FailureMode.id).where(FailureMode.id != before_mode).limit(1)
        )
        assert other_mode is not None

    resp2 = client.post(
        f"/api/memory/review/{wo2_id}",
        json={"verdict": "corrected", "failure_mode_id": other_mode},
    )
    assert resp2.status_code == 200
    with SessionLocal() as session:
        row = session.get(WorkOrder, wo2_id)
        assert row is not None
        assert row.failure_mode_id == before_mode
        assert row.normalization_score == before_score
        assert row.human_failure_mode_id == other_mode

    # Unclassifiable
    with SessionLocal() as session:
        wo3 = session.scalar(
            select(WorkOrder)
            .where(WorkOrder.failure_mode_id.isnot(None))
            .where(WorkOrder.human_reviewed_at.is_(None))
            .where(WorkOrder.id.notin_([wo_id, wo2_id]))
            .where(WorkOrder.wo_number.notin_(PLANTED_WOS))
            .limit(1)
        )
        assert wo3 is not None
        wo3_id = wo3.id
        b_mode = wo3.failure_mode_id
        b_score = wo3.normalization_score

    resp3 = client.post(f"/api/memory/review/{wo3_id}", json={"verdict": "unclassifiable"})
    assert resp3.status_code == 200
    with SessionLocal() as session:
        row3 = session.get(WorkOrder, wo3_id)
        assert row3 is not None
        assert row3.failure_mode_id == b_mode
        assert row3.normalization_score == b_score
        assert row3.human_verdict == HumanVerdict.unclassifiable

    # Cleanup human reviews from test
    with SessionLocal() as session:
        session.execute(
            update(WorkOrder)
            .where(WorkOrder.id.in_([wo2_id, wo3_id]))
            .values(
                human_failure_mode_id=None,
                human_verdict=None,
                human_reviewed_at=None,
            )
        )
        session.commit()


def test_ingest_reset_clears_human_columns_in_source() -> None:
    import inspect

    from app.memory.ingestion import document_ingestor

    src = inspect.getsource(document_ingestor.reset_ingest_state)
    assert "human_failure_mode_id=None" in src
    assert "human_verdict=None" in src
    assert "human_reviewed_at=None" in src
