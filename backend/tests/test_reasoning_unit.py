"""Unit tests for reasoning validation, report, and fallback (no LLM)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.models import AssetProfile, EventInfo, SharedContext, SisterIncident, WorkOrderRecord
from app.reasoning.graph import reasoning_sse_events
from app.reasoning.nodes.report import attach_strength, compute_guardrail_stats, persist_validated
from app.reasoning.nodes.validation_stage1 import run_validation_stage1
from app.reasoning.prompts.context_render import render_recommendation_context, render_shared_context
from app.reasoning.schemas import (
    AnalysisOutput,
    ProbableCause,
    RecommendationOutput,
    RecommendedAction,
    SafetyNote,
    ValidatedCause,
    ValidatedDossier,
    ValidatedSafetyNote,
)
from app.reasoning.state import DossierState


def _minimal_ctx(pool: set[str]) -> SharedContext:
    return SharedContext(
        event=EventInfo(
            event_id=1,
            asset_tag="P-3401",
            source="simulated",
            symptom_category="seal_leak",
            note="test",
            criticality="A",
            status="open",
            occurred_at=datetime(2026, 3, 1, tzinfo=UTC),
        ),
        asset_profile=AssetProfile(
            asset_id=1,
            tag="P-3401",
            name="Pump",
            asset_class="CP200",
            manufacturer="X",
            model="Y",
            plant="P1",
            unit="U1",
            area="A1",
            service_duty="transfer",
            criticality="A",
            installed_on=None,
        ),
        failure_history=[],
        sister_incidents=[],
        manual_chunks=[],
        sop_chunks=[],
        report_chunks=[],
        pattern_stats=[],
        evidence_pool=pool,
        assembled_at=datetime(2026, 3, 1, tzinfo=UTC),
        content_hash="abc",
    )


def test_stage1_strips_fabricated_citation() -> None:
    pool = {"WO-2024-0117", "CH-1"}
    ctx = _minimal_ctx(pool)
    state = DossierState(
        dossier_id=1,
        shared_context=ctx,
        analysis=AnalysisOutput(
            probable_causes=[
                ProbableCause(
                    statement="Seal failure",
                    mechanism_explanation="Wear",
                    evidence_ids=["WO-2024-0117", "WO-FAKE-999"],
                )
            ]
        ),
        recommendation=RecommendationOutput(
            safety_notes=[SafetyNote(text="LOTO", evidence_ids=["CH-1", "CH-BOGUS"])],
            actions=[
                RecommendedAction(
                    text="Inspect seal",
                    rationale="Check weep",
                    evidence_ids=["WO-FAKE-999"],
                )
            ],
        ),
    )
    run_validation_stage1(state)
    assert state.provisional_causes[0].evidence_ids == ["WO-2024-0117"]
    assert state.provisional_causes[0].grounding == "evidenced"
    assert state.provisional_notes[0].evidence_ids == ["CH-1"]
    assert state.provisional_actions[0].grounding == "hypothesis"
    assert state.stripped_id_counts["stage1"] == 3


def test_safety_hypothesis_deleted_in_sections() -> None:
    validated = ValidatedDossier(
        probable_causes=[],
        safety_notes=[
            ValidatedSafetyNote(
                text="Unverified hazard",
                evidence_ids=[],
                grounding="hypothesis",
                claim_ref="safety:0",
            ),
            ValidatedSafetyNote(
                text="LOTO per SOP",
                evidence_ids=["CH-1"],
                grounding="evidenced",
                claim_ref="safety:1",
            ),
        ],
        actions=[],
    )
    safe = [n for n in validated.safety_notes if n.grounding == "evidenced"]
    assert len(safe) == 1
    assert safe[0].text == "LOTO per SOP"


def test_guardrail_stats_from_state() -> None:
    from app.reasoning.state import DossierState

    pool = {"WO-2024-0117"}
    ctx = _minimal_ctx(pool)
    state = DossierState(
        dossier_id=1,
        shared_context=ctx,
        stripped_id_counts={"stage1": 2, "stage2": 1},
        validated=ValidatedDossier(
            probable_causes=[
                ValidatedCause(
                    statement="A",
                    mechanism_explanation="m",
                    evidence_ids=[],
                    grounding="hypothesis",
                    claim_ref="cause:0",
                )
            ],
            safety_notes=[
                ValidatedSafetyNote(
                    text="bad",
                    evidence_ids=[],
                    grounding="hypothesis",
                    claim_ref="safety:0",
                )
            ],
            actions=[],
        ),
    )
    stats = compute_guardrail_stats(state)
    assert stats["stage1_stripped_citations"] == 2
    assert stats["stage2_unsupported_removed"] == 1
    assert stats["hypothesis_claims"] == 1
    assert stats["safety_notes_deleted"] == 1
    assert stats["chat_citations_stripped"] == 0


def test_report_section_order() -> None:
    from app.reasoning.schemas import DossierSections

    sections = DossierSections(
        safety_notes=[],
        probable_causes=[
            ValidatedCause(
                statement="A",
                mechanism_explanation="m",
                evidence_ids=[],
                grounding="hypothesis",
                claim_ref="cause:0",
            )
        ],
        actions=[],
    )
    keys = list(sections.model_dump().keys())
    assert keys == ["safety_notes", "probable_causes", "actions"]


def test_strength_attachment() -> None:
    ctx = _minimal_ctx({"WO-2024-0117"})
    validated = ValidatedDossier(
        probable_causes=[
            ValidatedCause(
                statement="Seal",
                mechanism_explanation="m",
                evidence_ids=["WO-2024-0117"],
                grounding="evidenced",
                claim_ref="cause:0",
            )
        ],
        safety_notes=[],
        actions=[],
    )
    enriched = attach_strength(validated, ctx)
    assert enriched.probable_causes[0].strength_tier in ("Strong", "Moderate", "Weak")


def test_recommendation_context_omits_history_and_sisters() -> None:
    from datetime import date

    ctx = _minimal_ctx({"CH-1"}).model_copy(
        update={
            "failure_history": [
                WorkOrderRecord(
                    wo_number="WO-2024-0117",
                    asset_tag="P-3401",
                    opened_on=date(2024, 1, 1),
                    closed_on=None,
                    raw_description="Seal leak",
                    actions_taken=None,
                    downtime_hours=2.0,
                    failure_mode_code="seal_leak",
                )
            ],
            "sister_incidents": [
                SisterIncident(
                    wo_number="WO-2025-0099",
                    asset_tag="P-3402",
                    asset_name="Sister pump",
                    failure_mode_code="seal_leak",
                    opened_on=date(2025, 6, 1),
                    closed_on=None,
                    raw_description="Sister seal issue",
                    downtime_hours=1.0,
                )
            ],
        }
    )
    full = render_shared_context(ctx)
    slim = render_recommendation_context(ctx)
    assert "FAILURE HISTORY" in full
    assert "SISTER INCIDENTS" in full
    assert "FAILURE HISTORY" not in slim
    assert "SISTER INCIDENTS" not in slim
    assert "WO-2024-0117" not in slim
    assert "WO-2025-0099" not in slim


def test_output_schema_max_lengths() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AnalysisOutput(
            probable_causes=[
                ProbableCause(statement=f"c{i}", mechanism_explanation="m", evidence_ids=[])
                for i in range(5)
            ]
        )
    with pytest.raises(ValidationError):
        RecommendationOutput(
            safety_notes=[
                SafetyNote(text=f"n{i}", evidence_ids=[]) for i in range(4)
            ],
            actions=[],
        )
    with pytest.raises(ValidationError):
        RecommendationOutput(
            safety_notes=[],
            actions=[
                RecommendedAction(text=f"a{i}", rationale="r", evidence_ids=[])
                for i in range(6)
            ],
        )


def test_fallback_replay_on_node_failure(monkeypatch) -> None:
    from app.config import Settings

    ctx = _minimal_ctx({"CH-1"})
    cached_events = [
        {"event": "analysis", "data": {"probable_causes": [], "provisional": True}},
        {"event": "report_complete", "data": {"status": "complete"}},
    ]

    async def _fake_replay(*_a, **_k):
        yield "analysis", {"probable_causes": [], "provisional": True, "cached": True}
        yield "report_complete", {"status": "complete", "cached": True}

    monkeypatch.setattr("app.reasoning.graph.load_sequence", lambda _s, _c: cached_events)
    monkeypatch.setattr("app.reasoning.graph._replay_cached", _fake_replay)

    def _fake_settings() -> Settings:
        return Settings(openrouter_api_key="", demo_fallback=True, reasoning_enabled=True)

    monkeypatch.setattr("app.reasoning.graph.get_settings", _fake_settings)

    async def _collect() -> list[tuple[str, object]]:
        frames = []
        async for name, data in reasoning_sse_events(1, ctx):
            frames.append((name, data))
        return frames

    frames = asyncio.run(_collect())
    assert frames[0][0] == "analysis"
    assert frames[-1][0] == "report_complete"
    assert frames[0][1].get("cached") is True


def test_api_schema_strips_max_items() -> None:
    from app.llm.client import LLMClient
    from app.reasoning.schemas import AnalysisOutput

    raw = AnalysisOutput.model_json_schema()
    assert raw["properties"]["probable_causes"].get("maxItems") == 4
    api = LLMClient._api_schema(raw)
    assert "maxItems" not in api["properties"]["probable_causes"]


def test_post_check_strips_fabricated_citation() -> None:
    from app.reasoning.post_check import post_check_citations

    pool = {"CH-1", "WO-2024-0117"}
    citations, grounding = post_check_citations(
        ["CH-1", "WO-FAKE"], pool, refused=False
    )
    assert citations == ["CH-1"]
    assert grounding == "evidenced"

    citations2, grounding2 = post_check_citations(
        ["WO-FAKE"], pool, refused=False
    )
    assert citations2 == []
    assert grounding2 == "hypothesis"

    citations3, grounding3 = post_check_citations([], pool, refused=True)
    assert citations3 == []
    assert grounding3 is None


def test_no_httpx_outside_llm_client() -> None:
    app_root = Path(__file__).resolve().parents[1] / "app"
    offenders: list[str] = []
    for path in app_root.rglob("*.py"):
        if path.name == "client.py" and "llm" in path.parts:
            continue
        text = path.read_text()
        if "import httpx" in text or "from httpx" in text:
            offenders.append(str(path))
        if "openrouter.ai" in text:
            offenders.append(str(path))
    assert offenders == [], f"direct OpenRouter/httpx outside llm/client.py: {offenders}"
