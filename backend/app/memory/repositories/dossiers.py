"""Dossier repository — read + status transitions (TDD §3/§7).

Creation of the row + shared_context snapshot happens inside the assembler
(``context/assembler.py::_persist_snapshot``); this module reads dossiers back
and flips the status once assembly completes.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Dossier, DossierStatus


def get_by_id(session: Session, dossier_id: int) -> Dossier | None:
    return session.get(Dossier, dossier_id)


def get_by_event_id(session: Session, event_id: int) -> Dossier | None:
    return session.scalar(select(Dossier).where(Dossier.event_id == event_id))


def finalize_status(session: Session, dossier: Dossier, *, reasoning_enabled: bool) -> Dossier:
    """Set the post-assembly status per REASONING_ENABLED (M5 Task 1).

    reasoning off → the deterministic dossier is the final product: mark
    ``complete`` and stamp ``completed_at``. reasoning on → hand off to the M6
    graph by leaving it in ``reasoning`` (the graph will complete/fail it).
    """
    if reasoning_enabled:
        dossier.status = DossierStatus.reasoning
        dossier.completed_at = None
    else:
        dossier.status = DossierStatus.complete
        dossier.completed_at = datetime.now(UTC)
    session.commit()
    session.refresh(dossier)
    return dossier
