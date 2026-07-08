"""Human review write path — D-023 provenance (only human_* columns)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import FailureMode, HumanVerdict, WorkOrder

# D-023 / NFR-8: no re-review or undo without auth — irreversibility is safer
# than mutable-without-identity on a pre-auth surface.


def submit_review(
    session: Session,
    wo_id: int,
    *,
    verdict: HumanVerdict,
    failure_mode_id: int | None,
) -> WorkOrder:
    wo = session.get(WorkOrder, wo_id)
    if wo is None:
        raise HTTPException(404, f"work order {wo_id} not found")
    if wo.human_reviewed_at is not None:
        raise HTTPException(409, "work order already human-reviewed")

    if verdict == HumanVerdict.corrected:
        if failure_mode_id is None:
            raise HTTPException(422, "failure_mode_id required for corrected verdict")
        mode = session.get(FailureMode, failure_mode_id)
        if mode is None:
            raise HTTPException(422, f"invalid failure_mode_id {failure_mode_id}")
        wo.human_failure_mode_id = failure_mode_id
    elif verdict == HumanVerdict.confirmed:
        if wo.failure_mode_id is None:
            raise HTTPException(422, "cannot confirm — no auto classification")
        wo.human_failure_mode_id = wo.failure_mode_id
    else:  # unclassifiable
        if failure_mode_id is not None:
            raise HTTPException(422, "failure_mode_id forbidden for unclassifiable verdict")
        wo.human_failure_mode_id = None

    wo.human_verdict = verdict
    wo.human_reviewed_at = datetime.now(UTC)
    session.commit()
    session.refresh(wo)
    return wo


def get_mode_code(session: Session, mode_id: int | None) -> str | None:
    if mode_id is None:
        return None
    return session.scalar(select(FailureMode.code).where(FailureMode.id == mode_id))
