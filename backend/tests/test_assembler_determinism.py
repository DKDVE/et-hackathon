"""Determinism + latency of ``build_shared_context`` (P2, NFR-1, acceptance #3/#4).

Requires the seeded + ingested compose DB and loads the embedding model (slow).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import delete

from app.context.assembler import build_shared_context
from app.db.engine import SessionLocal
from app.db.models import Dossier, OperationalEvent
from app.memory.repositories import assets, events

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def demo_event_id() -> int:
    with SessionLocal() as s:
        asset_id = assets.get_asset_id_by_tag(s, "P-3401")
        assert asset_id is not None
        ev = events.create_event(
            s,
            asset_id=asset_id,
            source="simulated",
            symptom_category="seal_leak",
            note="Drips increasing at mechanical seal area.",
            criticality="A",
            occurred_at=datetime(2026, 3, 1, tzinfo=UTC),
        )
        event_id = ev.id
    yield event_id
    with SessionLocal() as s:
        s.execute(delete(Dossier).where(Dossier.event_id == event_id))
        s.execute(delete(OperationalEvent).where(OperationalEvent.id == event_id))
        s.commit()


def test_identical_content_hash_across_assemblies(demo_event_id: int) -> None:
    a = build_shared_context(demo_event_id)
    b = build_shared_context(demo_event_id)
    assert a.content_hash == b.content_hash
    assert a.canonical_payload() == b.canonical_payload()


def test_warm_latency_under_2s(demo_event_id: int) -> None:
    """NFR-1: warm assembly (model already loaded) < 2s. The first call warms
    the embedder; the measured call is the second."""
    build_shared_context(demo_event_id)  # warm the model cache
    timings: dict[str, float] = {}
    build_shared_context(demo_event_id, timings=timings)
    assert timings["total"] < 2000, timings
