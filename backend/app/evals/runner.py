"""Eval suite runner — one entrypoint for gate/audits (M11)."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import UTC, datetime
from typing import Any

from app.db.engine import SessionLocal
from app.db.models import EvalStatus, EvalSuite
from app.evals.persist import persist_eval_run
from tests.audits.groundedness_audit import audit_dossier
from tests.audits.normalization_audit import run_audit
from tests.audits.prose_id_audit import audit_prose_ids


def git_ref() -> str:
    import os

    env_ref = os.environ.get("GIT_REF", "").strip()
    if env_ref:
        return env_ref
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip() or "unknown"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def run_golden() -> tuple[EvalStatus, dict[str, Any], dict[str, Any] | None]:
    started = datetime.now(UTC)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-m",
            "slow",
            "tests/golden",
            "tests/test_assembler_determinism.py",
            "tests/test_lexical_channel.py",
        ],
        capture_output=True,
        text=True,
        cwd=".",
    )
    output = proc.stdout + proc.stderr
    passed = failed = 0
    m = re.search(r"(\d+) passed", output)
    if m:
        passed = int(m.group(1))
    m = re.search(r"(\d+) failed", output)
    if m:
        failed = int(m.group(1))
    status = EvalStatus.FAIL if proc.returncode != 0 else EvalStatus.PASS
    metrics = {"passed": passed, "failed": failed}
    detail = {"output_tail": output.strip()[-2000:]} if proc.returncode != 0 else None
    _ = started
    return status, metrics, detail


def run_normalization() -> tuple[EvalStatus, dict[str, Any], dict[str, Any] | None]:
    with SessionLocal() as session:
        ok, lines = run_audit(session)
    accuracy = 0.0
    unclassified_rate = 0.0
    cross_family_errors = 0
    for line in lines:
        if line.startswith("overall accuracy"):
            m = re.search(r"([\d.]+)", line)
            if m:
                accuracy = float(m.group(1))
        if line.startswith("unclassified rate"):
            m = re.search(r"([\d.]+)%", line)
            if m:
                unclassified_rate = float(m.group(1)) / 100.0
        if "cross-family" in line and "within-family" in line:
            m = re.search(r"(\d+) cross-family", line)
            if m:
                cross_family_errors = int(m.group(1))
    metrics = {
        "accuracy": accuracy,
        "unclassified_rate": unclassified_rate,
        "cross_family_errors": cross_family_errors,
    }
    status = EvalStatus.PASS if ok else EvalStatus.FAIL
    detail = {"lines": lines} if not ok else None
    return status, metrics, detail


def run_groundedness(dossier_id: int) -> tuple[EvalStatus, dict[str, Any], dict[str, Any] | None]:
    ok, issues = audit_dossier(dossier_id)
    metrics = {"dossier_id": dossier_id, "violations": len(issues)}
    detail = {"issues": issues} if issues else None
    return EvalStatus.PASS if ok else EvalStatus.FAIL, metrics, detail


def run_prose_id(dossier_id: int) -> tuple[EvalStatus, dict[str, Any], dict[str, Any] | None]:
    ok, issues = audit_prose_ids(dossier_id)
    metrics = {"dossier_id": dossier_id, "violations": len(issues)}
    detail = {"issues": issues} if issues else None
    return EvalStatus.PASS if ok else EvalStatus.FAIL, metrics, detail


def run_timing(
    *,
    wall_s: float,
    analysis_s: float,
    attempts: int,
    dossier_id: int | None = None,
    timing_warn: bool = False,
) -> tuple[EvalStatus, dict[str, Any], dict[str, Any] | None]:
    metrics: dict[str, Any] = {
        "wall_s": round(wall_s, 2),
        "t_analysis_s": round(analysis_s, 2),
        "attempts": attempts,
    }
    if dossier_id is not None:
        metrics["dossier_id"] = dossier_id
    status = EvalStatus.WARN if timing_warn else EvalStatus.PASS
    return status, metrics, None


def run_all_suites(dossier_id: int | None = None) -> list[int]:
    """Run every suite and persist one eval_runs row each. Returns row ids."""
    ref = git_ref()
    ids: list[int] = []
    with SessionLocal() as session:
        for suite_name, runner in (
            ("golden", lambda: run_golden()),
            ("normalization", lambda: run_normalization()),
        ):
            started = datetime.now(UTC)
            status, metrics, detail = runner()
            row = persist_eval_run(
                session,
                suite=EvalSuite(suite_name),
                started_at=started,
                status=status,
                metrics=metrics,
                git_ref=ref,
                detail=detail,
            )
            ids.append(row.id)
            print(f"{suite_name}: {status.value} — {metrics}")

        if dossier_id is not None:
            for suite_name, runner in (
                ("groundedness", lambda: run_groundedness(dossier_id)),
                ("prose_id", lambda: run_prose_id(dossier_id)),
            ):
                started = datetime.now(UTC)
                status, metrics, detail = runner()
                row = persist_eval_run(
                    session,
                    suite=EvalSuite(suite_name),
                    started_at=started,
                    status=status,
                    metrics=metrics,
                    git_ref=ref,
                    detail=detail,
                )
                ids.append(row.id)
                print(f"{suite_name}: {status.value} — {metrics}")
    return ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run eval suites and persist eval_runs")
    parser.add_argument("--dossier-id", type=int, default=None, help="For groundedness/prose_id")
    args = parser.parse_args(argv)
    run_all_suites(args.dossier_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
