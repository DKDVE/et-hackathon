"""D-015 lexical channel: exact literals an embedding blurs are recovered verbatim.

The demo dataset's flush plan is the API "Plan 11" (there is no literal
"flush plan Y" in any chunk — see verification block). An event note quoting
"Plan 11" must therefore surface at least one chunk containing that literal
token, tagged ``lexical`` or ``both``.

Requires the seeded + ingested compose DB and loads the model (slow).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import delete

from app.context.assembler import build_shared_context, extract_tokens
from app.db.engine import SessionLocal
from app.db.models import Dossier, OperationalEvent
from app.memory.repositories import assets, events

pytestmark = pytest.mark.slow

LEXICAL_NOTE = (
    'Seal weeping observed; maintenance referenced the "Plan 11" flush plan on the '
    "sister unit."
)


def test_extract_tokens_picks_quoted_literal() -> None:
    tokens = extract_tokens(f"{LEXICAL_NOTE} seal_leak")
    assert "Plan 11" in tokens


def test_extract_tokens_picks_asset_and_wo_codes() -> None:
    tokens = extract_tokens("Check P-3401 against WO-2024-0117 and SOP-001.")
    assert "P-3401" in tokens
    assert "WO-2024-0117" in tokens
    assert any(t.upper() == "SOP-001" for t in tokens)


@pytest.fixture(scope="module")
def lexical_ctx():
    with SessionLocal() as s:
        asset_id = assets.get_asset_id_by_tag(s, "P-3401")
        assert asset_id is not None
        ev = events.create_event(
            s,
            asset_id=asset_id,
            source="simulated",
            symptom_category="seal_leak",
            note=LEXICAL_NOTE,
            criticality="A",
            occurred_at=datetime(2026, 3, 1, tzinfo=UTC),
        )
        event_id = ev.id
    ctx = build_shared_context(event_id)
    yield ctx
    with SessionLocal() as s:
        s.execute(delete(Dossier).where(Dossier.event_id == event_id))
        s.execute(delete(OperationalEvent).where(OperationalEvent.id == event_id))
        s.commit()


def test_lexical_channel_recovers_literal(lexical_ctx) -> None:
    all_chunks = lexical_ctx.manual_chunks + lexical_ctx.sop_chunks + lexical_ctx.report_chunks
    hits = [
        c
        for c in all_chunks
        if c.retrieval_channel in ("lexical", "both") and "plan 11" in c.content.lower()
    ]
    assert hits, "lexical channel recovered no 'Plan 11' literal"
