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
    parser.add_argument("--api-url", default="http://localhost:8000", help="backend base URL")
    parser.add_argument("--web-url", default="http://localhost:5173", help="frontend base URL")
    args = parser.parse_args()

    if args.list:
        for sid, row in _load_scenarios().items():
            print(f"  {sid:28s} {row['asset']:8s} {row['symptom']}")
        return

    payload = _scenario_event(args.scenario) if args.scenario else DEMO_EVENT
    event = _post_event(args.api_url, payload)

    print(f"event {event['id']} created — {event['asset_tag']} / {event['symptom_category']} "
          f"(criticality {event['criticality']}, source {event['source']})")
    print(f"board:   {args.web_url}/events")
    print(f"dossier: {args.web_url}/events/{event['id']}")


if __name__ == "__main__":
    main()
