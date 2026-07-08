"""Effective failure mode helper tests (M12 / D-023)."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from app.db.engine import SessionLocal
from app.db.models import FailureMode, HumanVerdict, WorkOrder
from app.memory.effective_mode import effective_failure_mode_id, effective_failure_mode_id_for_wo


@pytest.fixture
def seal_mode_id() -> int:
    with SessionLocal() as session:
        mid = session.scalar(
            select(FailureMode.id).where(FailureMode.code == "mechanical_seal_leakage")
        )
        assert mid is not None
        return mid


def test_effective_mode_auto_only(seal_mode_id: int) -> None:
    wo = WorkOrder(
        id=-1,
        wo_number="TEST",
        asset_id=1,
        opened_on=datetime(2024, 1, 1).date(),
        raw_description="x",
        failure_mode_id=seal_mode_id,
        normalization_score=0.9,
        human_verdict=None,
        human_failure_mode_id=None,
    )
    assert effective_failure_mode_id_for_wo(wo) == seal_mode_id


def test_effective_mode_confirmed_uses_human_id(seal_mode_id: int) -> None:
    wo = WorkOrder(
        id=-1,
        wo_number="TEST",
        asset_id=1,
        opened_on=datetime(2024, 1, 1).date(),
        raw_description="x",
        failure_mode_id=seal_mode_id,
        normalization_score=0.9,
        human_verdict=HumanVerdict.confirmed,
        human_failure_mode_id=seal_mode_id,
    )
    assert effective_failure_mode_id_for_wo(wo) == seal_mode_id


def test_effective_mode_corrected_overrides(seal_mode_id: int) -> None:
    with SessionLocal() as session:
        other = session.scalar(
            select(FailureMode.id).where(FailureMode.code == "bearing_wear")
        )
        assert other is not None
    wo = WorkOrder(
        id=-1,
        wo_number="TEST",
        asset_id=1,
        opened_on=datetime(2024, 1, 1).date(),
        raw_description="x",
        failure_mode_id=seal_mode_id,
        normalization_score=0.9,
        human_verdict=HumanVerdict.corrected,
        human_failure_mode_id=other,
    )
    assert effective_failure_mode_id_for_wo(wo) == other


def test_effective_mode_unclassifiable_nulls_despite_auto(seal_mode_id: int) -> None:
    wo = WorkOrder(
        id=-1,
        wo_number="TEST",
        asset_id=1,
        opened_on=datetime(2024, 1, 1).date(),
        raw_description="x",
        failure_mode_id=seal_mode_id,
        normalization_score=0.9,
        human_verdict=HumanVerdict.unclassifiable,
        human_failure_mode_id=None,
    )
    assert effective_failure_mode_id_for_wo(wo) is None


def test_effective_mode_sql_expression_compiles() -> None:
    expr = effective_failure_mode_id()
    assert expr is not None
