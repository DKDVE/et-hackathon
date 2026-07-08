"""Linear reasoning pipeline (D-019: 3 LLM nodes + deterministic validation/report)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.engine import SessionLocal
from app.domain.models import SharedContext
from app.llm.client import LLMClient, NodeFailure
from app.llm.fallback_cache import load_sequence, replay_with_pacing, store_sequence
from app.reasoning.nodes import analysis, recommendation, validation_stage1, validation_stage2
from app.reasoning.nodes.report import run_report
from app.reasoning.nodes.validation_stage2 import validated_payload
from app.reasoning.state import DossierState

logger = logging.getLogger("oce.reasoning")


def _analysis_pre_validation(state: DossierState) -> dict[str, Any]:
    if state.analysis is None:
        return {"probable_causes": [], "provisional": True}
    causes = []
    for i, c in enumerate(state.analysis.probable_causes):
        row = c.model_dump()
        row["claim_ref"] = f"cause:{i}"
        row["grounding"] = "evidenced" if c.evidence_ids else "hypothesis"
        causes.append(row)
    return {"probable_causes": causes, "provisional": True}


def _recommendation_pre_validation(state: DossierState) -> dict[str, Any]:
    if state.recommendation is None:
        return {"safety_notes": [], "actions": [], "provisional": True}
    notes, actions = [], []
    for i, n in enumerate(state.recommendation.safety_notes):
        row = n.model_dump()
        row["claim_ref"] = f"safety:{i}"
        row["grounding"] = "evidenced" if n.evidence_ids else "hypothesis"
        notes.append(row)
    for i, a in enumerate(state.recommendation.actions):
        row = a.model_dump()
        row["claim_ref"] = f"action:{i}"
        row["grounding"] = "evidenced" if a.evidence_ids else "hypothesis"
        actions.append(row)
    return {"safety_notes": notes, "actions": actions, "provisional": True}


async def _replay_cached(
    session: Session,
    dossier_id: int,
    shared_context: SharedContext,
    cached: list[dict],
) -> AsyncIterator[tuple[str, dict]]:
    from app.reasoning.nodes.report import persist_validated

    frames = await replay_with_pacing(cached, cached=True)
    for frame in frames:
        name = frame["event"]
        data = json.loads(frame["data"])
        if name == "validated":
            persist_validated(session, dossier_id, data, shared_context)
        if name == "context_ready":
            continue
        yield name, data


async def reasoning_sse_events(
    dossier_id: int,
    shared_context: SharedContext,
) -> AsyncIterator[tuple[str, dict[str, Any] | Any]]:
    """Yield reasoning SSE frames after context_ready."""
    settings = get_settings()

    with SessionLocal() as session:
        if settings.demo_fallback and not settings.openrouter_api_key:
            cached = load_sequence(session, shared_context)
            if cached is not None:
                async for item in _replay_cached(session, dossier_id, shared_context, cached):
                    yield item
                return

    state = DossierState(dossier_id=dossier_id, shared_context=shared_context)
    client = LLMClient(settings)

    with SessionLocal() as session:
        try:
            if not settings.openrouter_api_key:
                raise NodeFailure("OPENROUTER_API_KEY not configured")
            collected: list[dict[str, Any]] = []
            analysis.run_analysis(state, session, client)
            frame = {"event": "analysis", "data": _analysis_pre_validation(state)}
            collected.append(frame)
            yield "analysis", frame["data"]

            recommendation.run_recommendation(state, session, client)
            frame = {"event": "recommendation", "data": _recommendation_pre_validation(state)}
            collected.append(frame)
            yield "recommendation", frame["data"]

            validation_stage1.run_validation_stage1(state)
            validation_stage2.run_validation_stage2(state, session, client)
            frame = {"event": "validated", "data": validated_payload(state)}
            collected.append(frame)
            yield "validated", frame["data"]

            run_report(state, session)
            frame = {"event": "report_complete", "data": {"status": "complete"}}
            collected.append(frame)
            store_sequence(session, shared_context, collected)
            yield "report_complete", frame["data"]
        except NodeFailure as exc:
            logger.warning("reasoning failure", extra={"error": str(exc)})
            if settings.demo_fallback:
                cached = load_sequence(session, shared_context)
                if cached is not None:
                    async for item in _replay_cached(session, dossier_id, shared_context, cached):
                        yield item
                    return
            err = str(exc).lower()
            reason = "llm_failure" if "transport" in err or "api" in err else "node_failure"
            yield "degraded", {"reason": reason, "deterministic_available": True}
        except Exception:
            logger.exception("reasoning unexpected failure")
            if settings.demo_fallback:
                cached = load_sequence(session, shared_context)
                if cached is not None:
                    async for item in _replay_cached(session, dossier_id, shared_context, cached):
                        yield item
                    return
            yield "degraded", {"reason": "node_failure", "deterministic_available": True}
