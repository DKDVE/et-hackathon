"""Persist eval_runs rows (M11)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import EvalRun, EvalStatus, EvalSuite
from app.llm.fallback_cache import prompt_versions


def persist_eval_run(
    session: Session,
    *,
    suite: EvalSuite,
    started_at: datetime,
    status: EvalStatus,
    metrics: dict[str, Any],
    git_ref: str,
    detail: dict[str, Any] | None = None,
    prompt_versions_map: dict[str, str] | None = None,
) -> EvalRun:
    row = EvalRun(
        suite=suite,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        git_ref=git_ref,
        prompt_versions=prompt_versions_map or prompt_versions(),
        status=status,
        metrics=metrics,
        detail=detail,
    )
    session.add(row)
    session.commit()
    return row
