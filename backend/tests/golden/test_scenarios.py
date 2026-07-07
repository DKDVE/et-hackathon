"""12 golden scenarios (PRD §17): universal invariants across varied assets and
symptoms, plus the Tier-3 thin-asset and `other`-symptom fallback edge cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.domain.symptom_map import symptom_modes

from .conftest import Assembled, AssembleFn, assert_pool_integrity

pytestmark = pytest.mark.slow

_SCENARIOS = yaml.safe_load((Path(__file__).parent / "scenarios.yaml").read_text())
_IDS = [s["id"] for s in _SCENARIOS]

_BUCKET_TYPES = {
    "manual_chunks": {"oem_manual"},
    "sop_chunks": {"sop"},
    "report_chunks": {"inspection_report", "incident_report"},
}


@pytest.fixture(scope="module", params=_SCENARIOS, ids=_IDS)
def scenario(request: pytest.FixtureRequest, assemble: AssembleFn) -> tuple[dict, Assembled]:
    spec = request.param
    return spec, assemble(spec["asset"], spec["symptom"], spec.get("note"))


def test_builds_and_hash_present(scenario: tuple[dict, Assembled]) -> None:
    _, a = scenario
    assert a.ctx.content_hash
    assert a.ctx.asset_profile.tag == a.ctx.event.asset_tag


def test_buckets_are_correctly_typed(scenario: tuple[dict, Assembled]) -> None:
    _, a = scenario
    for field, allowed in _BUCKET_TYPES.items():
        for c in getattr(a.ctx, field):
            assert c.doc_type in allowed, (field, c.doc_type)


def test_pool_matches_and_resolves(scenario: tuple[dict, Assembled]) -> None:
    _, a = scenario
    assert_pool_integrity(a.ctx)


def test_deterministic(scenario: tuple[dict, Assembled]) -> None:
    from app.context.assembler import build_shared_context

    _, a = scenario
    again = build_shared_context(a.event_id)
    assert again.content_hash == a.ctx.content_hash


def test_scenario_specific_expectations(scenario: tuple[dict, Assembled]) -> None:
    spec, a = scenario
    expect = spec.get("expect") or {}
    if "min_sisters" in expect:
        assert len(a.ctx.sister_incidents) >= expect["min_sisters"]
    if expect.get("no_mode_filter"):
        # `other` → None (no mode filter) → sister filter unrestricted (D-005).
        assert symptom_modes(spec["symptom"]) is None
    if expect.get("thin"):
        # Thin asset: no crash, valid context, and a modest evidence pool.
        assert isinstance(a.ctx.evidence_pool, set)
        assert len(a.ctx.evidence_pool) == len(
            {c.citation_id for c in a.ctx.manual_chunks}
            | {c.citation_id for c in a.ctx.sop_chunks}
            | {c.citation_id for c in a.ctx.report_chunks}
            | {w.citation_id for w in a.ctx.failure_history}
            | {s.citation_id for s in a.ctx.sister_incidents}
        )
