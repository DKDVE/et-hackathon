"""Persist reasoning_runs tracing rows (D-016)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import ReasoningRun, ReasoningRunStatus
from app.llm.client import LLMUsage


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
