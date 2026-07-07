"""Analysis LLM node."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.llm.client import LLMClient
from app.memory.repositories import reasoning_runs
from app.reasoning.prompts import analysis as analysis_prompt
from app.reasoning.prompts.context_render import render_shared_context
from app.reasoning.schemas import AnalysisOutput
from app.reasoning.state import DossierState


def run_analysis(state: DossierState, session: Session, client: LLMClient) -> DossierState:
    started = datetime.now(UTC)
    ctx_text = render_shared_context(state.shared_context)
    messages = [
        {"role": "system", "content": analysis_prompt.SYSTEM},
        {
            "role": "user",
            "content": analysis_prompt.USER_TEMPLATE.format(context=ctx_text),
        },
    ]
    model = get_settings().llm_models.get("analysis", "anthropic/claude-sonnet-4.6")
    try:
        output, usage = client.complete_structured("analysis", messages, AnalysisOutput)
        state.analysis = output  # type: ignore[assignment]
        reasoning_runs.record_run(
            session,
            dossier_id=state.dossier_id,
            node="analysis",
            model=model,
            prompt_version=analysis_prompt.PROMPT_VERSION,
            started_at=started,
            usage=usage,
        )
    except Exception as exc:
        reasoning_runs.record_failure(
            session,
            dossier_id=state.dossier_id,
            node="analysis",
            model=model,
            prompt_version=analysis_prompt.PROMPT_VERSION,
            started_at=started,
            detail=str(exc),
        )
        raise
    return state
