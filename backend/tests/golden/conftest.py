"""Golden-fixture harness (M4). Creates events via the repository (the API lands
in M5) and assembles them against the seeded + ingested compose database.

These are integration tests: they require ``make seed && make ingest`` to have
run, and they load the local embedding model — hence ``@pytest.mark.slow``.
Every event/dossier created here is torn down at session end so reruns stay
idempotent (the substrate is frozen; scratch rows are not).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select

from app.context.assembler import build_shared_context
from app.db.engine import SessionLocal
from app.db.models import Chunk, Dossier, OperationalEvent, WorkOrder
from app.domain.models import SharedContext
from app.memory.repositories import assets, events


@dataclass(frozen=True)
class Assembled:
    event_id: int
    ctx: SharedContext


AssembleFn = Callable[..., Assembled]


@pytest.fixture(scope="session")
def assemble() -> Iterator[AssembleFn]:
    created: list[int] = []

    def _make(
        asset_tag: str,
        symptom: str,
        note: str | None,
        *,
        criticality: str = "A",
        timings: dict[str, float] | None = None,
    ) -> Assembled:
        with SessionLocal() as s:
            asset_id = assets.get_asset_id_by_tag(s, asset_tag)
            assert asset_id is not None, f"asset {asset_tag} not seeded"
            ev = events.create_event(
                s,
                asset_id=asset_id,
                source="simulated",
                symptom_category=symptom,
                note=note,
                criticality=criticality,
                occurred_at=datetime(2026, 3, 1, tzinfo=UTC),
            )
            event_id = ev.id
        created.append(event_id)
        ctx = build_shared_context(event_id, timings=timings)
        return Assembled(event_id=event_id, ctx=ctx)

    yield _make

    if created:
        with SessionLocal() as s:
            s.execute(delete(Dossier).where(Dossier.event_id.in_(created)))
            s.execute(delete(OperationalEvent).where(OperationalEvent.id.in_(created)))
            s.commit()


@pytest.fixture(scope="session")
def demo(assemble: AssembleFn) -> Assembled:
    """THE demo event: P-3401, seal_leak, operator-rounds note."""
    return assemble(
        "P-3401",
        "seal_leak",
        "Drips increasing at mechanical seal area, noticed on operator rounds. "
        "Product traces on baseplate.",
    )


def assert_pool_integrity(ctx: SharedContext) -> None:
    """Every citation in the pool resolves to a real DB row (acceptance #5)."""
    chunk_ids = {int(cid[3:]) for cid in ctx.evidence_pool if cid.startswith("CH-")}
    wo_numbers = {cid for cid in ctx.evidence_pool if cid.startswith("WO-")}
    with SessionLocal() as s:
        if chunk_ids:
            found = set(
                s.scalars(select(Chunk.id).where(Chunk.id.in_(chunk_ids))).all()
            )
            assert found == chunk_ids, f"dangling chunk citations: {chunk_ids - found}"
        if wo_numbers:
            found_wo = set(
                s.scalars(
                    select(WorkOrder.wo_number).where(WorkOrder.wo_number.in_(wo_numbers))
                ).all()
            )
            assert found_wo == wo_numbers, f"dangling WO citations: {wo_numbers - found_wo}"
