"""Structured output schemas for the reasoning graph (TDD §6, D-019)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Grounding = Literal["evidenced", "hypothesis"]
ValidationVerdictKind = Literal["supported", "unsupported_evidence", "no_evidence"]


class ProbableCause(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str
    mechanism_explanation: str
    evidence_ids: list[str] = Field(default_factory=list)
    asset_specific_notes: str | None = None


class AnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    probable_causes: list[ProbableCause] = Field(min_length=1, max_length=4)


class SafetyNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    evidence_ids: list[str] = Field(default_factory=list)


class RecommendedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    sop_refs: list[str] = Field(default_factory=list)


class RecommendationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    safety_notes: list[SafetyNote] = Field(default_factory=list, max_length=3)
    actions: list[RecommendedAction] = Field(default_factory=list, max_length=5)


class ClaimValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_ref: str
    verdict: ValidationVerdictKind
    evidence_ids_confirmed: list[str] = Field(default_factory=list)


class ValidationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[ClaimValidation] = Field(default_factory=list)


class ProvisionalCause(ProbableCause):
    grounding: Grounding = "evidenced"
    claim_ref: str = ""


class ProvisionalSafetyNote(SafetyNote):
    grounding: Grounding = "evidenced"
    claim_ref: str = ""


class ProvisionalAction(RecommendedAction):
    grounding: Grounding = "evidenced"
    claim_ref: str = ""


class ValidatedCause(ProbableCause):
    grounding: Grounding
    claim_ref: str
    strength_tier: Literal["Strong", "Moderate", "Weak"] | None = None


class ValidatedSafetyNote(SafetyNote):
    grounding: Grounding
    claim_ref: str


class ValidatedAction(RecommendedAction):
    grounding: Grounding
    claim_ref: str


class ValidatedDossier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    probable_causes: list[ValidatedCause] = Field(default_factory=list)
    safety_notes: list[ValidatedSafetyNote] = Field(default_factory=list)
    actions: list[ValidatedAction] = Field(default_factory=list)


class DossierSections(BaseModel):
    """Persisted ``dossiers.sections`` JSON (PRD §9 order)."""

    model_config = ConfigDict(extra="forbid")

    safety_notes: list[ValidatedSafetyNote] = Field(default_factory=list)
    probable_causes: list[ValidatedCause] = Field(default_factory=list)
    actions: list[ValidatedAction] = Field(default_factory=list)
    executive_summary: str | None = None


class ChatOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    citations: list[str] = Field(default_factory=list)
    refused: bool
