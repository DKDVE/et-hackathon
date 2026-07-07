"""Frozen domain models — the ubiquitous language of the OCE.

Every model is immutable (``ConfigDict(frozen=True)``) so a ``SharedContext``
cannot mutate during a reasoning session (P4). Citation IDs are the evidence
contract (TDD §4): ``WO-{wo_number}`` for work orders, ``CH-{chunk_id}`` for
chunks. ``SharedContext.content_hash`` is the determinism fingerprint (P2):
sha256 of the canonical JSON with sorted keys and timestamps excluded.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, computed_field

RetrievalChannel = Literal["semantic", "lexical", "both"]


def _wo_citation(wo_number: str) -> str:
    """Work-order citation ID (TDD §4). The Meridian dataset's wo_number already
    carries the ``WO-`` prefix (e.g. ``WO-2024-0117``), so the contract is the
    wo_number itself; we only add the prefix if a bare number is ever supplied."""
    return wo_number if wo_number.startswith("WO-") else f"WO-{wo_number}"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class EventInfo(_Frozen):
    event_id: int
    asset_tag: str
    source: str
    symptom_category: str
    note: str | None
    criticality: str
    status: str
    occurred_at: datetime


class AssetProfile(_Frozen):
    asset_id: int
    tag: str
    name: str
    asset_class: str
    manufacturer: str
    model: str
    plant: str
    unit: str
    area: str
    service_duty: str
    criticality: str
    installed_on: date | None


class WorkOrderRecord(_Frozen):
    wo_number: str
    asset_tag: str
    opened_on: date
    closed_on: date | None
    raw_description: str
    actions_taken: str | None
    downtime_hours: float | None
    failure_mode_code: str | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def citation_id(self) -> str:
        return _wo_citation(self.wo_number)


class SisterIncident(_Frozen):
    wo_number: str
    asset_tag: str
    asset_name: str
    failure_mode_code: str | None
    opened_on: date
    closed_on: date | None
    raw_description: str
    downtime_hours: float | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def citation_id(self) -> str:
        return _wo_citation(self.wo_number)


class ChunkRecord(_Frozen):
    chunk_id: int
    document_id: int
    doc_type: str
    page: int
    section_ref: str | None
    content: str
    retrieval_channel: RetrievalChannel

    @computed_field  # type: ignore[prop-decorator]
    @property
    def citation_id(self) -> str:
        return f"CH-{self.chunk_id}"


class PatternStat(_Frozen):
    failure_mode: str
    occurrences: int
    span_months: int
    total_downtime_hours: float
    distinct_phrasings: list[str]
    asset_tags: list[str]


class SharedContext(_Frozen):
    event: EventInfo
    asset_profile: AssetProfile
    failure_history: list[WorkOrderRecord]
    sister_incidents: list[SisterIncident]
    manual_chunks: list[ChunkRecord]
    sop_chunks: list[ChunkRecord]
    report_chunks: list[ChunkRecord]
    pattern_stats: list[PatternStat]
    evidence_pool: set[str]
    assembled_at: datetime
    content_hash: str = ""

    def canonical_payload(self) -> dict[str, Any]:
        """The hash input: everything except the volatile timestamp and the
        hash itself, with the ``evidence_pool`` set imposed into a stable
        order (str hashing is per-process randomized; sorting removes it)."""
        data = self.model_dump(mode="json", exclude={"content_hash", "assembled_at"})
        data["evidence_pool"] = sorted(self.evidence_pool)
        return data

    def compute_hash(self) -> str:
        canonical = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def with_hash(self) -> SharedContext:
        """Return a copy whose ``content_hash`` is the fingerprint of its data."""
        return self.model_copy(update={"content_hash": self.compute_hash()})
