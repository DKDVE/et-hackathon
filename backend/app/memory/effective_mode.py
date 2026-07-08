"""Effective failure mode — D-023 human override over auto classification (P2)."""

from __future__ import annotations

from sqlalchemy import case
from sqlalchemy.sql.elements import ColumnElement

from app.db.models import HumanVerdict, WorkOrder


def effective_failure_mode_id() -> ColumnElement[int | None]:
    """SQL expression for the mode the system treats as authoritative.

    confirmed/corrected → human_failure_mode_id; unclassifiable → NULL;
    otherwise → auto failure_mode_id.
    """
    return case(
        (WorkOrder.human_verdict == HumanVerdict.unclassifiable, None),
        (
            WorkOrder.human_verdict.in_((HumanVerdict.confirmed, HumanVerdict.corrected)),
            WorkOrder.human_failure_mode_id,
        ),
        else_=WorkOrder.failure_mode_id,
    )


def effective_failure_mode_id_for_wo(wo: WorkOrder) -> int | None:
    """Python mirror of ``effective_failure_mode_id()`` for a loaded row."""
    if wo.human_verdict == HumanVerdict.unclassifiable:
        return None
    if wo.human_verdict in (HumanVerdict.confirmed, HumanVerdict.corrected):
        return wo.human_failure_mode_id
    return wo.failure_mode_id
