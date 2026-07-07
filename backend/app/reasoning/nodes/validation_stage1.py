"""Stage-1 deterministic validator: pool membership (TDD §6, P2)."""

from __future__ import annotations

import logging

from app.reasoning.schemas import ProvisionalAction, ProvisionalCause, ProvisionalSafetyNote
from app.reasoning.state import DossierState

logger = logging.getLogger("oce.reasoning")


def _strip_ids(ids: list[str], pool: set[str]) -> tuple[list[str], int]:
    valid = [cid for cid in ids if cid in pool]
    return valid, len(ids) - len(valid)


def _grounding(evidence_ids: list[str]) -> str:
    return "evidenced" if evidence_ids else "hypothesis"


def run_validation_stage1(state: DossierState) -> DossierState:
    """Strip citation IDs ∉ evidence_pool; zero-survivor → hypothesis."""
    if state.analysis is None or state.recommendation is None:
        raise ValueError("analysis and recommendation required before stage-1 validation")

    pool = state.shared_context.evidence_pool
    stripped_total = 0

    causes: list[ProvisionalCause] = []
    for i, c in enumerate(state.analysis.probable_causes):
        ids, n = _strip_ids(c.evidence_ids, pool)
        stripped_total += n
        data = c.model_dump()
        data["evidence_ids"] = ids
        causes.append(
            ProvisionalCause(
                **data,
                grounding=_grounding(ids),  # type: ignore[arg-type]
                claim_ref=f"cause:{i}",
            )
        )

    notes: list[ProvisionalSafetyNote] = []
    for i, n in enumerate(state.recommendation.safety_notes):
        ids, stripped = _strip_ids(n.evidence_ids, pool)
        stripped_total += stripped
        data = n.model_dump()
        data["evidence_ids"] = ids
        notes.append(
            ProvisionalSafetyNote(
                **data,
                grounding=_grounding(ids),  # type: ignore[arg-type]
                claim_ref=f"safety:{i}",
            )
        )

    actions: list[ProvisionalAction] = []
    for i, a in enumerate(state.recommendation.actions):
        ids, stripped = _strip_ids(a.evidence_ids, pool)
        stripped_total += stripped
        data = a.model_dump()
        data["evidence_ids"] = ids
        actions.append(
            ProvisionalAction(
                **data,
                grounding=_grounding(ids),  # type: ignore[arg-type]
                claim_ref=f"action:{i}",
            )
        )

    state.stripped_id_counts["stage1"] = stripped_total
    state.provisional_causes = causes
    state.provisional_notes = notes
    state.provisional_actions = actions
    logger.info(
        "validation stage-1 complete",
        extra={"stripped_ids": stripped_total, "dossier_id": state.dossier_id},
    )
    return state


def provisional_analysis_payload(state: DossierState) -> dict:
    return {
        "probable_causes": [c.model_dump() for c in state.provisional_causes],
        "provisional": True,
    }


def provisional_recommendation_payload(state: DossierState) -> dict:
    return {
        "safety_notes": [n.model_dump() for n in state.provisional_notes],
        "actions": [a.model_dump() for a in state.provisional_actions],
        "provisional": True,
    }
