"""Repositories must not query work_orders.failure_mode_id directly (M12)."""

from __future__ import annotations

import re
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1] / "app" / "memory" / "repositories"
# memory.py: taxonomy auto counts (D-023 audit on auto columns).
# review.py: reads wo.failure_mode_id on confirm only — never writes auto columns.
ALLOWED = {"memory.py", "review.py", "__init__.py"}
# Join/filter on auto column in repository queries (must use effective_failure_mode_id).
FORBIDDEN = re.compile(r"WorkOrder\.failure_mode_id")
# D-024: failure-history / pattern / review queries must exclude routine closures.
MUST_EXCLUDE_ROUTINE = {"work_orders.py", "memory.py"}


def test_repositories_use_effective_mode_not_raw_column() -> None:
    offenders: list[str] = []
    for path in REPO_DIR.glob("*.py"):
        if path.name in ALLOWED:
            continue
        if FORBIDDEN.search(path.read_text()):
            offenders.append(path.name)
    assert offenders == [], f"WorkOrder.failure_mode_id in repository queries: {offenders}"


def test_repositories_exclude_routine_disposition() -> None:
    for name in MUST_EXCLUDE_ROUTINE:
        text = (REPO_DIR / name).read_text()
        assert "WoDisposition.failure" in text or "_failure_only" in text, (
            f"{name} must filter routine closures (D-024)"
        )
