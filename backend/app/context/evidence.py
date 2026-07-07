"""Evidence pool enumeration + Evidence Strength (P8/D-003, TDD §6).

Pure functions over a frozen ``SharedContext``. No LLM, no DB: every number here
is hand-computable from enumerable inputs, which is the whole point (P8). The
Strength formula and tier cuts are TDD §6 verbatim; the constants live in config.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.config import get_settings
from app.domain.models import (
    ChunkRecord,
    SharedContext,
    SisterIncident,
    WorkOrderRecord,
)

Tier = Literal["Strong", "Moderate", "Weak"]


# --- evidence pool ----------------------------------------------------------

def pool_from_records(
    failure_history: Iterable[WorkOrderRecord],
    sister_incidents: Iterable[SisterIncident],
    *chunk_groups: Iterable[ChunkRecord],
) -> set[str]:
    """Every citation ID present across the given record groups (TDD §4)."""
    pool: set[str] = set()
    pool.update(wo.citation_id for wo in failure_history)
    pool.update(si.citation_id for si in sister_incidents)
    for group in chunk_groups:
        pool.update(c.citation_id for c in group)
    return pool


def enumerate_pool(ctx: SharedContext) -> set[str]:
    """The evidence pool of an assembled context (P3/P4 set-membership spine)."""
    return pool_from_records(
        ctx.failure_history,
        ctx.sister_incidents,
        ctx.manual_chunks,
        ctx.sop_chunks,
        ctx.report_chunks,
    )


# --- Evidence Strength ------------------------------------------------------

class StrengthComponents(BaseModel):
    model_config = ConfigDict(frozen=True)

    count: int
    source_type_diversity: int
    recency_months: int | None
    sister_corroboration: int


class StrengthResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tier: Tier
    score: float
    components: StrengthComponents


def _chunk_source_type(doc_type: str) -> str:
    if doc_type == "oem_manual":
        return "manual"
    if doc_type == "sop":
        return "sop"
    return "report"  # inspection_report / incident_report


def strength(
    evidence_ids: Sequence[str],
    ctx: SharedContext,
    *,
    reference_date: date | None = None,
) -> StrengthResult:
    """Evidence Strength for a claim's surviving evidence set (TDD §6).

        score = min(count, 4) * 1.0
              + distinct_source_types * 1.5
              + (2.0 if newest_supporting_record < 24 months else 0.5)
              + min(distinct_sister_assets, 3) * 1.5
        Strong >= 8, Moderate >= 4, else Weak.

    Only IDs that resolve within ``ctx`` (are in the pool) count. The empty set
    → Weak with all components zeroed. Adding evidence can never lower the tier
    (every term is monotonic non-decreasing in the evidence set).
    """
    cfg = get_settings()
    ref = reference_date or date.today()

    wo_index: dict[str, tuple[str, date | None]] = {}  # cid -> (asset_tag, date)
    for wo in ctx.failure_history:
        wo_index[wo.citation_id] = (wo.asset_tag, wo.closed_on or wo.opened_on)
    for si in ctx.sister_incidents:
        wo_index[si.citation_id] = (si.asset_tag, si.closed_on or si.opened_on)
    chunk_index: dict[str, str] = {}
    for group in (ctx.manual_chunks, ctx.sop_chunks, ctx.report_chunks):
        for c in group:
            chunk_index[c.citation_id] = _chunk_source_type(c.doc_type)

    pool = enumerate_pool(ctx)
    resolved = [cid for cid in dict.fromkeys(evidence_ids) if cid in pool]

    if not resolved:
        return StrengthResult(
            tier="Weak",
            score=0.0,
            components=StrengthComponents(
                count=0, source_type_diversity=0, recency_months=None, sister_corroboration=0
            ),
        )

    source_types: set[str] = set()
    sister_tags: set[str] = set()
    newest: date | None = None
    for cid in resolved:
        if cid in wo_index:
            source_types.add("work_order")
            tag, d = wo_index[cid]
            if tag != ctx.event.asset_tag:
                sister_tags.add(tag)
            if d is not None and (newest is None or d > newest):
                newest = d
        elif cid in chunk_index:
            source_types.add(chunk_index[cid])

    recency_months: int | None = None
    if newest is not None:
        recency_months = (ref.year - newest.year) * 12 + (ref.month - newest.month)

    count = len(resolved)
    diversity = len(source_types)
    sisters = len(sister_tags)
    recency_term = (
        cfg.evidence_w_recency_near
        if recency_months is not None and recency_months < cfg.evidence_recency_threshold_months
        else cfg.evidence_w_recency_far
    )
    score = (
        min(count, cfg.evidence_cap_count) * cfg.evidence_w_count
        + diversity * cfg.evidence_w_source_type
        + recency_term
        + min(sisters, cfg.evidence_cap_sister) * cfg.evidence_w_sister
    )
    tier: Tier = (
        "Strong"
        if score >= cfg.evidence_strength_strong
        else "Moderate"
        if score >= cfg.evidence_strength_moderate
        else "Weak"
    )
    return StrengthResult(
        tier=tier,
        score=round(score, 4),
        components=StrengthComponents(
            count=count,
            source_type_diversity=diversity,
            recency_months=recency_months,
            sister_corroboration=sisters,
        ),
    )
