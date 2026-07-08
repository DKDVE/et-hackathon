"""Executive summary lazy generation tests (M13)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.engine import SessionLocal
from app.db.models import Dossier
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _latest_complete_dossier_id() -> int | None:
    with SessionLocal() as session:
        dossier = session.scalar(
            select(Dossier)
            .where(Dossier.sections.isnot(None))
            .order_by(Dossier.id.desc())
        )
        return dossier.id if dossier else None


def test_summary_failure_leaves_report_intact(client: TestClient) -> None:
    dossier_id = _latest_complete_dossier_id()
    if dossier_id is None:
        pytest.skip("no complete dossier in DB")

    with patch("app.api.dossiers.LLMClient") as mock_cls:
        mock_cls.return_value.complete_structured.side_effect = RuntimeError("boom")
        resp = client.post(f"/api/dossiers/{dossier_id}/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sections"] is not None
    assert "probable_causes" in body["sections"] or "actions" in body["sections"]
    assert body["sections"].get("executive_summary") in (None, "")

    with SessionLocal() as session:
        dossier = session.get(Dossier, dossier_id)
        assert dossier is not None
        assert not dossier.sections.get("executive_summary")


def test_summary_immutable_once_written(client: TestClient) -> None:
    dossier_id = _latest_complete_dossier_id()
    if dossier_id is None:
        pytest.skip("no complete dossier in DB")

    with SessionLocal() as session:
        dossier = session.get(Dossier, dossier_id)
        assert dossier is not None
        if dossier.sections is None:
            pytest.skip("dossier has no sections")
        sections = dict(dossier.sections)
        sections.pop("executive_summary", None)
        sections["executive_summary"] = "Existing immutable summary."
        dossier.sections = sections
        session.commit()

    with patch(
        "app.reasoning.nodes.summary.run_summary",
        side_effect=AssertionError("should not call"),
    ):
        resp = client.post(f"/api/dossiers/{dossier_id}/summary")
    assert resp.status_code == 200
    assert resp.json()["sections"]["executive_summary"] == "Existing immutable summary."

    with SessionLocal() as session:
        dossier = session.get(Dossier, dossier_id)
        assert dossier is not None
        updated = dict(dossier.sections)
        updated.pop("executive_summary", None)
        dossier.sections = updated
        session.commit()
