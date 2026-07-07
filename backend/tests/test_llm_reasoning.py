"""Live LLM structural smoke for demo event (M6 acceptance)."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.engine import SessionLocal
from app.db.models import Dossier, EvidenceLink, OperationalEvent, ReasoningRun
from app.main import create_app
from tests.audits.groundedness_audit import audit_dossier

pytestmark = [pytest.mark.slow, pytest.mark.llm]

DEMO_EVENT = {
    "asset_tag": "P-3401",
    "source": "simulated",
    "symptom_category": "seal_leak",
    "note": (
        "Drips increasing at mechanical seal area, noticed on operator rounds. "
        "Product traces on baseplate."
    ),
    "criticality": "A",
}


def _parse_sse(text: str) -> list[str]:
    names: list[str] = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        for line in block.splitlines():
            if line.startswith("event:"):
                names.append(line[len("event:") :].strip())
    return names


@pytest.fixture(scope="module")
def client() -> TestClient:
    if not os.environ.get("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY not set")
    os.environ["REASONING_ENABLED"] = "true"
    os.environ["DEMO_FALLBACK"] = "false"
    from app.config import get_settings

    get_settings.cache_clear()
    return TestClient(create_app())


@pytest.fixture(scope="module")
def flow(client: TestClient) -> Iterator[dict]:
    resp = client.post("/api/events", json=DEMO_EVENT)
    assert resp.status_code == 201
    event_id = resp.json()["id"]
    dresp = client.post(f"/api/events/{event_id}/dossier")
    assert dresp.status_code == 201
    dossier_id = dresp.json()["dossier_id"]
    yield {"event_id": event_id, "dossier_id": dossier_id}
    with SessionLocal() as s:
        s.execute(delete(ReasoningRun).where(ReasoningRun.dossier_id == dossier_id))
        s.execute(delete(EvidenceLink).where(EvidenceLink.dossier_id == dossier_id))
        s.execute(delete(Dossier).where(Dossier.id == dossier_id))
        s.execute(delete(OperationalEvent).where(OperationalEvent.id == event_id))
        s.commit()


def test_demo_event_full_sse_sequence(client: TestClient, flow: dict) -> None:
    resp = client.get(f"/api/dossiers/{flow['dossier_id']}/stream")
    assert resp.status_code == 200
    names = _parse_sse(resp.text)
    assert names[:1] == ["context_ready"]
    assert "analysis" in names
    assert "recommendation" in names
    assert "validated" in names
    assert "report_complete" in names
    assert "degraded" not in names

    body = client.get(f"/api/dossiers/{flow['dossier_id']}").json()
    assert body["status"] == "complete"
    sections = body["sections"]
    assert sections is not None
    causes = sections.get("probable_causes", [])
    assert 1 <= len(causes) <= 4

    pool = set(body["context"]["evidence_pool"])
    for c in causes:
        for cid in c.get("evidence_ids", []):
            assert cid in pool
    planted = {"WO-2024-0117", "WO-2025-0289", "WO-2026-0034"}
    cited: set[str] = set()
    for key in ("probable_causes", "safety_notes", "actions"):
        for item in sections.get(key, []):
            cited.update(item.get("evidence_ids") or [])
    assert cited, "expected at least one evidenced claim"
    assert cited <= pool
    # ponytail: LLM may cite manual chunks instead of planted WO; either is valid grounding
    assert cited & (planted | {c for c in cited if c.startswith("CH-")}), (
        "expected planted WO or chunk citations"
    )
    assert sections.get("safety_notes"), "expected safety notes"
    for n in sections["safety_notes"]:
        assert n.get("evidence_ids"), "safety notes must cite SOP/manual"

    ok, issues = audit_dossier(flow["dossier_id"])
    assert ok, issues

    with SessionLocal() as s:
        from sqlalchemy import select

        runs = s.scalars(
            select(ReasoningRun).where(ReasoningRun.dossier_id == flow["dossier_id"])
        ).all()
    assert len(runs) >= 3
    ok_runs = [r for r in runs if str(r.status) == "ok" or str(r.status) == "repaired"]
    assert len(ok_runs) >= 3
    for r in ok_runs:
        assert r.latency_ms > 0
        assert r.prompt_tokens >= 0


def test_chat_known_answerable(client: TestClient, flow: dict) -> None:
    """Flush plan question — answerable from manual chunks."""
    # Ensure reasoning completed
    resp = client.get(f"/api/dossiers/{flow['dossier_id']}/stream")
    assert resp.status_code == 200

    body = client.post(
        f"/api/dossiers/{flow['dossier_id']}/chat",
        json={"question": "What flush plan does the OEM specify for this pump?", "history": []},
    )
    assert body.status_code == 200
    data = body.json()
    assert data["refused"] is False
    assert len(data["citations"]) >= 1
    pool = set(
        client.get(f"/api/dossiers/{flow['dossier_id']}").json()["context"]["evidence_pool"]
    )
    for cid in data["citations"]:
        assert cid in pool


def test_chat_unanswerable_refusal(client: TestClient, flow: dict) -> None:
    """Motor insulation class not in dossier — honest refusal."""
    body = client.post(
        f"/api/dossiers/{flow['dossier_id']}/chat",
        json={
            "question": "What is the winding insulation class of motor M-1101?",
            "history": [],
        },
    )
    assert body.status_code == 200
    data = body.json()
    assert data["refused"] is True
    assert data["citations"] == []


def test_chat_reasoning_run_recorded(client: TestClient, flow: dict) -> None:
    client.post(
        f"/api/dossiers/{flow['dossier_id']}/chat",
        json={"question": "What is the seal flush plan?", "history": []},
    )
    with SessionLocal() as s:
        from sqlalchemy import select

        runs = s.scalars(
            select(ReasoningRun).where(
                ReasoningRun.dossier_id == flow["dossier_id"],
                ReasoningRun.node == "chat",
            )
        ).all()
    assert len(runs) >= 1
