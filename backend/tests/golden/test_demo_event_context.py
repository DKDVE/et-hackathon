"""Golden assertions for THE demo event (M4 acceptance #2/#3/#5).

The demo asset P-3401 with a seal-leak note must assemble into a context that
tells the mechanical-seal story: the self work order in the pool, the two
corroborating sister incidents present, the misalignment herring absent, the
planted pattern quantified, and the right manual/SOP/report clauses retrieved.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.context.evidence import enumerate_pool
from app.db.engine import SessionLocal
from app.db.models import Dossier

from .conftest import Assembled, assert_pool_integrity

pytestmark = pytest.mark.slow

HERRING_WO = "WO-2024-0662"  # P-2210 shaft_misalignment — must NOT be a sister incident


def test_self_wo_in_pool(demo: Assembled) -> None:
    assert "WO-2024-0117" in demo.ctx.evidence_pool


def test_sister_incidents_present(demo: Assembled) -> None:
    sisters = {si.wo_number: si.asset_tag for si in demo.ctx.sister_incidents}
    assert sisters.get("WO-2025-0289") == "P-3105"
    assert sisters.get("WO-2026-0034") == "P-3402"


def test_misalignment_herring_absent(demo: Assembled) -> None:
    numbers = {si.wo_number for si in demo.ctx.sister_incidents}
    assert HERRING_WO not in numbers
    assert not any(si.asset_tag == "P-2210" and si.failure_mode_code == "shaft_misalignment"
                   for si in demo.ctx.sister_incidents)


def test_planted_pattern_row(demo: Assembled) -> None:
    """The planted mechanical-seal pattern is present with exact values.

    NOTE (deviation): the row is asserted by *existence*, not as ``[0]``. Task-3
    sorts pattern_stats by cumulative downtime, and seal_flush_line_blockage
    accrues ~99h across the frozen sister history vs 41h for the planted 3-WO
    seal pattern — so it legitimately sorts on top. The substrate is frozen
    (M4 rule), so we assert the demo pattern's exact figures wherever it ranks.
    """
    rows = {p.failure_mode: p for p in demo.ctx.pattern_stats}
    assert "mechanical_seal_leakage" in rows
    p = rows["mechanical_seal_leakage"]
    assert p.occurrences == 3
    assert p.span_months == 22
    assert p.total_downtime_hours == 41.0
    assert len(p.distinct_phrasings) == 3
    assert set(p.asset_tags) == {"P-3401", "P-3105", "P-3402"}


def test_pattern_stats_sorted_by_downtime(demo: Assembled) -> None:
    downtimes = [p.total_downtime_hours for p in demo.ctx.pattern_stats]
    assert downtimes == sorted(downtimes, reverse=True)


def test_manual_troubleshooting_and_cartridge_clauses(demo: Assembled) -> None:
    refs = [c.section_ref or "" for c in demo.ctx.manual_chunks]
    assert any("Troubleshooting" in r for r in refs), refs
    assert any("Cartridge" in r for r in refs), refs


def test_sop_section_level_chunk(demo: Assembled) -> None:
    """Post-Task-0: SOPs yield section-level chunks (section_ref != bare title)."""
    assert demo.ctx.sop_chunks, "no SOP chunks retrieved"
    refs = [c.section_ref for c in demo.ctx.sop_chunks]
    assert any(r and not r.upper().startswith("SOP-") for r in refs), refs


def test_report_chunk_from_sister_mentions_flush(demo: Assembled) -> None:
    hits = [c for c in demo.ctx.report_chunks if "flush" in (c.content or "").lower()]
    assert hits, "no report chunk mentioning flush"


def test_pool_matches_enumeration(demo: Assembled) -> None:
    assert demo.ctx.evidence_pool == enumerate_pool(demo.ctx)


def test_pool_integrity(demo: Assembled) -> None:
    assert_pool_integrity(demo.ctx)


def test_snapshot_persisted(demo: Assembled) -> None:
    with SessionLocal() as s:
        dossier = s.scalar(select(Dossier).where(Dossier.event_id == demo.event_id))
    assert dossier is not None
    assert dossier.status == "assembling"
    assert dossier.shared_context is not None
    assert dossier.shared_context["content_hash"] == demo.ctx.content_hash
