"""Routine-closure guard — deterministic pre-embedding patterns (D-024)."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

_PATTERNS_PATH = Path(__file__).with_name("routine_closure_patterns.yaml")


@lru_cache(maxsize=1)
def load_routine_patterns() -> list[tuple[str, re.Pattern[str], str]]:
    """Return (id, compiled regex, note) tuples from the curated YAML."""
    with open(_PATTERNS_PATH) as fh:
        data = yaml.safe_load(fh)
    out: list[tuple[str, re.Pattern[str], str]] = []
    for row in data.get("patterns", []):
        out.append(
            (
                str(row["id"]),
                re.compile(str(row["regex"]), re.IGNORECASE),
                str(row.get("note", "")),
            )
        )
    return out


def match_routine_closure(text: str) -> str | None:
    """Return the matching pattern id, or None if this WO should normalize."""
    for pattern_id, regex, _note in load_routine_patterns():
        if regex.search(text):
            return pattern_id
    return None
