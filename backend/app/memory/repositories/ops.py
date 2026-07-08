"""Ops panel read-only queries (M11, D-016/D-022)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.trace_cost import estimate_cost_usd
from app.config import get_settings
from app.db.models import Dossier, EvalRun, EvalSuite, ReasoningRun


def list_runs(
    session: Session,
    *,
    node: str | None = None,
    model: str | None = None,
    since: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[tuple[ReasoningRun, int, int]]:
    q = (
        select(ReasoningRun, Dossier.id, Dossier.event_id)
        .join(Dossier, Dossier.id == ReasoningRun.dossier_id)
        .order_by(ReasoningRun.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if node:
        q = q.where(ReasoningRun.node == node)
    if model:
        q = q.where(ReasoningRun.model == model)
    if since:
        q = q.where(ReasoningRun.started_at >= since)
    return list(session.execute(q).all())


def cost_rollup(session: Session) -> dict[str, Any]:
    settings = get_settings()
    runs = list(session.scalars(select(ReasoningRun)).all())
    by_model: dict[str, dict[str, int | float]] = {}
    by_day: dict[str, dict[str, int | float]] = {}
    today = datetime.now(UTC).date()

    for run in runs:
        model_bucket = by_model.setdefault(
            run.model,
            {"prompt_tokens": 0, "completion_tokens": 0, "estimated_cost_usd": 0.0},
        )
        model_bucket["prompt_tokens"] = int(model_bucket["prompt_tokens"]) + run.prompt_tokens
        model_bucket["completion_tokens"] = (
            int(model_bucket["completion_tokens"]) + run.completion_tokens
        )
        day_key = run.started_at.astimezone(UTC).date().isoformat()
        day_bucket = by_day.setdefault(
            day_key,
            {"prompt_tokens": 0, "completion_tokens": 0, "estimated_cost_usd": 0.0},
        )
        day_bucket["prompt_tokens"] = int(day_bucket["prompt_tokens"]) + run.prompt_tokens
        day_bucket["completion_tokens"] = (
            int(day_bucket["completion_tokens"]) + run.completion_tokens
        )

    for model, bucket in by_model.items():
        model_runs = [r for r in runs if r.model == model]
        bucket["estimated_cost_usd"] = estimate_cost_usd(model_runs, settings.model_costs)

    for day_key, bucket in by_day.items():
        day_runs = [
            r for r in runs if r.started_at.astimezone(UTC).date().isoformat() == day_key
        ]
        bucket["estimated_cost_usd"] = estimate_cost_usd(day_runs, settings.model_costs)

    total_cost = estimate_cost_usd(runs, settings.model_costs)
    today_key = today.isoformat()
    today_bucket = by_day.get(
        today_key,
        {"prompt_tokens": 0, "completion_tokens": 0, "estimated_cost_usd": 0.0},
    )
    return {
        "total_estimated_cost_usd": total_cost,
        "today_estimated_cost_usd": today_bucket["estimated_cost_usd"],
        "by_model": by_model,
        "by_day": by_day,
    }


def list_eval_runs(session: Session, *, limit: int = 50) -> list[EvalRun]:
    return list(
        session.scalars(
            select(EvalRun).order_by(EvalRun.started_at.desc()).limit(limit)
        )
    )


def latest_by_suite(session: Session) -> dict[str, EvalRun | None]:
    out: dict[str, EvalRun | None] = {s.value: None for s in EvalSuite}
    for suite in EvalSuite:
        row = session.scalar(
            select(EvalRun)
            .where(EvalRun.suite == suite)
            .order_by(EvalRun.started_at.desc())
            .limit(1)
        )
        out[suite.value] = row
    return out


def guardrail_fleet(session: Session) -> dict[str, Any]:
    rows = list(
        session.scalars(
            select(Dossier).where(Dossier.guardrail_stats.isnot(None)).order_by(Dossier.id)
        )
    )
    not_recorded = session.scalar(
        select(func.count())
        .select_from(Dossier)
        .where(Dossier.sections.isnot(None), Dossier.guardrail_stats.is_(None))
    ) or 0
    totals = {
        "stage1_stripped_citations": 0,
        "stage2_unsupported_removed": 0,
        "hypothesis_claims": 0,
        "safety_notes_deleted": 0,
        "chat_citations_stripped": 0,
    }
    per_dossier: list[dict[str, Any]] = []
    for d in rows:
        stats = d.guardrail_stats or {}
        per_dossier.append(
            {
                "dossier_id": d.id,
                "event_id": d.event_id,
                "completed_at": d.completed_at,
                "stats": stats,
            }
        )
        for key in totals:
            totals[key] += int(stats.get(key, 0))
    return {
        "fleet_totals": totals,
        "not_recorded_count": not_recorded,
        "dossiers": per_dossier,
    }
