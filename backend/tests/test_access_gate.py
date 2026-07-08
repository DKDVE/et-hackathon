"""Access gate middleware — inert locally, enforced when ACCESS_PASSWORD is set."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    os.environ.pop("ACCESS_PASSWORD", None)
    get_settings.cache_clear()
    return TestClient(create_app())


def test_gate_inert_when_unset(client: TestClient) -> None:
    assert get_settings().access_password == ""
    r = client.get("/api/config")
    assert r.status_code == 200


def test_gate_blocks_without_credentials() -> None:
    os.environ["ACCESS_PASSWORD"] = "hosted-secret"
    get_settings.cache_clear()
    client = TestClient(create_app())
    try:
        assert client.get("/api/config").status_code == 401
        assert client.get("/health").status_code == 200
    finally:
        os.environ.pop("ACCESS_PASSWORD", None)
        get_settings.cache_clear()


def test_gate_allows_cors_preflight_without_credentials() -> None:
    os.environ["ACCESS_PASSWORD"] = "hosted-secret"
    os.environ["FRONTEND_ORIGIN"] = "https://dkdve.github.io"
    get_settings.cache_clear()
    client = TestClient(create_app())
    try:
        r = client.options(
            "/api/events",
            headers={
                "Origin": "https://dkdve.github.io",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "https://dkdve.github.io"
    finally:
        os.environ.pop("ACCESS_PASSWORD", None)
        os.environ.pop("FRONTEND_ORIGIN", None)
        get_settings.cache_clear()


def test_gate_allows_with_basic_credentials() -> None:
    os.environ["ACCESS_PASSWORD"] = "hosted-secret"
    get_settings.cache_clear()
    client = TestClient(create_app())
    try:
        r = client.get("/api/config", auth=("any-user", "hosted-secret"))
        assert r.status_code == 200
    finally:
        os.environ.pop("ACCESS_PASSWORD", None)
        get_settings.cache_clear()
