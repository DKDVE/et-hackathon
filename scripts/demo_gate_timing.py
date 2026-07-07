#!/usr/bin/env python3
"""Timed demo-event dossier for ``make demo-gate`` (M9).

Creates a fresh P-3401 seal-leak event, runs full reasoning via SSE, asserts
wall < 60s and time-to-first-analysis < 30s, then tears down the scratch row.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

DEMO_EVENT = {
    "asset_tag": "P-3401",
    "source": "simulated",
    "symptom_category": "seal_leak",
    "note": (
        "Drips increasing at mechanical seal area, noticed on operator rounds. "
        "Product traces on baseplate."
    ),
    "criticality": "A",
}

BASE = os.environ.get("DEMO_GATE_API_URL", "http://localhost:8000")


def _post(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def _get(path: str) -> str:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=120) as resp:
        return resp.read().decode()


def _delete_event(event_id: int) -> None:
    from sqlalchemy import delete, select

    from app.db.engine import SessionLocal
    from app.db.models import Dossier, EvidenceLink, OperationalEvent, ReasoningRun

    with SessionLocal() as s:
        dossier = s.scalar(select(Dossier).where(Dossier.event_id == event_id))
        if dossier is not None:
            s.execute(delete(ReasoningRun).where(ReasoningRun.dossier_id == dossier.id))
            s.execute(delete(EvidenceLink).where(EvidenceLink.dossier_id == dossier.id))
            s.execute(delete(Dossier).where(Dossier.id == dossier.id))
        s.execute(delete(OperationalEvent).where(OperationalEvent.id == event_id))
        s.commit()


def _parse_sse(text: str) -> list[str]:
    names: list[str] = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        for line in block.splitlines():
            if line.startswith("event:"):
                names.append(line[len("event:") :].strip())
    return names


def main() -> int:
    if os.environ.get("REASONING_ENABLED", "").lower() not in ("true", "1"):
        print("REASONING_ENABLED must be true for timed demo run", file=sys.stderr)
        return 1
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY not set", file=sys.stderr)
        return 1

    event_id: int | None = None
    t0 = time.monotonic()
    try:
        event = _post("/api/events", DEMO_EVENT)
        event_id = event["id"]
        dossier = _post(f"/api/events/{event_id}/dossier")
        dossier_id = dossier["dossier_id"]

        stream_text = _get(f"/api/dossiers/{dossier_id}/stream")
        names = _parse_sse(stream_text)
        t_analysis: float | None = None
        for name in names:
            if name == "analysis":
                t_analysis = time.monotonic() - t0
                break
        wall = time.monotonic() - t0

        if "report_complete" not in names and "degraded" not in names:
            print(f"unexpected SSE sequence: {names}", file=sys.stderr)
            return 1
        if t_analysis is None:
            print(f"no analysis event in SSE sequence: {names}", file=sys.stderr)
            return 1
        if wall >= 60.0:
            print(f"wall time {wall:.1f}s >= 60s", file=sys.stderr)
            return 1
        if t_analysis >= 30.0:
            print(f"time-to-analysis {t_analysis:.1f}s >= 30s", file=sys.stderr)
            return 1

        print(f"wall={wall:.1f}s analysis_at={t_analysis:.1f}s dossier={dossier_id}")
        # ponytail: keep dossier for demo-gate audits (verify-seed already ran)
        event_id = None
        return 0
    except urllib.error.URLError as exc:
        print(f"API unreachable at {BASE}: {exc}", file=sys.stderr)
        return 1
    finally:
        if event_id is not None:
            try:
                _delete_event(event_id)
            except Exception as exc:  # noqa: BLE001 — best-effort teardown
                print(f"teardown warning: {exc}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
