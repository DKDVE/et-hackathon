"""Operational-event repository — get + create (TDD §5, P6).

Creation is used by the golden fixtures in M4; the intake API lands in M5.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Asset,
    Criticality,
    Dossier,
    EventSource,
    EventStatus,
    OperationalEvent,
)
from app.domain.models import EventInfo


def get_event(session: Session, event_id: int) -> EventInfo | None:
    row = session.execute(
        select(OperationalEvent, Asset.tag)
        .join(Asset, OperationalEvent.asset_id == Asset.id)
        .where(OperationalEvent.id == event_id)
    ).first()
    if row is None:
        return None
    event, tag = row
    return EventInfo(
        event_id=event.id,
        asset_tag=tag,
        source=str(event.source),
        symptom_category=event.symptom_category,
        note=event.note,
        criticality=str(event.criticality),
        status=str(event.status),
        occurred_at=event.occurred_at,
    )


def list_event_summaries(
    session: Session, *, status: str | None = None
) -> Sequence[tuple[OperationalEvent, Asset, int | None]]:
    """Event board rows: event + its asset + its dossier id (if assembled).

    Newest first. ``status`` filters on the event status enum when given.
    """
    stmt = (
        select(OperationalEvent, Asset, Dossier.id)
        .join(Asset, OperationalEvent.asset_id == Asset.id)
        .outerjoin(Dossier, Dossier.event_id == OperationalEvent.id)
        .order_by(OperationalEvent.created_at.desc(), OperationalEvent.id.desc())
    )
    if status:
        stmt = stmt.where(OperationalEvent.status == EventStatus(status))
    return [(ev, asset, did) for ev, asset, did in session.execute(stmt).all()]


def get_event_summary(
    session: Session, event_id: int
) -> tuple[OperationalEvent, Asset, int | None] | None:
    row = session.execute(
        select(OperationalEvent, Asset, Dossier.id)
        .join(Asset, OperationalEvent.asset_id == Asset.id)
        .outerjoin(Dossier, Dossier.event_id == OperationalEvent.id)
        .where(OperationalEvent.id == event_id)
    ).first()
    return (row[0], row[1], row[2]) if row else None


def create_event(
    session: Session,
    *,
    asset_id: int,
    source: EventSource | str,
    symptom_category: str,
    note: str | None,
    criticality: Criticality | str,
    occurred_at: datetime,
    status: EventStatus | str = EventStatus.open,
) -> OperationalEvent:
    event = OperationalEvent(
        asset_id=asset_id,
        source=EventSource(source),
        symptom_category=symptom_category,
        note=note,
        criticality=Criticality(criticality),
        status=EventStatus(status),
        occurred_at=occurred_at,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event
