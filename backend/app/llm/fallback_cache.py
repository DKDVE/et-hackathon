"""Fallback SSE cache for demo resilience (P9)."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ReasoningFallbackCache
from app.domain.models import SharedContext
from app.reasoning.prompts import analysis, recommendation, validation


def prompt_versions() -> dict[str, str]:
    return {
        "analysis": analysis.PROMPT_VERSION,
        "recommendation": recommendation.PROMPT_VERSION,
        "validation": validation.PROMPT_VERSION,
    }


def event_fingerprint(ctx: SharedContext) -> str:
    ev = ctx.event
    note = (ev.note or "").strip()
    return f"{ev.asset_tag}|{ev.symptom_category}|{note}"


def cache_key(ctx: SharedContext) -> str:
    payload = json.dumps(
        {
            "event": event_fingerprint(ctx),
            "content_hash": ctx.content_hash,
            "prompt_versions": prompt_versions(),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def store_sequence(session: Session, ctx: SharedContext, events: list[dict[str, Any]]) -> None:
    key = cache_key(ctx)
    existing = session.scalar(
        select(ReasoningFallbackCache).where(ReasoningFallbackCache.cache_key == key)
    )
    if existing is not None:
        existing.events = events
        session.commit()
        return
    row = ReasoningFallbackCache(
        cache_key=key,
        event_fingerprint=event_fingerprint(ctx),
        content_hash=ctx.content_hash,
        prompt_versions=prompt_versions(),
        events=events,
    )
    session.add(row)
    session.commit()


def load_sequence(session: Session, ctx: SharedContext) -> list[dict[str, Any]] | None:
    key = cache_key(ctx)
    row = session.scalar(
        select(ReasoningFallbackCache).where(ReasoningFallbackCache.cache_key == key)
    )
    if row is None:
        return None
    return list(row.events)


async def replay_with_pacing(
    events: list[dict[str, Any]],
    *,
    cached: bool = True,
) -> list[dict[str, str]]:
    """Replay cached SSE frames with realistic pacing; flag payloads cached."""
    out: list[dict[str, str]] = []
    for frame in events:
        name = frame["event"]
        data = frame.get("data", {})
        if cached and isinstance(data, dict) and name != "context_ready":
            data = {**data, "cached": True}
        out.append({"event": name, "data": json.dumps(data)})
        await asyncio.sleep(0.4)
    return out
