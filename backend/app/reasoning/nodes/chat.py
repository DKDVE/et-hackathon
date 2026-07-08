"""Contextual chat node — answers only from frozen dossier context (FR-9, P1/P4)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Dossier
from app.domain.models import SharedContext
from app.llm.client import LLMClient, NodeFailure
from app.memory.repositories import reasoning_runs
from app.reasoning.post_check import post_check_citations
from app.reasoning.prompts import chat as chat_prompt
from app.reasoning.prompts.context_render import render_dossier_context
from app.reasoning.schemas import ChatOutput

MAX_HISTORY_TURNS = 6


def _format_history(history: list[dict[str, str]]) -> str:
    if not history:
        return "(none)"
    lines: list[str] = []
    for turn in history[-MAX_HISTORY_TURNS:]:
        role = turn.get("role", "user")
        text = turn.get("text", "").strip()
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines) if lines else "(none)"


def run_chat(
    *,
    dossier_id: int,
    session: Session,
    client: LLMClient,
    shared_context: SharedContext,
    sections: dict,
    question: str,
    history: list[dict[str, str]],
) -> dict:
    """One chat turn. Reads only dossier row fields; writes reasoning_runs."""
    started = datetime.now(UTC)
    capped_history = history[-MAX_HISTORY_TURNS:]
    ctx_text = render_dossier_context(shared_context, sections)
    messages = [
        {"role": "system", "content": chat_prompt.SYSTEM},
        {
            "role": "user",
            "content": chat_prompt.USER_TEMPLATE.format(
                context=ctx_text,
                history=_format_history(capped_history),
                question=question.strip(),
            ),
        },
    ]
    model = get_settings().llm_models.get("chat", "anthropic/claude-haiku-4.5")
    try:
        output, usage = client.complete_structured("chat", messages, ChatOutput)
        reasoning_runs.record_run(
            session,
            dossier_id=dossier_id,
            node="chat",
            model=model,
            prompt_version=chat_prompt.PROMPT_VERSION,
            started_at=started,
            usage=usage,
        )
    except NodeFailure as exc:
        reasoning_runs.record_failure(
            session,
            dossier_id=dossier_id,
            node="chat",
            model=model,
            prompt_version=chat_prompt.PROMPT_VERSION,
            started_at=started,
            detail=str(exc),
        )
        raise

    pool = set(shared_context.evidence_pool)
    raw_citations = list(output.citations)
    citations, grounding = post_check_citations(raw_citations, pool, refused=output.refused)
    stripped = len(raw_citations) - len(citations)
    if stripped:
        dossier = session.get(Dossier, dossier_id)
        if dossier is not None:
            stats = dict(dossier.guardrail_stats or {})
            stats["chat_citations_stripped"] = stats.get("chat_citations_stripped", 0) + stripped
            dossier.guardrail_stats = stats
            session.commit()
    result: dict = {
        "answer": output.answer.strip(),
        "citations": citations,
        "refused": output.refused,
    }
    if grounding == "hypothesis":
        result["grounding"] = "hypothesis"
    return result
