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
