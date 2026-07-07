"""Recommendation LLM node."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.llm.client import LLMClient
from app.memory.repositories import reasoning_runs
from app.reasoning.prompts import recommendation as rec_prompt
from app.reasoning.prompts.context_render import render_recommendation_context
from app.reasoning.schemas import RecommendationOutput
from app.reasoning.state import DossierState


def run_recommendation(state: DossierState, session: Session, client: LLMClient) -> DossierState:
    if state.analysis is None:
        raise ValueError("analysis required before recommendation")
    started = datetime.now(UTC)
    ctx_text = render_recommendation_context(state.shared_context)
    causes_json = json.dumps(
        [c.model_dump() for c in state.analysis.probable_causes], indent=2
    )
    messages = [
        {"role": "system", "content": rec_prompt.SYSTEM},
        {
            "role": "user",
            "content": rec_prompt.USER_TEMPLATE.format(context=ctx_text, causes=causes_json),
        },
    ]
    model = get_settings().llm_models.get("recommendation", "anthropic/claude-sonnet-4.6")
    try:
        output, usage = client.complete_structured("recommendation", messages, RecommendationOutput)
        state.recommendation = output
        reasoning_runs.record_run(
            session,
            dossier_id=state.dossier_id,
            node="recommendation",
            model=model,
            prompt_version=rec_prompt.PROMPT_VERSION,
            started_at=started,
            usage=usage,
        )
    except Exception as exc:
        reasoning_runs.record_failure(
            session,
            dossier_id=state.dossier_id,
            node="recommendation",
            model=model,
            prompt_version=rec_prompt.PROMPT_VERSION,
            started_at=started,
            detail=str(exc),
        )
        raise
    return state
