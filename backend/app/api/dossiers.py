"""Dossier lifecycle + SSE stream + evidence breakdown (TDD §7, Tasks 1/2).

POST assembles synchronously and idempotently; the stream replays the persisted
deterministic dossier as the SSE sequence; the evidence endpoint's contract
lands now and 404s with a message until M6 populates claims.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app import obs
from app.api.deps import DbDep
from app.api.limiter import limiter
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    DossierResponse,
    EvidenceBreakdown,
    ReasoningRunRow,
    ReasoningRunsResponse,
)
from app.api.service import build_dossier_response, dossier_sse
from app.api.trace_cost import COST_FOOTNOTE, estimate_cost_usd
from app.config import get_settings
from app.context.assembler import build_shared_context
from app.db.engine import SessionLocal
from app.db.models import DossierStatus
from app.domain.models import SharedContext
from app.llm.client import LLMClient, NodeFailure
from app.memory.repositories import dossiers, events, reasoning_runs
from app.reasoning.nodes.chat import run_chat

logger = logging.getLogger("oce.dossier")

router = APIRouter(prefix="/api", tags=["dossiers"])


@router.post("/events/{event_id}/dossier", status_code=201, response_model=DossierResponse)
def create_dossier(event_id: int, db: DbDep) -> DossierResponse:
    """Idempotent: an existing dossier is returned untouched (its Shared Context
    is frozen, P4); otherwise assemble synchronously and set status per
    REASONING_ENABLED."""
    if events.get_event(db, event_id) is None:
        raise HTTPException(404, f"event {event_id} not found")

    existing = dossiers.get_by_event_id(db, event_id)
    if existing is not None and existing.shared_context is not None:
        obs.set_correlation(dossier_id=existing.id)
        return build_dossier_response(existing)

    timings: dict[str, float] = {}
    build_shared_context(event_id, session=db, timings=timings)
    dossier = dossiers.get_by_event_id(db, event_id)
    assert dossier is not None
    dossiers.finalize_status(
        db, dossier, reasoning_enabled=get_settings().reasoning_enabled
    )
    obs.set_correlation(dossier_id=dossier.id)
    logger.info(
        "dossier assembled",
        extra={"assembler_ms": timings.get("total"), "stage_ms": timings},
    )
    return build_dossier_response(dossier)


@router.get("/dossiers/{dossier_id}", response_model=DossierResponse)
def get_dossier(dossier_id: int, db: DbDep) -> DossierResponse:
    dossier = dossiers.get_by_id(db, dossier_id)
    if dossier is None:
        raise HTTPException(404, f"dossier {dossier_id} not found")
    return build_dossier_response(dossier)


@router.get("/dossiers/{dossier_id}/runs", response_model=ReasoningRunsResponse)
def get_dossier_runs(dossier_id: int, db: DbDep) -> ReasoningRunsResponse:
    """Reasoning trace rows for a dossier (D-016), read-only."""
    dossier = dossiers.get_by_id(db, dossier_id)
    if dossier is None:
        raise HTTPException(404, f"dossier {dossier_id} not found")

    rows, replayed = reasoning_runs.list_for_dossier_view(db, dossier)
    settings = get_settings()
    runs = [
        ReasoningRunRow(
            id=r.id,
            node=r.node,
            model=r.model,
            prompt_version=r.prompt_version,
            started_at=r.started_at,
            latency_ms=r.latency_ms,
            prompt_tokens=r.prompt_tokens,
            completion_tokens=r.completion_tokens,
            status=str(r.status),
        )
        for r in rows
    ]
    return ReasoningRunsResponse(
        runs=runs,
        replayed_from_cache=replayed,
        total_latency_ms=sum(r.latency_ms for r in rows),
        total_prompt_tokens=sum(r.prompt_tokens for r in rows),
        total_completion_tokens=sum(r.completion_tokens for r in rows),
        estimated_cost_usd=estimate_cost_usd(rows, settings.model_costs),
        cost_footnote=COST_FOOTNOTE,
    )


@router.get("/dossiers/{dossier_id}/stream")
async def stream_dossier(dossier_id: int) -> EventSourceResponse:
    with SessionLocal() as session:
        if dossiers.get_by_id(session, dossier_id) is None:
            raise HTTPException(404, f"dossier {dossier_id} not found")
    # ping=15 → heartbeat comment every 15s; client polls GET on disconnect.
    return EventSourceResponse(dossier_sse(dossier_id), ping=15)


@router.get(
    "/dossiers/{dossier_id}/evidence/{claim_ref}", response_model=EvidenceBreakdown
)
def get_evidence(
    dossier_id: int, claim_ref: str, db: DbDep
) -> EvidenceBreakdown:
    """Evidence Strength breakdown for a claim (backend explainability, P8)."""
    dossier = dossiers.get_by_id(db, dossier_id)
    if dossier is None:
        raise HTTPException(404, f"dossier {dossier_id} not found")
    if dossier.sections is None or dossier.shared_context is None:
        raise HTTPException(404, f"no claim '{claim_ref}' in dossier {dossier_id}")

    from app.context.evidence import strength
    from app.domain.models import SharedContext

    ctx = SharedContext.model_validate(dossier.shared_context)
    sections = dossier.sections
    claim = None
    for key in ("probable_causes", "safety_notes", "actions"):
        for item in sections.get(key, []):
            if item.get("claim_ref") == claim_ref:
                claim = item
                break
        if claim:
            break
    if claim is None:
        raise HTTPException(404, f"no claim '{claim_ref}' in dossier {dossier_id}")

    ids = claim.get("evidence_ids") or []
    result = strength(ids, ctx)
    return EvidenceBreakdown(
        claim_ref=claim_ref,
        tier=result.tier,
        score=result.score,
        components=result.components.model_dump(),
        evidence_ids=list(ids),
    )


@router.post("/dossiers/{dossier_id}/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
def chat_dossier(
    request: Request,
    dossier_id: int,
    body: ChatRequest,
    db: DbDep,
) -> ChatResponse:
    """Contextual Q&A scoped to frozen dossier context only (FR-9, P1/P4)."""
    if not get_settings().reasoning_enabled:
        raise HTTPException(503, "reasoning layer not enabled")

    dossier = dossiers.get_by_id(db, dossier_id)
    if dossier is None:
        raise HTTPException(404, f"dossier {dossier_id} not found")
    if str(dossier.status) != DossierStatus.complete.value:
        raise HTTPException(409, "dossier reasoning not complete")
    if dossier.shared_context is None or dossier.sections is None:
        raise HTTPException(409, "dossier has no validated context")

    ctx = SharedContext.model_validate(dossier.shared_context)
    obs.set_correlation(dossier_id=dossier_id)
    client = LLMClient()
    try:
        result = run_chat(
            dossier_id=dossier_id,
            session=db,
            client=client,
            shared_context=ctx,
            sections=dossier.sections,
            question=body.question,
            history=[h.model_dump() for h in body.history[:6]],
        )
    except NodeFailure as exc:
        raise HTTPException(502, f"chat unavailable: {exc}") from exc

    return ChatResponse(**result)
