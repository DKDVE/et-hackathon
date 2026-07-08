"""Work-order repository — failure history, sister incidents, pattern aggregate.

All deterministic SQL (P2). The pattern aggregate (TDD §5.5 / FR-12) is a plain
GROUP BY over normalized failure modes — the demo's proof that the intelligence
is in the substrate.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Asset, FailureMode, WorkOrder
from app.domain.models import PatternStat, SisterIncident, WorkOrderRecord
from app.memory.effective_mode import effective_failure_mode_id

_eff_mode = effective_failure_mode_id()


def _f(value: Any) -> float | None:
    return float(value) if value is not None else None  # Numeric -> float


def get_work_order_source(
    session: Session, wo_number: str
) -> tuple[WorkOrder, str, str, str | None, str | None] | None:
    """A single WO for the SourceViewer: (wo, asset_tag, asset_name, mode_code,
    mode_name). Accepts the wo_number with or without the ``WO-`` prefix."""
    candidates = [wo_number]
    if not wo_number.startswith("WO-"):
        candidates.append(f"WO-{wo_number}")
    row = session.execute(
        select(WorkOrder, Asset.tag, Asset.name, FailureMode.code, FailureMode.name)
        .join(Asset, WorkOrder.asset_id == Asset.id)
        .outerjoin(FailureMode, FailureMode.id == _eff_mode)
        .where(WorkOrder.wo_number.in_(candidates))
    ).first()
    return (row[0], row[1], row[2], row[3], row[4]) if row else None


def get_failure_history(
    session: Session, asset_id: int, *, cap: int
) -> list[WorkOrderRecord]:
    """All WOs for this asset, newest first, capped (TDD §5.2)."""
    rows = session.execute(
        select(WorkOrder, Asset.tag, FailureMode.code)
        .join(Asset, WorkOrder.asset_id == Asset.id)
        .outerjoin(FailureMode, FailureMode.id == _eff_mode)
        .where(WorkOrder.asset_id == asset_id)
        .order_by(WorkOrder.opened_on.desc(), WorkOrder.wo_number.desc())
        .limit(cap)
    ).all()
    return [
        WorkOrderRecord(
            wo_number=wo.wo_number,
            asset_tag=tag,
            opened_on=wo.opened_on,
            closed_on=wo.closed_on,
            raw_description=wo.raw_description,
            actions_taken=wo.actions_taken,
            downtime_hours=_f(wo.downtime_hours),
            failure_mode_code=code,
        )
        for wo, tag, code in rows
    ]


def get_sister_incidents(
    session: Session,
    sister_ids: Sequence[int],
    mode_codes: Sequence[str] | None,
    *,
    cap: int,
) -> list[SisterIncident]:
    """WOs on sister assets, filtered to symptom-plausible failure modes.

    ``mode_codes is None`` means no mode filter (recall fallback for ``other``).
    Newest first, capped (TDD §5.3).
    """
    if not sister_ids:
        return []
    stmt = (
        select(WorkOrder, Asset.tag, Asset.name, FailureMode.code)
        .join(Asset, WorkOrder.asset_id == Asset.id)
        .outerjoin(FailureMode, FailureMode.id == _eff_mode)
        .where(WorkOrder.asset_id.in_(sister_ids))
    )
    if mode_codes is not None:
        stmt = stmt.where(FailureMode.code.in_(mode_codes))
    stmt = stmt.order_by(WorkOrder.opened_on.desc(), WorkOrder.wo_number.desc()).limit(cap)
    rows = session.execute(stmt).all()
    return [
        SisterIncident(
            wo_number=wo.wo_number,
            asset_tag=tag,
            asset_name=name,
            failure_mode_code=code,
            opened_on=wo.opened_on,
            closed_on=wo.closed_on,
            raw_description=wo.raw_description,
            downtime_hours=_f(wo.downtime_hours),
        )
        for wo, tag, name, code in rows
    ]


def get_pattern_stats(
    session: Session,
    asset_ids: Sequence[int],
    mode_codes: Sequence[str] | None,
) -> list[PatternStat]:
    """GROUP BY failure_mode over the sister set (incl. self), TDD §5.5 / FR-12.

    One row per normalized failure mode: occurrences, span (months between the
    earliest and latest closed dates), cumulative downtime, the distinct raw
    phrasings, and the distinct asset tags. Only classified WOs participate
    (an unclassified WO has no mode to group on). Sorted by total downtime desc
    (tie-break by mode code) for a stable, hand-computable order.
    """
    if not asset_ids:
        return []
    stmt = (
        select(
            FailureMode.code,
            func.count(WorkOrder.id),
            func.min(WorkOrder.closed_on),
            func.max(WorkOrder.closed_on),
            func.coalesce(func.sum(WorkOrder.downtime_hours), 0),
            func.array_agg(func.distinct(WorkOrder.raw_description)),
            func.array_agg(func.distinct(Asset.tag)),
        )
        .join(Asset, WorkOrder.asset_id == Asset.id)
        .join(FailureMode, FailureMode.id == _eff_mode)
        .where(WorkOrder.asset_id.in_(asset_ids))
        .where(_eff_mode.isnot(None))
    )
    if mode_codes is not None:
        stmt = stmt.where(FailureMode.code.in_(mode_codes))
    stmt = stmt.group_by(FailureMode.code)

    stats: list[PatternStat] = []
    for code, occ, closed_min, closed_max, downtime, phrasings, tags in session.execute(stmt):
        span = 0
        if closed_min and closed_max:
            span = (closed_max.year - closed_min.year) * 12 + (
                closed_max.month - closed_min.month
            )
        stats.append(
            PatternStat(
                failure_mode=code,
                occurrences=occ,
                span_months=span,
                total_downtime_hours=float(downtime),
                distinct_phrasings=sorted(p for p in phrasings if p is not None),
                asset_tags=sorted(t for t in tags if t is not None),
            )
        )
    stats.sort(key=lambda s: (-s.total_downtime_hours, s.failure_mode))
    return stats
