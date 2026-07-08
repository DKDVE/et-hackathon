"""Deterministic report step (D-019): strength, sections, evidence_links."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.context.evidence import strength
from app.db.models import Chunk, Dossier, DossierStatus, EvidenceKind, EvidenceLink, WorkOrder
from app.domain.models import SharedContext
from app.reasoning.schemas import (
    DossierSections,
    ValidatedAction,
    ValidatedCause,
    ValidatedDossier,
    ValidatedSafetyNote,
)
from app.reasoning.state import DossierState


def compute_guardrail_stats(state: DossierState) -> dict[str, int]:
    """Aggregate structural guardrail counters for ops (M11)."""
    validated = state.validated
    hypothesis_claims = 0
    safety_deleted = 0
    if validated is not None:
        for claim in (*validated.probable_causes, *validated.actions):
            if claim.grounding == "hypothesis":
                hypothesis_claims += 1
        for note in validated.safety_notes:
            if note.grounding == "hypothesis":
                safety_deleted += 1
    return {
        "stage1_stripped_citations": state.stripped_id_counts.get("stage1", 0),
        "stage2_unsupported_removed": state.stripped_id_counts.get("stage2", 0),
        "hypothesis_claims": hypothesis_claims,
        "safety_notes_deleted": safety_deleted,
        "chat_citations_stripped": 0,
    }


def attach_strength(validated: ValidatedDossier, ctx: SharedContext) -> ValidatedDossier:
    causes: list[ValidatedCause] = []
    for c in validated.probable_causes:
        tier = None
        if c.grounding == "evidenced" and c.evidence_ids:
            tier = strength(c.evidence_ids, ctx).tier
        causes.append(c.model_copy(update={"strength_tier": tier}))
    return validated.model_copy(update={"probable_causes": causes})


def persist_validated(
    session: Session,
    dossier_id: int,
    validated_data: dict,
    ctx: SharedContext,
    *,
    guardrail_stats: dict[str, int] | None = None,
) -> DossierSections:
    """Build sections from validated payload and persist (live report or fallback replay)."""
    cleaned = {k: v for k, v in validated_data.items() if k not in ("provisional", "cached")}
    validated = ValidatedDossier.model_validate(cleaned)
    enriched = attach_strength(validated, ctx)
    safe_notes = [n for n in enriched.safety_notes if n.grounding == "evidenced"]
    sections = DossierSections(
        safety_notes=safe_notes,
        probable_causes=enriched.probable_causes,
        actions=enriched.actions,
    )
    dossier = session.get(Dossier, dossier_id)
    if dossier is None:
        raise ValueError(f"dossier {dossier_id} not found")
    dossier.sections = sections.model_dump(mode="json")
    dossier.status = DossierStatus.complete
    dossier.completed_at = datetime.now(UTC)
    if guardrail_stats is not None:
        dossier.guardrail_stats = guardrail_stats
    session.execute(delete(EvidenceLink).where(EvidenceLink.dossier_id == dossier_id))
    for claim in _all_claims(sections):
        for cid in claim.evidence_ids:
            _link_evidence(session, dossier_id, claim.claim_ref, cid)
    session.commit()
    return sections


def run_report(state: DossierState, session: Session) -> DossierState:
    if state.validated is None:
        raise ValueError("validated dossier required before report")
    stats = compute_guardrail_stats(state)
    state.sections = persist_validated(
        session,
        state.dossier_id,
        state.validated.model_dump(),
        state.shared_context,
        guardrail_stats=stats,
    )
    return state


def _all_claims(
    sections: DossierSections,
) -> list[ValidatedCause | ValidatedSafetyNote | ValidatedAction]:
    return [*sections.safety_notes, *sections.probable_causes, *sections.actions]


def _link_evidence(session: Session, dossier_id: int, claim_ref: str, citation_id: str) -> None:
    if citation_id.startswith("WO-"):
        wo_id = session.scalar(
            select(WorkOrder.id).where(WorkOrder.wo_number == citation_id)
        )
        if wo_id is None:
            return
        session.add(
            EvidenceLink(
                dossier_id=dossier_id,
                claim_ref=claim_ref,
                evidence_kind=EvidenceKind.work_order,
                work_order_id=wo_id,
            )
        )
    elif citation_id.startswith("CH-"):
        chunk_id = int(citation_id[3:])
        if session.get(Chunk, chunk_id) is None:
            return
        session.add(
            EvidenceLink(
                dossier_id=dossier_id,
                claim_ref=claim_ref,
                evidence_kind=EvidenceKind.chunk,
                chunk_id=chunk_id,
            )
        )
