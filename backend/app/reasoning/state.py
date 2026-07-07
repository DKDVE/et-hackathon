"""Reasoning graph state (TDD §6)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import SharedContext
from app.reasoning.schemas import (
    AnalysisOutput,
    DossierSections,
    ProvisionalAction,
    ProvisionalCause,
    ProvisionalSafetyNote,
    RecommendationOutput,
    ValidatedDossier,
)


class DossierState(BaseModel):
    """Mutable working state for one dossier reasoning run."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    dossier_id: int
    shared_context: SharedContext
    analysis: AnalysisOutput | None = None
    recommendation: RecommendationOutput | None = None
    provisional_causes: list[ProvisionalCause] = Field(default_factory=list)
    provisional_notes: list[ProvisionalSafetyNote] = Field(default_factory=list)
    provisional_actions: list[ProvisionalAction] = Field(default_factory=list)
    validated: ValidatedDossier | None = None
    sections: DossierSections | None = None
    errors: list[str] = Field(default_factory=list)
    stripped_id_counts: dict[str, int] = Field(default_factory=dict)
