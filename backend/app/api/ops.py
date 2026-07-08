"""Read-only AI Operations API (M11, D-016/D-022)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from app.api.deps import DbDep
from app.api.schemas import (
    EvalRunRow,
    EvalRunsResponse,
    GuardrailsResponse,
    OpsCostsResponse,
    OpsRunRow,
    OpsRunsResponse,
)
from app.api.trace_cost import COST_FOOTNOTE
from app.memory.repositories import ops

router = APIRouter(prefix="/api/ops", tags=["ops"])


@router.get("/runs", response_model=OpsRunsResponse)
def get_ops_runs(
    db: DbDep,
    node: str | None = None,
    model: str | None = None,
    since: datetime | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
) -> OpsRunsResponse:
    rows = ops.list_runs(db, node=node, model=model, since=since, limit=limit, offset=offset)
    return OpsRunsResponse(
        runs=[
            OpsRunRow(
                id=run.id,
                dossier_id=dossier_id,
                event_id=event_id,
                node=run.node,
                model=run.model,
                prompt_version=run.prompt_version,
                started_at=run.started_at,
                latency_ms=run.latency_ms,
                prompt_tokens=run.prompt_tokens,
                completion_tokens=run.completion_tokens,
                status=str(run.status),
            )
            for run, dossier_id, event_id in rows
        ],
        limit=limit,
        offset=offset,
    )


@router.get("/costs", response_model=OpsCostsResponse)
def get_ops_costs(db: DbDep) -> OpsCostsResponse:
    rollup = ops.cost_rollup(db)
    return OpsCostsResponse(
        total_estimated_cost_usd=rollup["total_estimated_cost_usd"],
        today_estimated_cost_usd=rollup["today_estimated_cost_usd"],
        by_model=rollup["by_model"],
        by_day=rollup["by_day"],
        cost_footnote=COST_FOOTNOTE,
    )


@router.get("/evals", response_model=EvalRunsResponse)
def get_ops_evals(db: DbDep, limit: int = Query(default=50, le=200)) -> EvalRunsResponse:
    history = ops.list_eval_runs(db, limit=limit)
    latest = ops.latest_by_suite(db)
    return EvalRunsResponse(
        history=[
            EvalRunRow(
                id=r.id,
                suite=str(r.suite),
                started_at=r.started_at,
                finished_at=r.finished_at,
                git_ref=r.git_ref,
                prompt_versions=r.prompt_versions,
                status=str(r.status),
                metrics=r.metrics,
                detail=r.detail,
            )
            for r in history
        ],
        latest_by_suite={
            suite: (
                EvalRunRow(
                    id=row.id,
                    suite=str(row.suite),
                    started_at=row.started_at,
                    finished_at=row.finished_at,
                    git_ref=row.git_ref,
                    prompt_versions=row.prompt_versions,
                    status=str(row.status),
                    metrics=row.metrics,
                    detail=row.detail,
                )
                if row
                else None
            )
            for suite, row in latest.items()
        },
    )


@router.get("/guardrails", response_model=GuardrailsResponse)
def get_ops_guardrails(db: DbDep) -> GuardrailsResponse:
    data = ops.guardrail_fleet(db)
    return GuardrailsResponse(**data)
