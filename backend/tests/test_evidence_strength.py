"""Evidence Strength — pure property/table tests (P8, TDD §6).

No DB, no model: a synthetic ``SharedContext`` is hand-built so every score is
verifiable by hand, which is the whole point of P8.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.context.evidence import enumerate_pool, strength
from app.domain.models import (
    AssetProfile,
    ChunkRecord,
    EventInfo,
    SharedContext,
    SisterIncident,
    WorkOrderRecord,
)

REF = date(2026, 3, 1)
EVENT_TAG = "P-3401"


def _wo(number: str, tag: str, closed: date) -> WorkOrderRecord:
    return WorkOrderRecord(
        wo_number=number,
        asset_tag=tag,
        opened_on=closed,
        closed_on=closed,
        raw_description="seal leak",
        actions_taken="replaced seal",
        downtime_hours=8.0,
        failure_mode_code="mechanical_seal_leakage",
    )


def _sister(number: str, tag: str, closed: date) -> SisterIncident:
    return SisterIncident(
        wo_number=number,
        asset_tag=tag,
        asset_name=tag,
        failure_mode_code="mechanical_seal_leakage",
        opened_on=closed,
        closed_on=closed,
        raw_description="seal leak on sister",
        downtime_hours=6.0,
    )


def _chunk(chunk_id: int, doc_type: str) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        document_id=chunk_id,
        doc_type=doc_type,
        page=1,
        section_ref="6 Troubleshooting",
        content="seal leakage row",
        retrieval_channel="semantic",
    )


def _ctx(
    *,
    failure_history: list[WorkOrderRecord] | None = None,
    sister_incidents: list[SisterIncident] | None = None,
    manual: list[ChunkRecord] | None = None,
    sop: list[ChunkRecord] | None = None,
    report: list[ChunkRecord] | None = None,
) -> SharedContext:
    event = EventInfo(
        event_id=1,
        asset_tag=EVENT_TAG,
        source="simulated",
        symptom_category="seal_leak",
        note="drips at seal",
        criticality="A",
        status="open",
        occurred_at=datetime(2026, 3, 1, tzinfo=UTC),
    )
    profile = AssetProfile(
        asset_id=1, tag=EVENT_TAG, name="Ester feed pump A",
        asset_class="CP200", manufacturer="Acme", model="X", plant="P",
        unit="U", area="A", service_duty="hot organics", criticality="A",
        installed_on=date(2015, 1, 1),
    )
    shared = SharedContext(
        event=event,
        asset_profile=profile,
        failure_history=failure_history or [],
        sister_incidents=sister_incidents or [],
        manual_chunks=manual or [],
        sop_chunks=sop or [],
        report_chunks=report or [],
        pattern_stats=[],
        evidence_pool=set(),
        assembled_at=datetime.now(UTC),
    )
    pool = enumerate_pool(shared)
    return shared.model_copy(update={"evidence_pool": pool}).with_hash()


def test_empty_set_is_weak_with_zeroed_components() -> None:
    ctx = _ctx(failure_history=[_wo("WO-2026-0001", EVENT_TAG, date(2026, 2, 1))])
    res = strength([], ctx, reference_date=REF)
    assert res.tier == "Weak"
    assert res.score == 0.0
    assert res.components.count == 0
    assert res.components.source_type_diversity == 0
    assert res.components.recency_months is None
    assert res.components.sister_corroboration == 0


def test_single_recent_self_wo_is_moderate() -> None:
    ctx = _ctx(failure_history=[_wo("WO-2026-0001", EVENT_TAG, date(2026, 2, 1))])
    res = strength(["WO-2026-0001"], ctx, reference_date=REF)
    # 1*1.0 + 1(work_order)*1.5 + 2.0(recent) + 0 = 4.5
    assert res.score == 4.5
    assert res.tier == "Moderate"
    assert res.components.recency_months == 1


def test_recency_boundary_at_24_months_is_far() -> None:
    """< 24 months → near (2.0); exactly 24 → far (0.5). The boundary is exact."""
    ctx = _ctx(
        failure_history=[
            _wo("WO-FAR", EVENT_TAG, date(2024, 3, 1)),   # exactly 24 months
            _wo("WO-NEAR", EVENT_TAG, date(2024, 4, 1)),  # 23 months
        ]
    )
    far = strength(["WO-FAR"], ctx, reference_date=REF)
    assert far.components.recency_months == 24
    assert far.score == 1.0 + 1.5 + 0.5  # 3.0 → Weak
    assert far.tier == "Weak"

    near = strength(["WO-NEAR"], ctx, reference_date=REF)
    assert near.components.recency_months == 23
    assert near.score == 1.0 + 1.5 + 2.0  # 4.5 → Moderate
    assert near.tier == "Moderate"


def test_full_diversity_and_sisters_is_strong() -> None:
    ctx = _ctx(
        failure_history=[_wo("WO-SELF", EVENT_TAG, date(2026, 1, 1))],
        sister_incidents=[
            _sister("WO-S1", "P-3105", date(2026, 1, 1)),
            _sister("WO-S2", "P-3402", date(2025, 6, 1)),
            _sister("WO-S3", "P-2210", date(2025, 1, 1)),
        ],
        manual=[_chunk(101, "oem_manual")],
        sop=[_chunk(102, "sop")],
        report=[_chunk(103, "incident_report")],
    )
    ids = ["WO-SELF", "WO-S1", "WO-S2", "WO-S3", "CH-101", "CH-102", "CH-103"]
    res = strength(ids, ctx, reference_date=REF)
    # count min(7,4)=4 → 4.0 ; sources {work_order,manual,sop,report}=4 → 6.0 ;
    # recency near 2.0 ; sisters min(3,3)=3 → 4.5 ; total 16.5
    assert res.components.count == 7
    assert res.components.source_type_diversity == 4
    assert res.components.sister_corroboration == 3
    assert res.score == 16.5
    assert res.tier == "Strong"


def test_adding_evidence_never_lowers_the_tier() -> None:
    ctx = _ctx(
        failure_history=[_wo("WO-SELF", EVENT_TAG, date(2026, 1, 1))],
        sister_incidents=[
            _sister("WO-S1", "P-3105", date(2026, 1, 1)),
            _sister("WO-S2", "P-3402", date(2025, 6, 1)),
        ],
        manual=[_chunk(201, "oem_manual")],
        sop=[_chunk(202, "sop")],
        report=[_chunk(203, "incident_report")],
    )
    order = ["WO-SELF", "WO-S1", "WO-S2", "CH-201", "CH-202", "CH-203"]
    rank = {"Weak": 0, "Moderate": 1, "Strong": 2}
    prev_score = -1.0
    prev_tier = -1
    for i in range(len(order) + 1):
        res = strength(order[:i], ctx, reference_date=REF)
        assert res.score >= prev_score
        assert rank[res.tier] >= prev_tier
        prev_score, prev_tier = res.score, rank[res.tier]


def test_unresolved_and_duplicate_ids_are_ignored() -> None:
    ctx = _ctx(failure_history=[_wo("WO-2026-0001", EVENT_TAG, date(2026, 2, 1))])
    # bogus id not in pool + duplicate real id
    res = strength(
        ["WO-9999-9999", "WO-2026-0001", "WO-2026-0001"], ctx, reference_date=REF
    )
    assert res.components.count == 1  # dedup + drop unresolved
