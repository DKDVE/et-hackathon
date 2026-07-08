"""Unit tests for trace cost estimation."""

from datetime import UTC, datetime

from app.api.trace_cost import estimate_cost_usd
from app.db.models import ReasoningRun


def _run(model: str, prompt: int, completion: int) -> ReasoningRun:
    return ReasoningRun(
        dossier_id=1,
        node="analysis",
        model=model,
        prompt_version="v1",
        started_at=datetime(2026, 7, 8, 12, 0, tzinfo=UTC),
        latency_ms=1,
        prompt_tokens=prompt,
        completion_tokens=completion,
        status="ok",
        output_digest="x",
    )


def test_estimate_cost_usd() -> None:
    rates = {
        "anthropic/claude-sonnet-4.6": {"prompt": 3.0, "completion": 15.0},
        "anthropic/claude-haiku-4.5": {"prompt": 0.8, "completion": 4.0},
    }
    runs = [_run("anthropic/claude-sonnet-4.6", 1_000_000, 0)]
    assert estimate_cost_usd(runs, rates) == 3.0
