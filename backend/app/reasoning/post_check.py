"""Deterministic citation post-check (shared by chat and unit tests)."""

from __future__ import annotations

from typing import Literal

Grounding = Literal["evidenced", "hypothesis"]


def post_check_citations(
    citations: list[str],
    pool: set[str],
    *,
    refused: bool,
) -> tuple[list[str], Grounding | None]:
    """Strip citation IDs ∉ pool. Hypothesis flag when non-refusal has zero citations."""
    valid = [cid for cid in citations if cid in pool]
    if refused:
        return valid, None
    if not valid:
        return valid, "hypothesis"
    return valid, "evidenced"
