"""API request/response schemas (TDD §7).

The reasoning-facing shapes (``analysis``/``recommendation``/``validated``/
``report``) are declared here as the FULL vocabulary so the OpenAPI-generated
frontend types are complete now; M5 simply never populates them. This is the
seam that lets M6 slot in without a frontend change.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.db.models import Criticality, EventSource
from app.domain.models import SharedContext

# --- events -----------------------------------------------------------------


class EventCreate(BaseModel):
    """Canonical Operational Event intake (P6/D-011). ``source`` and
    ``criticality`` are enum-validated by pydantic; ``asset_tag`` existence and
    ``symptom_category`` membership are validated in the handler."""

    asset_tag: str = Field(min_length=1)
    source: EventSource
    symptom_category: str = Field(min_length=1)
    note: str | None = None
    criticality: Criticality


class EventSummary(BaseModel):
    """Event board row + single-event view."""

    id: int
    asset_tag: str
    asset_name: str
    plant: str
    unit: str
    source: str
    symptom_category: str
    note: str | None
    criticality: str
    status: str
    occurred_at: datetime
    created_at: datetime
    dossier_id: int | None = None


# --- dossiers ---------------------------------------------------------------

DegradeReason = Literal["reasoning_disabled", "llm_failure", "node_failure"]


class DegradedInfo(BaseModel):
    reason: DegradeReason
    deterministic_available: bool = True


class DossierResponse(BaseModel):
    """Full dossier JSON (GET) and the ``context_ready`` SSE payload share this
    shape. ``context`` is the frozen deterministic Shared Context; ``sections``
    holds validated AI outputs (null until M6); ``degraded`` is set when the
    reasoning layer did not (or could not) run."""

    dossier_id: int
    event_id: int
    status: str
    reasoning_enabled: bool
    evidence_pool_size: int
    context: SharedContext | None = None
    sections: dict[str, Any] | None = None
    degraded: DegradedInfo | None = None


# --- sources ----------------------------------------------------------------


class WorkOrderSource(BaseModel):
    wo_number: str
    citation_id: str
    asset_tag: str
    asset_name: str
    opened_on: date | None = None
    closed_on: date | None = None
    raw_description: str
    actions_taken: str | None = None
    downtime_hours: float | None = None
    failure_mode_code: str | None = None
    failure_mode_name: str | None = None


class ChunkSource(BaseModel):
    chunk_id: int
    citation_id: str
    document_id: int
    doc_type: str
    document_title: str
    page: int
    section_ref: str | None = None
    content: str
    file_url: str


# --- assets -----------------------------------------------------------------


class AssetSummary(BaseModel):
    asset_id: int
    tag: str
    name: str
    asset_class: str
    plant: str
    unit: str
    area: str
    service_duty: str
    criticality: str


# --- evidence (contract only in M5; populated in M6) ------------------------


class EvidenceBreakdown(BaseModel):
    claim_ref: str
    tier: str
    score: float
    components: dict[str, Any]
    evidence_ids: list[str]


# --- chat (FR-9) -------------------------------------------------------------


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    history: list[ChatTurn] = Field(default_factory=list, max_length=6)


class ChatResponse(BaseModel):
    answer: str
    citations: list[str]
    refused: bool
    grounding: Literal["evidenced", "hypothesis"] | None = None


# --- config (D-021) ----------------------------------------------------------


class AppConfig(BaseModel):
    downtime_cost_per_hour_inr: int
    downtime_cost_label: str
    model_costs: dict[str, dict[str, float]]


# --- reasoning trace (D-016) -------------------------------------------------


class ReasoningRunRow(BaseModel):
    id: int
    node: str
    model: str
    prompt_version: str
    started_at: datetime
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    status: str


class ReasoningRunsResponse(BaseModel):
    runs: list[ReasoningRunRow]
    replayed_from_cache: bool = False
    total_latency_ms: int
    total_prompt_tokens: int
    total_completion_tokens: int
    estimated_cost_usd: float
    cost_footnote: str


# --- ops (M11) ---------------------------------------------------------------


class OpsRunRow(BaseModel):
    id: int
    dossier_id: int
    event_id: int
    node: str
    model: str
    prompt_version: str
    started_at: datetime
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    status: str


class OpsRunsResponse(BaseModel):
    runs: list[OpsRunRow]
    limit: int
    offset: int


class OpsCostsResponse(BaseModel):
    total_estimated_cost_usd: float
    today_estimated_cost_usd: float
    by_model: dict[str, dict[str, float | int]]
    by_day: dict[str, dict[str, float | int]]
    cost_footnote: str


class EvalRunRow(BaseModel):
    id: int
    suite: str
    started_at: datetime
    finished_at: datetime
    git_ref: str
    prompt_versions: dict[str, Any]
    status: str
    metrics: dict[str, Any]
    detail: dict[str, Any] | None = None


class EvalRunsResponse(BaseModel):
    history: list[EvalRunRow]
    latest_by_suite: dict[str, EvalRunRow | None]


class GuardrailDossierRow(BaseModel):
    dossier_id: int
    event_id: int
    completed_at: datetime | None
    stats: dict[str, int]


class GuardrailsResponse(BaseModel):
    fleet_totals: dict[str, int]
    not_recorded_count: int
    dossiers: list[GuardrailDossierRow]


class RateLimitDetail(BaseModel):
    message: str = "Rate limit reached — try again in a moment."


# --- memory layer (M12, D-012/D-023) ----------------------------------------


class MemoryOverview(BaseModel):
    asset_count: int
    document_count: int
    chunk_count: int
    work_order_count: int
    wo_auto_classified: int
    wo_unclassified: int
    wo_human_reviewed: int
    taxonomy_size: int


class MemoryAssetRow(BaseModel):
    asset_id: int
    tag: str
    name: str
    asset_class: str
    manual_available: bool
    sop_count: int
    wo_count: int
    last_inspection_date: date | None
    classified_ratio: float
    coverage_tier: Literal["Good", "Partial", "Thin"]


class MemoryAssetsResponse(BaseModel):
    assets: list[MemoryAssetRow]
    coverage_footnote: str


class MemoryDocumentRow(BaseModel):
    document_id: int
    title: str
    doc_type: str
    owner_asset_tag: str | None
    owner_class: str | None
    chunk_count: int
    ocr_page_count: int
    file_url: str


class ModeCandidate(BaseModel):
    mode_id: int
    code: str
    name: str
    score: float


class TaxonomyModeRow(BaseModel):
    mode_id: int
    code: str
    name: str
    auto_wo_count: int
    human_override_count: int
    mean_normalization_score: float | None


class TaxonomyFamilyGroup(BaseModel):
    family: str
    modes: list[TaxonomyModeRow]


class ReviewQueueRow(BaseModel):
    wo_id: int
    wo_number: str
    asset_tag: str
    raw_description: str
    auto_failure_mode_code: str | None
    auto_failure_mode_family: str | None
    normalization_score: float | None
    candidates: list[ModeCandidate]


class ReviewVerdictRequest(BaseModel):
    verdict: Literal["confirmed", "corrected", "unclassifiable"]
    failure_mode_id: int | None = None


class ReviewVerdictResponse(BaseModel):
    wo_id: int
    wo_number: str
    human_verdict: str
    human_failure_mode_id: int | None
    human_failure_mode_code: str | None
    human_reviewed_at: datetime
    # D-023: auto columns echoed read-only for provenance audit
    failure_mode_id: int | None
    normalization_score: float | None
