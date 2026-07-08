"""Cache-Control on static PDF route (M11 Task 5)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    import os

    os.environ["REASONING_ENABLED"] = "false"
    get_settings.cache_clear()
    return TestClient(create_app())


def test_pdf_cache_control_header(client: TestClient) -> None:
    chunks = client.get("/api/sources/chunk/1")
    if chunks.status_code != 200:
        pytest.skip("no chunk 1 in test DB")
    doc_id = chunks.json()["document_id"]
    resp = client.get(f"/api/sources/file/{doc_id}")
    assert resp.status_code == 200
    assert resp.headers.get("cache-control") == "public, max-age=86400, immutable"
