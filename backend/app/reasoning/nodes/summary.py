"""Executive summary LLM node (D-019 stretch, M13)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.config import get_settings
from app.llm.client import LLMClient
from app.memory.repositories import reasoning_runs
from app.reasoning.prompts import summary as summary_prompt


class SummaryOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str


def run_summary(
    *,
    dossier_id: int,
    session: Session,
    client: LLMClient,
    sections: dict,
) -> str | None:
    """One Haiku call over validated sections; None on failure (graceful)."""
    validated_only = {
        k: sections.get(k)
        for k in ("safety_notes", "probable_causes", "actions")
        if sections.get(k)
    }
    if not validated_only:
        return None

    started = datetime.now(UTC)
    model = get_settings().llm_models.get("summary", "anthropic/claude-haiku-4.5")
    messages = [
        {"role": "system", "content": summary_prompt.SYSTEM},
        {
            "role": "user",
            "content": summary_prompt.USER_TEMPLATE.format(
                sections=json.dumps(validated_only, indent=2)
            ),
        },
    ]
    try:
        output, usage = client.complete_structured("summary", messages, SummaryOutput)
        reasoning_runs.record_run(
            session,
            dossier_id=dossier_id,
            node="summary",
            model=model,
            prompt_version=summary_prompt.PROMPT_VERSION,
            started_at=started,
            usage=usage,
        )
        return output.text.strip()
    except Exception as exc:
        reasoning_runs.record_failure(
            session,
            dossier_id=dossier_id,
            node="summary",
            model=model,
            prompt_version=summary_prompt.PROMPT_VERSION,
            started_at=started,
            detail=str(exc),
        )
        return None
