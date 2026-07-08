"""Chat rate limit smoke (M11 Task 5)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.config import get_settings
from app.db.engine import SessionLocal
from app.db.models import Dossier, DossierStatus, EvidenceLink, OperationalEvent, ReasoningRun
from app.main import create_app

DEMO_EVENT = {
    "asset_tag": "P-3401",
    "source": "simulated",
    "symptom_category": "seal_leak",
    "note": "Rate limit test.",
    "criticality": "A",
}


@pytest.fixture
def client() -> TestClient:
    import os

    os.environ["REASONING_ENABLED"] = "true"
    get_settings.cache_clear()
    return TestClient(create_app())


def _complete_dossier(client: TestClient) -> tuple[int, int]:
    event_id = client.post("/api/events", json=DEMO_EVENT).json()["id"]
    dossier_id = client.post(f"/api/events/{event_id}/dossier").json()["dossier_id"]
    with SessionLocal() as session:
        d = session.get(Dossier, dossier_id)
        assert d is not None
        d.status = DossierStatus.complete
        d.shared_context = d.shared_context or {"evidence_pool": []}
        d.sections = {"probable_causes": [], "safety_notes": [], "actions": []}
        session.commit()
    return dossier_id, event_id


def _teardown(dossier_id: int, event_id: int) -> None:
    with SessionLocal() as session:
        session.execute(delete(ReasoningRun).where(ReasoningRun.dossier_id == dossier_id))
        session.execute(delete(EvidenceLink).where(EvidenceLink.dossier_id == dossier_id))
        session.execute(delete(Dossier).where(Dossier.id == dossier_id))
        session.execute(delete(OperationalEvent).where(OperationalEvent.id == event_id))
        session.commit()


def test_chat_rate_limit_429(client: TestClient) -> None:
    dossier_id, event_id = _complete_dossier(client)
    fake_chat = {"answer": "ok", "citations": [], "refused": False}

    with patch("app.api.dossiers.run_chat", return_value=fake_chat):
        try:
            for _ in range(10):
                r = client.post(
                    f"/api/dossiers/{dossier_id}/chat",
                    json={"question": "test?", "history": []},
                )
                assert r.status_code == 200
            r = client.post(
                f"/api/dossiers/{dossier_id}/chat",
                json={"question": "one more", "history": []},
            )
            assert r.status_code == 429
            assert "Rate limit" in r.json()["message"]
        finally:
            _teardown(dossier_id, event_id)
