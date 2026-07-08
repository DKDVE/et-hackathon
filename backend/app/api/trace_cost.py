"""Trace tab cost estimates (D-022)."""

from __future__ import annotations

from app.db.models import ReasoningRun

COST_FOOTNOTE = (
    "Estimated at configured per-model token rates (USD per 1M tokens); "
    "actual billing may differ."
)


def estimate_cost_usd(
    runs: list[ReasoningRun],
    rates: dict[str, dict[str, float]],
) -> float:
    total = 0.0
    for run in runs:
        rate = rates.get(run.model, {"prompt": 0.0, "completion": 0.0})
        total += (
            run.prompt_tokens * rate.get("prompt", 0.0)
            + run.completion_tokens * rate.get("completion", 0.0)
        ) / 1_000_000
    return round(total, 6)
