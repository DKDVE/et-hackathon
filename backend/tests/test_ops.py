"""Ops API tests (M11)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.config import get_settings
from app.db.engine import SessionLocal
from app.db.models import (
    Dossier,
    EvalRun,
    EvidenceLink,
    OperationalEvent,
    ReasoningRun,
)
from app.main import create_app

DEMO_EVENT = {
    "asset_tag": "P-3401",
    "source": "simulated",
    "symptom_category": "seal_leak",
    "note": "Ops API test.",
    "criticality": "A",
}


@pytest.fixture
def client() -> TestClient:
    import os

    os.environ["REASONING_ENABLED"] = "false"
    get_settings.cache_clear()
    return TestClient(create_app())


def _teardown(dossier_id: int, event_id: int) -> None:
    with SessionLocal() as session:
        session.execute(delete(EvalRun))
        session.execute(delete(ReasoningRun).where(ReasoningRun.dossier_id == dossier_id))
        session.execute(delete(EvidenceLink).where(EvidenceLink.dossier_id == dossier_id))
        session.execute(delete(Dossier).where(Dossier.id == dossier_id))
        session.execute(delete(OperationalEvent).where(OperationalEvent.id == event_id))
        session.commit()


def test_ops_runs_empty(client: TestClient) -> None:
    resp = client.get("/api/ops/runs?node=__no_such_node__")
    assert resp.status_code == 200
    assert resp.json()["runs"] == []


def test_ops_runs_filter(client: TestClient) -> None:
    event_id = client.post("/api/events", json=DEMO_EVENT).json()["id"]
    dossier_id = client.post(f"/api/events/{event_id}/dossier").json()["dossier_id"]
    with SessionLocal() as session:
        session.add(
            ReasoningRun(
                dossier_id=dossier_id,
                node="ops_filter_probe",
                model="anthropic/claude-sonnet-4.6",
                prompt_version="v1",
                started_at=datetime(2026, 7, 8, 12, 0, tzinfo=UTC),
                latency_ms=100,
                prompt_tokens=10,
                completion_tokens=5,
                status="ok",
                output_digest="x",
            )
        )
        session.commit()
    try:
        resp = client.get("/api/ops/runs?node=ops_filter_probe")
        assert resp.status_code == 200
        rows = resp.json()["runs"]
        assert len(rows) == 1
        assert rows[0]["event_id"] == event_id
        assert client.get("/api/ops/runs?node=ops_filter_probe_empty").json()["runs"] == []
    finally:
        _teardown(dossier_id, event_id)


def test_ops_evals_and_guardrails_empty(client: TestClient) -> None:
    resp = client.get("/api/ops/evals")
    assert resp.status_code == 200
    body = resp.json()
    assert "history" in body
    assert "latest_by_suite" in body

    g = client.get("/api/ops/guardrails").json()
    assert g["fleet_totals"]["stage1_stripped_citations"] == 0
    assert g["not_recorded_count"] >= 0


def test_ops_costs_footnote(client: TestClient) -> None:
    resp = client.get("/api/ops/costs")
    assert resp.status_code == 200
    assert "cost_footnote" in resp.json()
