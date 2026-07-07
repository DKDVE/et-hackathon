"""Checkpoint-α end-to-end: a simulated event assembles into a complete
deterministic dossier with zero LLM involvement (P5, M5 Task 6).

Flow: POST event → POST dossier → SSE yields context_ready then degraded →
GET dossier exposes sections + evidence pool → a cited chunk resolves to its
source with a page. Requires the seeded + ingested compose DB and loads the
local embedding model (assembler), hence ``@pytest.mark.slow``. The scratch
event/dossier is torn down so reruns stay idempotent (the substrate is frozen).
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.engine import SessionLocal
from app.db.models import Dossier, EvidenceLink, OperationalEvent
from app.main import create_app

pytestmark = pytest.mark.slow

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


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    """(event_name, data) pairs from an SSE body, ignoring heartbeat comments."""
    events: list[tuple[str, dict]] = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        name: str | None = None
        data = ""
        for line in block.splitlines():
            if line.startswith(":"):
                continue  # heartbeat comment
            if line.startswith("event:"):
                name = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data += line[len("data:"):].strip()
        if name and data:
            events.append((name, json.loads(data)))
    return events


@pytest.fixture(scope="module")
def client() -> TestClient:
    import os

    os.environ["REASONING_ENABLED"] = "false"
    from app.config import get_settings

    get_settings.cache_clear()
    return TestClient(create_app())


@pytest.fixture(scope="module")
def flow(client: TestClient) -> Iterator[dict]:
    resp = client.post("/api/events", json=DEMO_EVENT)
    assert resp.status_code == 201, resp.text
    event_id = resp.json()["id"]

    dresp = client.post(f"/api/events/{event_id}/dossier")
    assert dresp.status_code == 201, dresp.text
    dossier_id = dresp.json()["dossier_id"]

    yield {"event_id": event_id, "dossier_id": dossier_id, "post": dresp.json()}

    with SessionLocal() as s:
        s.execute(delete(EvidenceLink).where(EvidenceLink.dossier_id == dossier_id))
        s.execute(delete(Dossier).where(Dossier.id == dossier_id))
        s.execute(delete(OperationalEvent).where(OperationalEvent.id == event_id))
        s.commit()


def test_post_dossier_is_deterministic_and_degraded(flow: dict) -> None:
    post = flow["post"]
    assert post["status"] == "complete"
    assert post["reasoning_enabled"] is False
    assert post["degraded"]["reason"] == "reasoning_disabled"
    assert post["degraded"]["deterministic_available"] is True
    assert post["sections"] is None  # no LLM output in M5


def test_idempotent_dossier_creation(client: TestClient, flow: dict) -> None:
    again = client.post(f"/api/events/{flow['event_id']}/dossier")
    assert again.status_code == 201
    assert again.json()["dossier_id"] == flow["dossier_id"]


def test_sse_yields_context_ready_then_degraded(client: TestClient, flow: dict) -> None:
    resp = client.get(f"/api/dossiers/{flow['dossier_id']}/stream")
    assert resp.status_code == 200
    names = [name for name, _ in _parse_sse(resp.text)]
    assert names == ["context_ready", "degraded"], names


def test_context_ready_carries_full_deterministic_sections(
    client: TestClient, flow: dict
) -> None:
    events = dict(_parse_sse(client.get(f"/api/dossiers/{flow['dossier_id']}/stream").text))
    ctx = events["context_ready"]["context"]
    assert ctx["asset_profile"]["tag"] == "P-3401"
    assert ctx["failure_history"]
    assert ctx["sister_incidents"]
    assert ctx["manual_chunks"] and ctx["sop_chunks"] and ctx["report_chunks"]
    # both pattern rows (D-018): the planted seal pattern and the flush-line row
    modes = {p["failure_mode"] for p in ctx["pattern_stats"]}
    assert "mechanical_seal_leakage" in modes
    assert len(ctx["pattern_stats"]) >= 2
    assert events["context_ready"]["evidence_pool_size"] > 0
    assert events["degraded"]["reason"] == "reasoning_disabled"


def test_get_dossier_exposes_sections_and_pool(client: TestClient, flow: dict) -> None:
    body = client.get(f"/api/dossiers/{flow['dossier_id']}").json()
    assert body["evidence_pool_size"] == len(set(body["context"]["evidence_pool"]))
    assert body["evidence_pool_size"] > 0


def test_cited_chunk_resolves_to_source_with_page(client: TestClient, flow: dict) -> None:
    ctx = client.get(f"/api/dossiers/{flow['dossier_id']}").json()["context"]
    chunk_id = ctx["manual_chunks"][0]["chunk_id"]
    src = client.get(f"/api/sources/chunk/{chunk_id}")
    assert src.status_code == 200
    body = src.json()
    assert body["page"] >= 1
    assert body["citation_id"] == f"CH-{chunk_id}"
    assert body["file_url"].endswith(f"/file/{body['document_id']}")


def test_evidence_endpoint_contract_404s_without_sections(client: TestClient, flow: dict) -> None:
    resp = client.get(f"/api/dossiers/{flow['dossier_id']}/evidence/cause:1")
    assert resp.status_code == 404
    assert "no claim" in resp.json()["detail"]
