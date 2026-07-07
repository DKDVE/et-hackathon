#!/usr/bin/env python3
"""Act-2 demo trigger (D-007): POST a simulated Operational Event to the API.

Fires THE demo event by default (P-3401, seal_leak, the M4 golden note); the
``--scenario`` flag selects any row from the golden scenario yaml. Prints the
created event id and the board URL to open.

Stdlib-only for the default path (urllib) so it runs on a bare host without the
backend venv; ``--scenario``/``--list`` lazily import pyyaml.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

_SCENARIOS = Path(__file__).resolve().parent.parent / "backend/tests/golden/scenarios.yaml"

# THE demo event — P-3401 mechanical-seal leak, the exact M4 golden note.
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


def _load_scenarios() -> dict[str, dict]:
    import yaml  # lazy: only needed for --scenario/--list

    rows = yaml.safe_load(_SCENARIOS.read_text())
    return {r["id"]: r for r in rows}


def _scenario_event(scenario_id: str) -> dict:
    rows = _load_scenarios()
    if scenario_id not in rows:
        sys.exit(f"unknown scenario '{scenario_id}'; try --list")
    row = rows[scenario_id]
    return {
        "asset_tag": row["asset"],
        "source": "simulated",
        "symptom_category": row["symptom"],
        "note": row.get("note"),
        "criticality": "A",
    }


# Board dressing (M9): historical events on non-hero assets — varied symptoms,
# closed/reviewed, timestamps days old. Hero demo event stays open + A + newest.
BACKGROUND_EVENTS = [
    {
        "asset_tag": "P-2210",
        "symptom_category": "vibration",
        "note": "Drive-end vibration elevated after last turnaround; coupling alignment suspect.",
        "criticality": "B",
        "status": "closed",
        "days_ago": 14,
    },
    {
        "asset_tag": "A-3110",
        "symptom_category": "abnormal_noise",
        "note": "Intermittent knocking from agitator gearbox under full load.",
        "criticality": "C",
        "status": "reviewed",
        "days_ago": 6,
    },
    {
        "asset_tag": "E-1110",
        "symptom_category": "overheating",
        "note": "Condenser approach temperature drifting high; tubes may be fouling.",
        "criticality": "B",
        "status": "closed",
        "days_ago": 21,
    },
]


def _seed_background_events() -> None:
    """Insert historical board rows via the backend container (status + backdated)."""
    script = r"""
from datetime import UTC, datetime, timedelta
import json
from app.db.engine import SessionLocal
from app.db.models import EventStatus
from app.memory.repositories import assets, events

rows = json.loads(__import__("sys").stdin.read())
with SessionLocal() as s:
    created = []
    for row in rows:
        asset_id = assets.get_asset_id_by_tag(s, row["asset_tag"])
        if asset_id is None:
            raise SystemExit(f"asset {row['asset_tag']} not found")
        occurred = datetime.now(UTC) - timedelta(days=row["days_ago"])
        ev = events.create_event(
            s,
            asset_id=asset_id,
            source="simulated",
            symptom_category=row["symptom_category"],
            note=row["note"],
            criticality=row["criticality"],
            occurred_at=occurred,
            status=EventStatus(row["status"]),
        )
        created.append((ev.id, row["asset_tag"], row["status"], row["days_ago"]))
    for eid, tag, status, days in created:
        print(f"  background event {eid} — {tag} / {status} / {days}d ago")
"""
    payload = json.dumps(BACKGROUND_EVENTS)
    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "backend", "python", "-c", script],
        input=payload,
        text=True,
        capture_output=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    if proc.returncode != 0:
        sys.exit(proc.stderr.strip() or proc.stdout.strip() or "background seed failed")
    print(proc.stdout.strip())


def _post_event(api_url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{api_url}/api/events",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        sys.exit(f"API error {exc.code}: {exc.read().decode(errors='replace')}")
    except urllib.error.URLError as exc:
        sys.exit(f"could not reach API at {api_url}: {exc.reason} (is `make up` running?)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate an Operational Event (D-007).")
    parser.add_argument("--scenario", help="scenario id from the golden yaml (default: demo event)")
    parser.add_argument("--list", action="store_true", help="list available scenarios and exit")
    parser.add_argument(
        "--background",
        action="store_true",
        help="seed 3 historical events on non-hero assets (board dressing)",
    )
    parser.add_argument("--api-url", default="http://localhost:8000", help="backend base URL")
    parser.add_argument("--web-url", default="http://localhost:5173", help="frontend base URL")
    args = parser.parse_args()

    if args.list:
        for sid, row in _load_scenarios().items():
            print(f"  {sid:28s} {row['asset']:8s} {row['symptom']}")
        return

    if args.background:
        print("Seeding background events (non-hero assets, closed/reviewed, backdated)…")
        _seed_background_events()
        return

    payload = _scenario_event(args.scenario) if args.scenario else DEMO_EVENT
    event = _post_event(args.api_url, payload)

    print(f"event {event['id']} created — {event['asset_tag']} / {event['symptom_category']} "
          f"(criticality {event['criticality']}, source {event['source']})")
    print(f"board:   {args.web_url}/events")
    print(f"dossier: {args.web_url}/events/{event['id']}")


if __name__ == "__main__":
    main()
