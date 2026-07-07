"""Dossier assembly + SSE event sequence (TDD §7, Task 1/Task 2).

One builder produces the shape shared by ``GET /api/dossiers/{id}`` and the
``context_ready`` SSE event; one async generator emits the FULL SSE vocabulary.
M5 emits only the deterministic subset (``context_ready`` → ``degraded``); M6
runs the reasoning graph when REASONING_ENABLED.
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
from app.reasoning.graph import reasoning_sse_events

logger = logging.getLogger("oce.dossier")

SSE_EVENTS = (
    "context_ready",
    "analysis",
    "recommendation",
    "validated",
    "report_complete",
    "degraded",
)


def build_dossier_response(dossier: Dossier) -> DossierResponse:
    """Assemble the API view of a dossier row (deterministic sections + status)."""
    reasoning_enabled = get_settings().reasoning_enabled
    ctx: SharedContext | None = None
    pool_size = 0
    if dossier.shared_context:
        ctx = SharedContext.model_validate(dossier.shared_context)
        pool_size = len(ctx.evidence_pool)

    degraded: DegradedInfo | None = None
    if not reasoning_enabled and str(dossier.status) == "complete":
        degraded = DegradedInfo(
            reason="reasoning_disabled", deterministic_available=ctx is not None
        )
    elif reasoning_enabled and dossier.sections is None and str(dossier.status) == "reasoning":
        degraded = None  # in-flight
    elif reasoning_enabled and dossier.sections is None and str(dossier.status) == "complete":
        degraded = None

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


def _event(name: str, payload: DossierResponse | DegradedInfo | dict) -> dict[str, str]:
    if isinstance(payload, (DossierResponse, DegradedInfo)):
        data = payload.model_dump_json()
    else:
        data = json.dumps(payload)
    return {"event": name, "data": data}


async def dossier_sse(dossier_id: int) -> AsyncIterator[dict[str, str]]:
    """Yield the SSE sequence for a dossier (sse-starlette event dicts)."""
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
        ctx = (
            SharedContext.model_validate(dossier.shared_context)
            if dossier.shared_context
            else None
        )

    context_frame = response.model_copy(update={"degraded": None})
    yield _event("context_ready", context_frame)

    if not get_settings().reasoning_enabled:
        yield _event(
            "degraded",
            response.degraded or DegradedInfo(reason="reasoning_disabled"),
        )
        return

    if ctx is None:
        yield _event("degraded", DegradedInfo(reason="node_failure"))
        return

    async for event_name, payload in reasoning_sse_events(dossier_id, ctx):
        if event_name == "degraded":
            yield _event("degraded", DegradedInfo(**payload))
            return
        if event_name == "report_complete":
            with SessionLocal() as session:
                dossier = dossiers.get_by_id(session, dossier_id)
                if dossier is not None:
                    yield _event("report_complete", build_dossier_response(dossier))
                    return
        yield _event(event_name, payload)
