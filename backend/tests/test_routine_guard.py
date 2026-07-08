"""Routine-closure guard pattern tests (D-024)."""

from __future__ import annotations

import csv
from pathlib import Path

from app.domain.routine_guard import load_routine_patterns, match_routine_closure

_TRUTH = Path(__file__).resolve().parents[2] / "dataset" / "rendered" / "work_orders_truth.csv"


def test_routine_patterns_load() -> None:
    patterns = load_routine_patterns()
    assert 10 <= len(patterns) <= 15


def test_catches_designed_routine_phrases() -> None:
    assert match_routine_closure("routine pm done, greased, checked, all ok")
    assert match_routine_closure("topped up oil, wiped down, running fine")
    assert match_routine_closure("checked pump running normal no issue closed wo")
    assert match_routine_closure(
        "Scheduled PM: lubrication, general check. No abnormality found."
    )


def test_does_not_flag_real_failure_on_routine_survey() -> None:
    text = (
        "Drive-end bearing exhibiting elevated noise and vibration on routine survey; "
        "wear suspected, replacement planned."
    )
    assert match_routine_closure(text) is None


def test_guard_recall_on_truth_unclassified() -> None:
    """Designed-routine rows in truth should match the guard (informational baseline)."""
    wo_csv = _TRUTH.parent / "work_orders.csv"
    if not _TRUTH.is_file() or not wo_csv.is_file():
        return
    with open(_TRUTH, newline="") as fh:
        truth = {r["wo_number"]: r["true_failure_mode"] for r in csv.DictReader(fh)}
    with open(wo_csv, newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if truth.get(r["wo_number"]) == "unclassified"]
    assert rows
    hits = sum(1 for r in rows if match_routine_closure(r["raw_description"]))
    assert hits / len(rows) >= 0.85
