"""Eval runner persistence tests (M11)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import delete

from app.db.engine import SessionLocal
from app.db.models import EvalRun, EvalStatus, EvalSuite
from app.evals.persist import persist_eval_run
from app.evals.runner import run_timing


@pytest.fixture(autouse=True)
def _clean_eval_runs() -> None:
    with SessionLocal() as session:
        session.execute(delete(EvalRun))
        session.commit()
    yield
    with SessionLocal() as session:
        session.execute(delete(EvalRun))
        session.commit()


def test_persist_timing_suite() -> None:
    started = datetime.now(UTC)
    status, metrics, _ = run_timing(wall_s=42.0, analysis_s=38.5, attempts=1, dossier_id=7)
    assert status == EvalStatus.PASS
    with SessionLocal() as session:
        row = persist_eval_run(
            session,
            suite=EvalSuite.timing,
            started_at=started,
            status=status,
            metrics=metrics,
            git_ref="abc1234",
        )
        assert row.metrics["t_analysis_s"] == 38.5
        assert row.metrics["attempts"] == 1


def test_timing_warn_status() -> None:
    status, metrics, _ = run_timing(
        wall_s=65.0, analysis_s=40.0, attempts=2, timing_warn=True
    )
    assert status == EvalStatus.WARN
    assert metrics["attempts"] == 2


def test_run_all_suites_stubbed(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.evals import runner

    monkeypatch.setattr(runner, "run_golden", lambda: (EvalStatus.PASS, {"passed": 3, "failed": 0}, None))
    monkeypatch.setattr(
        runner,
        "run_normalization",
        lambda: (EvalStatus.PASS, {"accuracy": 0.95, "unclassified_rate": 0.1, "cross_family_errors": 0}, None),
    )
    ids = runner.run_all_suites(dossier_id=None)
    assert len(ids) == 2
    with SessionLocal() as session:
        rows = session.scalars(
            __import__("sqlalchemy").select(EvalRun).order_by(EvalRun.id)
        ).all()
        assert len(rows) == 2
        assert {r.suite for r in rows} == {EvalSuite.golden, EvalSuite.normalization}
