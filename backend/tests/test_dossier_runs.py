"""GET /api/dossiers/{id}/runs — reasoning trace (M10, D-016)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.config import get_settings
from app.db.engine import SessionLocal
from app.db.models import Dossier, EvidenceLink, OperationalEvent, ReasoningRun
from app.main import create_app

DEMO_EVENT = {
    "asset_tag": "P-3401",
    "source": "simulated",
    "symptom_category": "seal_leak",
    "note": "Trace endpoint test event.",
    "criticality": "A",
}


@pytest.fixture
def client() -> TestClient:
    import os

    os.environ["REASONING_ENABLED"] = "false"
    get_settings.cache_clear()
    return TestClient(create_app())


def _create_event_and_dossier(client: TestClient) -> int:
    event_id = client.post("/api/events", json=DEMO_EVENT).json()["id"]
    dossier_id = client.post(f"/api/events/{event_id}/dossier").json()["dossier_id"]
    return dossier_id


def _teardown(dossier_id: int, event_id: int) -> None:
    with SessionLocal() as session:
        session.execute(delete(ReasoningRun).where(ReasoningRun.dossier_id == dossier_id))
        session.execute(delete(EvidenceLink).where(EvidenceLink.dossier_id == dossier_id))
        session.execute(delete(Dossier).where(Dossier.id == dossier_id))
        session.execute(delete(OperationalEvent).where(OperationalEvent.id == event_id))
        session.commit()


def test_runs_empty_for_deterministic_dossier(client: TestClient) -> None:
    event_id = client.post("/api/events", json=DEMO_EVENT).json()["id"]
    dossier_id = client.post(f"/api/events/{event_id}/dossier").json()["dossier_id"]
    try:
        resp = client.get(f"/api/dossiers/{dossier_id}/runs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["runs"] == []
        assert body["total_latency_ms"] == 0
        assert body["estimated_cost_usd"] == 0.0
        footnote = body["cost_footnote"].lower()
        assert "footnote" in footnote or "token" in footnote
    finally:
        _teardown(dossier_id, event_id)


def test_runs_returns_rows_for_reasoned_dossier(client: TestClient) -> None:
    dossier_id = _create_event_and_dossier(client)
    event_id = client.get(f"/api/dossiers/{dossier_id}").json()["event_id"]
    with SessionLocal() as session:
        session.add(
            ReasoningRun(
                dossier_id=dossier_id,
                node="analysis",
                model="anthropic/claude-sonnet-4.6",
                prompt_version="v1",
                started_at=datetime(2026, 7, 8, 12, 0, tzinfo=UTC),
                latency_ms=1200,
                prompt_tokens=1000,
                completion_tokens=200,
                status="ok",
                output_digest="abc",
            )
        )
        session.commit()
    try:
        resp = client.get(f"/api/dossiers/{dossier_id}/runs")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["runs"]) == 1
        assert body["runs"][0]["node"] == "analysis"
        assert body["total_latency_ms"] == 1200
        assert body["total_prompt_tokens"] == 1000
        assert body["estimated_cost_usd"] > 0
    finally:
        _teardown(dossier_id, event_id)


def test_runs_404_unknown_dossier(client: TestClient) -> None:
    resp = client.get("/api/dossiers/999999999/runs")
    assert resp.status_code == 404
