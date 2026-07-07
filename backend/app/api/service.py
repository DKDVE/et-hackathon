"""Dossier assembly + SSE event sequence (TDD §7, Task 1/Task 2).

One builder produces the shape shared by ``GET /api/dossiers/{id}`` and the
``context_ready`` SSE event; one async generator emits the FULL SSE vocabulary.
M5 emits only the deterministic subset (``context_ready`` → ``degraded``); the
M6 branch is a marked seam so the reasoning layer slots in without touching the
frontend or this event ordering.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from app.api.schemas import DegradedInfo, DossierResponse
from app.config import get_settings
from app.db.engine import SessionLocal
from app.db.models import Dossier
from app.domain.models import SharedContext
from app.memory.repositories import dossiers

logger = logging.getLogger("oce.dossier")

# The full SSE event vocabulary (TDD §7). Declared here so it is one source of
# truth for the server, the E2E test, and the frontend contract.
SSE_EVENTS = (
    "context_ready",
    "analysis",
    "recommendation",
    "validated",
    "report_complete",
    "degraded",
)


def build_dossier_response(dossier: Dossier) -> DossierResponse:
    """Assemble the API view of a dossier row (deterministic sections + status).

    ``degraded`` is populated whenever the reasoning layer did not run — in M5
    that is always ``reasoning_disabled`` (reasoning off by default, P5).
    """
    reasoning_enabled = get_settings().reasoning_enabled
    ctx: SharedContext | None = None
    pool_size = 0
    if dossier.shared_context:
        ctx = SharedContext.model_validate(dossier.shared_context)
        pool_size = len(ctx.evidence_pool)

    degraded: DegradedInfo | None = None
    if not reasoning_enabled:
        degraded = DegradedInfo(
            reason="reasoning_disabled", deterministic_available=ctx is not None
        )

    return DossierResponse(
        dossier_id=dossier.id,
        event_id=dossier.event_id,
        status=str(dossier.status),
        reasoning_enabled=reasoning_enabled,
        evidence_pool_size=pool_size,
        context=ctx,
        sections=dossier.sections,
        degraded=degraded,
    )


def _event(name: str, payload: DossierResponse | DegradedInfo) -> dict[str, str]:
    return {"event": name, "data": payload.model_dump_json()}


async def dossier_sse(dossier_id: int) -> AsyncIterator[dict[str, str]]:
    """Yield the SSE sequence for a dossier (sse-starlette event dicts).

    M5: ``context_ready`` (deterministic sections) then ``degraded`` with
    ``reasoning_disabled``. The reasoning branch below is the M6 seam.
    """
    with SessionLocal() as session:
        dossier = dossiers.get_by_id(session, dossier_id)
        if dossier is None:
            yield {
                "event": "degraded",
                "data": json.dumps(
                    {"reason": "node_failure", "deterministic_available": False}
                ),
            }
            return
        response = build_dossier_response(dossier)

    # context_ready carries the deterministic dossier; the degraded / reasoning
    # events follow as their own frames, so strip the envelope's degraded here.
    context_frame = response.model_copy(update={"degraded": None})
    yield _event("context_ready", context_frame)

    if not get_settings().reasoning_enabled:
        yield _event(
            "degraded",
            response.degraded or DegradedInfo(reason="reasoning_disabled"),
        )
        return

    # ── M6 seam ────────────────────────────────────────────────────────────
    # When REASONING_ENABLED, run the LangGraph and emit, in order:
    #   analysis → recommendation → validated → report_complete
    # (or degraded{llm_failure|node_failure} on the failure path). No frontend
    # change is required: the vocabulary and ordering are already the contract.
    logger.warning("reasoning_enabled but M6 graph not wired; emitting degraded")
    yield _event("degraded", DegradedInfo(reason="node_failure"))
