"""Persist reasoning_runs tracing rows (D-016)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Dossier, ReasoningRun, ReasoningRunStatus
from app.domain.models import SharedContext
from app.llm.client import LLMUsage
from app.llm.fallback_cache import cache_key, load_sequence


def record_run(
    session: Session,
    *,
    dossier_id: int,
    node: str,
    model: str,
    prompt_version: str,
    started_at: datetime,
    usage: LLMUsage,
) -> ReasoningRun:
    row = ReasoningRun(
        dossier_id=dossier_id,
        node=node,
        model=model,
        prompt_version=prompt_version,
        started_at=started_at,
        latency_ms=usage.latency_ms,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        status=ReasoningRunStatus(usage.status),
        output_digest=usage.output_digest,
    )
    session.add(row)
    session.commit()
    return row


def record_failure(
    session: Session,
    *,
    dossier_id: int,
    node: str,
    model: str,
    prompt_version: str,
    started_at: datetime,
    latency_ms: int = 0,
    detail: str = "",
) -> ReasoningRun:
    row = ReasoningRun(
        dossier_id=dossier_id,
        node=node,
        model=model,
        prompt_version=prompt_version,
        started_at=started_at,
        latency_ms=latency_ms,
        prompt_tokens=0,
        completion_tokens=0,
        status=ReasoningRunStatus.failed,
        output_digest=detail[:64] or "failed",
    )
    session.add(row)
    session.commit()
    return row


def list_by_dossier(session: Session, dossier_id: int) -> list[ReasoningRun]:
    return list(
        session.scalars(
            select(ReasoningRun)
            .where(ReasoningRun.dossier_id == dossier_id)
            .order_by(ReasoningRun.started_at)
        )
    )


def list_for_dossier_view(
    session: Session, dossier: Dossier
) -> tuple[list[ReasoningRun], bool]:
    """Runs for this dossier; when cache-replayed with no local rows, borrow source runs."""
    runs = list_by_dossier(session, dossier.id)
    if runs or dossier.shared_context is None or dossier.sections is None:
        return runs, False

    ctx = SharedContext.model_validate(dossier.shared_context)
    if load_sequence(session, ctx) is None:
        return [], False

    key = cache_key(ctx)
    for candidate in session.scalars(
        select(Dossier.id)
        .join(ReasoningRun, ReasoningRun.dossier_id == Dossier.id)
        .where(Dossier.id != dossier.id)
        .where(Dossier.shared_context.isnot(None))
        .distinct()
    ):
        other = session.get(Dossier, candidate)
        if other is None or other.shared_context is None:
            continue
        other_ctx = SharedContext.model_validate(other.shared_context)
        if cache_key(other_ctx) == key:
            return list_by_dossier(session, other.id), True

    return [], True
