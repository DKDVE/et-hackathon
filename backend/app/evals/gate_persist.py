"""Gate result persistence — called from demo_gate.sh when GATE_PERSIST=1 (M11)."""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import UTC, datetime

from app.db.engine import SessionLocal
from app.db.models import EvalSuite
from app.evals.persist import persist_eval_run
from app.evals.runner import (
    git_ref,
    run_groundedness,
    run_normalization,
    run_prose_id,
    run_timing,
)


def _timing_warn_from_output(text: str) -> bool:
    return "TIMING_WARN:" in text


def _parse_timing(text: str) -> tuple[float, float, int | None, int]:
    wall_m = re.search(r"wall=([\d.]+)s", text)
    analysis_m = re.search(r"analysis_at=([\d.]+)s", text)
    dossier_m = re.search(r"dossier=(\d+)", text)
    attempts_m = re.search(r"attempts_used=(\d+)", text)
    wall = float(wall_m.group(1)) if wall_m else 0.0
    analysis = float(analysis_m.group(1)) if analysis_m else 0.0
    dossier_id = int(dossier_m.group(1)) if dossier_m else None
    attempts = int(attempts_m.group(1)) if attempts_m else 1
    return wall, analysis, dossier_id, attempts


def persist_gate(
    *,
    timing_output: str,
    dossier_id: int | None = None,
) -> None:
    ref = git_ref()
    wall, analysis, parsed_dossier, attempts = _parse_timing(timing_output)
    dossier_id = dossier_id or parsed_dossier
    timing_warn = _timing_warn_from_output(timing_output)

    with SessionLocal() as session:
        started = datetime.now(UTC)
        status, metrics, _ = run_timing(
            wall_s=wall,
            analysis_s=analysis,
            attempts=attempts,
            dossier_id=dossier_id,
            timing_warn=timing_warn,
        )
        persist_eval_run(
            session,
            suite=EvalSuite.timing,
            started_at=started,
            status=status,
            metrics=metrics,
            git_ref=ref,
        )
        print(f"timing: {status.value} — {metrics}")

        started = datetime.now(UTC)
        status, metrics, detail = run_normalization()
        persist_eval_run(
            session,
            suite=EvalSuite.normalization,
            started_at=started,
            status=status,
            metrics=metrics,
            git_ref=ref,
            detail=detail,
        )
        print(f"normalization: {status.value} — {metrics}")

        if dossier_id is not None:
            for suite, fn in (
                (EvalSuite.groundedness, lambda: run_groundedness(dossier_id)),
                (EvalSuite.prose_id, lambda: run_prose_id(dossier_id)),
            ):
                started = datetime.now(UTC)
                status, metrics, detail = fn()
                persist_eval_run(
                    session,
                    suite=suite,
                    started_at=started,
                    status=status,
                    metrics=metrics,
                    git_ref=ref,
                    detail=detail,
                )
                print(f"{suite.value}: {status.value} — {metrics}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Persist demo-gate eval rows")
    parser.add_argument("--timing-output", default=None, help="stdout from demo_gate_timing.py")
    parser.add_argument("--dossier-id", type=int, default=None)
    args = parser.parse_args(argv)
    timing_output = args.timing_output
    if timing_output is None:
        timing_output = sys.stdin.read()
    if os.environ.get("GATE_PERSIST", "1").strip().lower() in ("0", "false", "no"):
        print("GATE_PERSIST=0 — skipping eval persistence")
        return 0
    persist_gate(timing_output=timing_output, dossier_id=args.dossier_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
