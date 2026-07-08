#!/usr/bin/env python3
"""M9.2 closeout — three fresh demo-event dossiers, zero repaired (Task 0)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

from sqlalchemy import select

from app.db.engine import SessionLocal
from app.db.models import ReasoningRun, ReasoningRunStatus

DEMO = "/scripts/demo_gate_timing.py"


def _repaired_for_dossier(dossier_id: int) -> int:
    with SessionLocal() as s:
        rows = s.scalars(
            select(ReasoningRun).where(ReasoningRun.dossier_id == dossier_id)
        ).all()
        return sum(1 for r in rows if r.status == ReasoningRunStatus.repaired)


def main() -> int:
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY required", file=sys.stderr)
        return 1
    print("run\twall_s\tanalysis_s\trepaired\tdossier")
    fails = 0
    for i in range(1, 4):
        t0 = time.monotonic()
        out = subprocess.check_output(["python", DEMO], text=True, stderr=subprocess.STDOUT)
        wall = time.monotonic() - t0
        dossier_id = None
        analysis_s = None
        for line in out.splitlines():
            if "dossier=" in line:
                for part in line.split():
                    if part.startswith("dossier="):
                        dossier_id = int(part.split("=", 1)[1])
                    if part.startswith("analysis_at="):
                        analysis_s = float(part.split("=", 1)[1].rstrip("s"))
        repaired = _repaired_for_dossier(dossier_id) if dossier_id else -1
        print(f"{i}\t{wall:.1f}\t{analysis_s or 0:.1f}\t{repaired}\t{dossier_id}")
        if repaired != 0:
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
