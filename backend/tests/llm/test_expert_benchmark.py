"""Domain-expert benchmark — plant-engineer phrasing, structural assertions only (M14+).

Runs against the live demo dossier (P-3401 seal leak) + contextual chat.
Failures are reported as findings; do not tune the product to pass here.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.engine import SessionLocal
from app.db.models import Dossier, EvidenceLink, OperationalEvent, ReasoningRun
from app.main import create_app

pytestmark = [pytest.mark.slow, pytest.mark.llm]

DEMO_EVENT = {
    "asset_tag": "P-3401",
    "source": "simulated",
    "symptom_category": "seal_leak",
    "note": (
        "Drips increasing at mechanical seal area, noticed on operator rounds. "
        "Product traces on baseplate."
    ),
    "criticality": "A",
}


@dataclass(frozen=True)
class ExpertCase:
    id: str
    question: str
    expect_refused: bool
    min_citations: int = 0
    pool_ids: tuple[str, ...] = ()
    answer_must_contain_any: tuple[str, ...] = ()
    surface: Literal["chat", "dossier"] = "chat"


CASES: tuple[ExpertCase, ...] = (
    ExpertCase(
        id="flush_plan_oem",
        question="What flush plan does the OEM specify for this pump?",
        expect_refused=False,
        min_citations=1,
    ),
    ExpertCase(
        id="sop_isolation_section",
        question=(
            "For cartridge mechanical seal replacement on this CP200 pump, "
            "which SOP covers isolation and what is the procedure number?"
        ),
        expect_refused=False,
        min_citations=1,
        answer_must_contain_any=("SOP-001", "sop-001"),
    ),
    ExpertCase(
        id="sister_seal_failures",
        question="Which sister assets on this duty have had the same mechanical seal failure mode?",
        expect_refused=False,
        min_citations=1,
        answer_must_contain_any=("P-3105", "P-3402", "3105", "3402"),
    ),
    ExpertCase(
        id="acute_pattern_downtime",
        question="What is the cumulative downtime hours for the mechanical seal leakage pattern on the sister pumps?",
        expect_refused=False,
        min_citations=0,
        surface="dossier",
        answer_must_contain_any=("41", "41.0"),
    ),
    ExpertCase(
        id="chronic_pattern_downtime",
        question="How much total downtime is recorded for flush-line blockage on this pump class?",
        expect_refused=False,
        min_citations=0,
        surface="dossier",
        answer_must_contain_any=("99", "99.1"),
    ),
    ExpertCase(
        id="motor_insulation_refusal",
        question="What is the winding insulation class of motor M-1101?",
        expect_refused=True,
    ),
    ExpertCase(
        id="ocr_sop_flush_reassembly",
        question=(
            "On reassembly after seal work, what does SOP-001 require regarding "
            "the seal flush plan — cite the procedure."
        ),
        expect_refused=False,
        min_citations=1,
        answer_must_contain_any=("Plan 11", "plan 11", "flush"),
    ),
    ExpertCase(
        id="seal_cartridge_manual_section",
        question="Which OEM manual section should we follow for cartridge seal replacement?",
        expect_refused=False,
        min_citations=1,
        answer_must_contain_any=("5.3", "cartridge", "Cartridge", "seal"),
    ),
    ExpertCase(
        id="unanswerable_tank_capacity",
        question="What is the rated storage capacity in cubic metres of tank TK-9900?",
        expect_refused=True,
    ),
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    if not os.environ.get("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY not set")
    os.environ["REASONING_ENABLED"] = "true"
    os.environ["DEMO_FALLBACK"] = "false"
    from app.config import get_settings

    get_settings.cache_clear()
    return TestClient(create_app())


@pytest.fixture(scope="module")
def flow(client: TestClient) -> Iterator[dict[str, Any]]:
    resp = client.post("/api/events", json=DEMO_EVENT)
    assert resp.status_code == 201
    event_id = resp.json()["id"]
    dresp = client.post(f"/api/events/{event_id}/dossier")
    assert dresp.status_code == 201
    dossier_id = dresp.json()["dossier_id"]
    stream = client.get(f"/api/dossiers/{dossier_id}/stream")
    assert stream.status_code == 200
    body = client.get(f"/api/dossiers/{dossier_id}").json()
    assert body["status"] == "complete"
    pool = set(body["context"]["evidence_pool"])
    yield {"event_id": event_id, "dossier_id": dossier_id, "pool": pool, "body": body}
    with SessionLocal() as s:
        s.execute(delete(ReasoningRun).where(ReasoningRun.dossier_id == dossier_id))
        s.execute(delete(EvidenceLink).where(EvidenceLink.dossier_id == dossier_id))
        s.execute(delete(Dossier).where(Dossier.id == dossier_id))
        s.execute(delete(OperationalEvent).where(OperationalEvent.id == event_id))
        s.commit()


def _pattern_text(body: dict[str, Any], mode_substr: str) -> str:
    stats = body.get("context", {}).get("pattern_stats") or []
    parts: list[str] = []
    for row in stats:
        code = str(row.get("failure_mode") or row.get("failure_mode_code") or "")
        if mode_substr in code:
            parts.append(str(row))
    return " ".join(parts)


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_expert_benchmark_case(client: TestClient, flow: dict[str, Any], case: ExpertCase) -> None:
    pool: set[str] = flow["pool"]
    dossier_id = flow["dossier_id"]

    if case.surface == "dossier":
        text = _pattern_text(flow["body"], "mechanical_seal" if "acute" in case.id else "flush")
        if case.expect_refused:
            pytest.fail(f"{case.id}: dossier surface should not be refused")
        if case.answer_must_contain_any:
            assert any(tok.lower() in text.lower() for tok in case.answer_must_contain_any), (
                f"{case.id}: pattern row missing expected tokens in {text!r}"
            )
        return

    resp = client.post(
        f"/api/dossiers/{dossier_id}/chat",
        json={"question": case.question, "history": []},
    )
    assert resp.status_code == 200, case.id
    data = resp.json()
    assert data["refused"] is case.expect_refused, f"{case.id}: refusal mismatch"
    citations = data.get("citations") or []
    answer = (data.get("answer") or "").lower()

    if case.expect_refused:
        assert citations == [], f"{case.id}: refused chat must not cite"
        return

    assert len(citations) >= case.min_citations, f"{case.id}: expected citations"
    for cid in citations:
        assert cid in pool, f"{case.id}: citation {cid} not in evidence pool"
    if case.pool_ids:
        assert any(cid in citations for cid in case.pool_ids), case.id
    if case.answer_must_contain_any:
        assert any(tok.lower() in answer for tok in case.answer_must_contain_any), (
            f"{case.id}: answer missing expected tokens: {data.get('answer')!r}"
        )
