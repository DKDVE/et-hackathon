"""Validation stage-2 LLM node."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.models import SharedContext
from app.llm.client import LLMClient
from app.memory.repositories import reasoning_runs
from app.reasoning.prompts import validation as val_prompt
from app.reasoning.schemas import (
    ProvisionalAction,
    ProvisionalCause,
    ProvisionalSafetyNote,
    ValidatedAction,
    ValidatedCause,
    ValidatedDossier,
    ValidatedSafetyNote,
    ValidationOutput,
)
from app.reasoning.state import DossierState


def _resolve_text(cid: str, ctx: SharedContext) -> str:
    for wo in ctx.failure_history:
        if wo.citation_id == cid:
            return wo.raw_description
    for si in ctx.sister_incidents:
        if si.citation_id == cid:
            return si.raw_description
    for group in (ctx.manual_chunks, ctx.sop_chunks, ctx.report_chunks):
        for c in group:
            if c.citation_id == cid:
                return c.content
    return "(unknown)"


def _claims_block(
    causes: list[ProvisionalCause],
    notes: list[ProvisionalSafetyNote],
    actions: list[ProvisionalAction],
    ctx: SharedContext,
) -> str:
    lines: list[str] = []
    for c in causes:
        cited = "\n".join(
            f"  - {cid}: {_resolve_text(cid, ctx)[:300]}" for cid in c.evidence_ids
        )
        lines.append(
            f"claim_ref={c.claim_ref}\n"
            f"text: {c.statement}\n"
            f"mechanism: {c.mechanism_explanation}\n"
            f"cited:\n{cited or '  (none)'}"
        )
    for n in notes:
        cited = "\n".join(
            f"  - {cid}: {_resolve_text(cid, ctx)[:300]}" for cid in n.evidence_ids
        )
        lines.append(f"claim_ref={n.claim_ref}\ntext: {n.text}\ncited:\n{cited or '  (none)'}")
    for a in actions:
        cited = "\n".join(
            f"  - {cid}: {_resolve_text(cid, ctx)[:300]}" for cid in a.evidence_ids
        )
        lines.append(
            f"claim_ref={a.claim_ref}\ntext: {a.text}\nrationale: {a.rationale}\n"
            f"cited:\n{cited or '  (none)'}"
        )
    return "\n\n---\n\n".join(lines)


def _apply_verdicts(
    state: DossierState,
    output: ValidationOutput,
) -> ValidatedDossier:
    verdicts = {v.claim_ref: v for v in output.claims}
    pool = state.shared_context.evidence_pool
    stage2_removed = 0

    causes: list[ValidatedCause] = []
    for c in state.provisional_causes:
        v = verdicts.get(c.claim_ref)
        if v is None:
            ids = [x for x in c.evidence_ids if x in pool]
            grounding = "evidenced" if ids else "hypothesis"
        elif v.verdict == "supported":
            ids = [x for x in v.evidence_ids_confirmed if x in pool]
            grounding = "evidenced" if ids else "hypothesis"
        elif v.verdict == "unsupported_evidence":
            ids = [x for x in v.evidence_ids_confirmed if x in pool]
            grounding = "evidenced" if ids else "hypothesis"
        else:
            ids = []
            grounding = "hypothesis"
        stage2_removed += max(0, len(c.evidence_ids) - len(ids))
        causes.append(
            ValidatedCause(
                statement=c.statement,
                mechanism_explanation=c.mechanism_explanation,
                evidence_ids=ids,
                asset_specific_notes=c.asset_specific_notes,
                grounding=grounding,  # type: ignore[arg-type]
                claim_ref=c.claim_ref,
            )
        )

    notes: list[ValidatedSafetyNote] = []
    for n in state.provisional_notes:
        v = verdicts.get(n.claim_ref)
        ids = _final_ids(n.evidence_ids, v, pool)
        stage2_removed += max(0, len(n.evidence_ids) - len(ids))
        grounding = "evidenced" if ids else "hypothesis"
        notes.append(
            ValidatedSafetyNote(
                text=n.text,
                evidence_ids=ids,
                grounding=grounding,  # type: ignore[arg-type]
                claim_ref=n.claim_ref,
            )
        )

    actions: list[ValidatedAction] = []
    for a in state.provisional_actions:
        v = verdicts.get(a.claim_ref)
        ids = _final_ids(a.evidence_ids, v, pool)
        stage2_removed += max(0, len(a.evidence_ids) - len(ids))
        grounding = "evidenced" if ids else "hypothesis"
        actions.append(
            ValidatedAction(
                text=a.text,
                rationale=a.rationale,
                evidence_ids=ids,
                sop_refs=a.sop_refs if ids else [],
                grounding=grounding,  # type: ignore[arg-type]
                claim_ref=a.claim_ref,
            )
        )

    state.stripped_id_counts["stage2"] = stage2_removed
    return ValidatedDossier(probable_causes=causes, safety_notes=notes, actions=actions)


def _final_ids(
    original: list[str],
    verdict: object | None,
    pool: set[str],
) -> list[str]:
    from app.reasoning.schemas import ClaimValidation

    if verdict is None or not isinstance(verdict, ClaimValidation):
        return [x for x in original if x in pool]
    if verdict.verdict == "supported":
        return [x for x in verdict.evidence_ids_confirmed if x in pool]
    if verdict.verdict == "unsupported_evidence":
        return [x for x in verdict.evidence_ids_confirmed if x in pool]
    return []


def run_validation_stage2(state: DossierState, session: Session, client: LLMClient) -> DossierState:
    started = datetime.now(UTC)
    claims = _claims_block(
        state.provisional_causes,
        state.provisional_notes,
        state.provisional_actions,
        state.shared_context,
    )
    messages = [
        {"role": "system", "content": val_prompt.SYSTEM},
        {"role": "user", "content": val_prompt.USER_TEMPLATE.format(claims_block=claims)},
    ]
    model = get_settings().llm_models.get("validation", "anthropic/claude-sonnet-4.6")
    try:
        output, usage = client.complete_structured("validation", messages, ValidationOutput)
        state.validated = _apply_verdicts(state, output)  # type: ignore[arg-type]
        reasoning_runs.record_run(
            session,
            dossier_id=state.dossier_id,
            node="validation",
            model=model,
            prompt_version=val_prompt.PROMPT_VERSION,
            started_at=started,
            usage=usage,
        )
    except Exception as exc:
        reasoning_runs.record_failure(
            session,
            dossier_id=state.dossier_id,
            node="validation",
            model=model,
            prompt_version=val_prompt.PROMPT_VERSION,
            started_at=started,
            detail=str(exc),
        )
        raise
    return state


def validated_payload(state: DossierState) -> dict:
    """SSE validated event — includes strength tiers (attached in report step)."""
    if state.validated is None:
        return {}
    from app.reasoning.nodes.report import attach_strength

    enriched = attach_strength(state.validated, state.shared_context)
    return {
        "probable_causes": [c.model_dump() for c in enriched.probable_causes],
        "safety_notes": [n.model_dump() for n in enriched.safety_notes],
        "actions": [a.model_dump() for a in enriched.actions],
        "provisional": False,
    }
