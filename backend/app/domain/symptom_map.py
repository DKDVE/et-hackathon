"""Loader for the curated symptom → failure-mode map (P2, TDD §5.3).

Pure, deterministic, cached. No LLM: the same symptom always yields the same
plausible failure modes and query-expansion terms.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_PATH = Path(__file__).with_name("symptom_map.yaml")


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    with open(_PATH) as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError("symptom_map.yaml must be a mapping")
    return data


def symptom_modes(category: str) -> list[str] | None:
    """Failure-mode codes plausible for ``category``.

    Returns ``None`` when no mode filter should be applied — i.e. for ``other``
    or any unmapped category (recall over precision, D-005). An entry with an
    empty ``modes`` list is treated the same as unmapped: no filter.
    """
    entry = _load().get(category)
    if not entry:
        return None
    modes = entry.get("modes") or []
    return list(modes) if modes else None


def expansion_terms(category: str) -> list[str]:
    """Query-expansion terms for ``category`` (empty list if unmapped)."""
    entry = _load().get(category)
    if not entry:
        return []
    return list(entry.get("terms") or [])
