"""Operational Event intake + board (TDD §7, P6/D-011).

One canonical intake contract for every producer (simulator, quick-log, future
integrations). The engine never branches on ``source``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbDep
from app.api.schemas import EventCreate, EventSummary
from app.db.models import Asset, EventStatus, OperationalEvent
from app.domain.symptom_map import known_symptoms
from app.memory.repositories import assets, events

router = APIRouter(prefix="/api/events", tags=["events"])


def _to_summary(
    event: OperationalEvent, asset: Asset, dossier_id: int | None
) -> EventSummary:
    return EventSummary(
        id=event.id,
        asset_tag=asset.tag,
        asset_name=asset.name,
        plant=asset.plant,
        unit=asset.unit,
        source=str(event.source),
        symptom_category=event.symptom_category,
        note=event.note,
        criticality=str(event.criticality),
        status=str(event.status),
        occurred_at=event.occurred_at,
        created_at=event.created_at,
        dossier_id=dossier_id,
    )


@router.post("", status_code=201, response_model=EventSummary)
def create_event(body: EventCreate, db: DbDep) -> EventSummary:
    """Create an Operational Event. Validates asset existence, enum source (by
    pydantic), and symptom membership against the curated map (D-011)."""
    if body.symptom_category not in known_symptoms():
        raise HTTPException(
            422,
            f"unknown symptom_category '{body.symptom_category}'; "
            f"expected one of {known_symptoms()}",
        )
    asset_id = assets.get_asset_id_by_tag(db, body.asset_tag)
    if asset_id is None:
        raise HTTPException(422, f"asset '{body.asset_tag}' not found")

    event = events.create_event(
        db,
        asset_id=asset_id,
        source=body.source,
        symptom_category=body.symptom_category,
        note=body.note,
        criticality=body.criticality,
        occurred_at=datetime.now(UTC),
        status=EventStatus.open,
    )
    row = events.get_event_summary(db, event.id)
    assert row is not None
    return _to_summary(*row)


@router.get("", response_model=list[EventSummary])
def list_events(
    db: DbDep,
    status: str | None = Query(default=None),
) -> list[EventSummary]:
    if status is not None and status not in {s.value for s in EventStatus}:
        raise HTTPException(422, f"unknown status '{status}'")
    rows = events.list_event_summaries(db, status=status)
    return [_to_summary(ev, asset, did) for ev, asset, did in rows]


@router.get("/{event_id}", response_model=EventSummary)
def get_event(event_id: int, db: DbDep) -> EventSummary:
    row = events.get_event_summary(db, event_id)
    if row is None:
        raise HTTPException(404, f"event {event_id} not found")
    return _to_summary(*row)
