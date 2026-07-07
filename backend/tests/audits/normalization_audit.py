"""Normalization audit — sole reader of work_orders_truth.csv (M3)."""

from __future__ import annotations

import csv
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.engine import SessionLocal
from app.db.models import FailureMode, WorkOrder
from app.llm.embeddings import get_embedder

PLANTED_WOS = ("WO-2024-0117", "WO-2025-0289", "WO-2026-0034")
PLANTED_MODE = "mechanical_seal_leakage"
MIN_ACCURACY = 0.90
UNCLASSIFIED_LO = 0.08
UNCLASSIFIED_HI = 0.18
# D-017: cross-family confusion is the failure the margin guard exists to prevent.
MAX_CROSS_FAMILY_ERRORS = 2


def _truth_file() -> Path:
    env = os.environ.get("TRUTH_CSV")
    if env:
        return Path(env)
    for base in (os.environ.get("DATASET_DIR"), "/dataset", Path(__file__).resolve().parents[3].parent / "dataset"):
        if not base:
            continue
        p = Path(base) / "rendered" / "work_orders_truth.csv"
        if p.is_file():
            return p
    return Path(__file__).resolve().parents[3].parent / "dataset/rendered/work_orders_truth.csv"


@dataclass
class AuditRow:
    wo_number: str
    true_mode: str
    predicted_code: str | None
    score: float | None
    margin: float | None
    runner_code: str | None


def _load_truth() -> dict[str, str]:
    with open(_truth_file(), newline="") as fh:
        return {r["wo_number"]: r["true_failure_mode"] for r in csv.DictReader(fh)}


def _mode_codes(session: Session) -> dict[int, str]:
    return {m.id: m.code for m in session.scalars(select(FailureMode)).all()}


def _families(session: Session) -> dict[str, str]:
    """code -> family."""
    return {m.code: m.family for m in session.scalars(select(FailureMode)).all()}


def _margins(session: Session) -> dict[str, tuple[float | None, str | None]]:
    """wo_number -> (top-minus-runner margin, runner-up mode code)."""
    modes = session.scalars(select(FailureMode).order_by(FailureMode.id)).all()
    matrix = np.asarray([m.embedding for m in modes], dtype=np.float64)
    codes = [m.code for m in modes]
    if matrix.ndim != 2 or matrix.shape[0] == 0:
        return {}
    embedder = get_embedder()
    out: dict[str, tuple[float | None, str | None]] = {}
    for wo in session.scalars(select(WorkOrder)).all():
        q = np.asarray(embedder.embed_batch([wo.raw_description])[0], dtype=np.float64)
        scores = matrix @ q
        if len(scores) < 2:
            out[wo.wo_number] = (None, None)
            continue
        order = np.argsort(scores)
        top = float(scores[order[-1]])
        runner = float(scores[order[-2]])
        out[wo.wo_number] = (top - runner, codes[int(order[-2])])
    return out


def run_audit(session: Session) -> tuple[bool, list[str]]:
    truth = _load_truth()
    codes = _mode_codes(session)
    families = _families(session)
    margins = _margins(session)
    norm_margin = get_settings().norm_margin

    def fam(code: str | None) -> str | None:
        return families.get(code) if code else None

    rows: list[AuditRow] = []
    for wo in session.scalars(select(WorkOrder)).all():
        pred = codes.get(wo.failure_mode_id) if wo.failure_mode_id else None
        m, runner = margins.get(wo.wo_number, (None, None))
        rows.append(
            AuditRow(
                wo_number=wo.wo_number,
                true_mode=truth[wo.wo_number],
                predicted_code=pred,
                score=wo.normalization_score,
                margin=m,
                runner_code=runner,
            )
        )

    classified = [r for r in rows if r.predicted_code is not None]
    unclassified = [r for r in rows if r.predicted_code is None]
    correct = [r for r in classified if r.predicted_code == r.true_mode]
    errors = [r for r in classified if r.predicted_code != r.true_mode]
    accuracy = len(correct) / len(classified) if classified else 0.0
    uncl_rate = len(unclassified) / len(rows)

    # D-017 error split. Three distinct failure kinds among misclassifications:
    #   * false_positives — a routine WO (true == "unclassified") assigned a real
    #     mode. This is an over-classification, governed by the unclassified-rate
    #     and accuracy gates — NOT a cross-family confusion.
    #   * within_family    — real -> real, same family (an expected adjacent-mode
    #     nuance under D-017).
    #   * cross_family     — real -> real, DIFFERENT family: the confusion the
    #     margin guard exists to prevent. This is the gated bucket.
    real_errors = [r for r in errors if r.true_mode != "unclassified"]
    false_positives = [r for r in errors if r.true_mode == "unclassified"]
    within_family_errors = [r for r in real_errors if fam(r.predicted_code) == fam(r.true_mode)]
    cross_family_errors = [r for r in real_errors if fam(r.predicted_code) != fam(r.true_mode)]

    # Rescued rows: classified despite a sub-margin top-vs-runner gap — only
    # possible under the same-family branch of the D-017 rule.
    rescued = [r for r in classified if r.margin is not None and r.margin < norm_margin]

    # Per-family accuracy, keyed by the TRUE mode's family.
    fam_total: Counter[str] = Counter()
    fam_correct: Counter[str] = Counter()
    for r in classified:
        f = fam(r.true_mode) or "unknown"
        fam_total[f] += 1
        if r.predicted_code == r.true_mode:
            fam_correct[f] += 1

    confusion: Counter[tuple[str, str]] = Counter()
    for r in errors:
        confusion[(r.true_mode, r.predicted_code)] += 1

    planted_ok = all(
        next(r.predicted_code for r in rows if r.wo_number == wo) == PLANTED_MODE
        for wo in PLANTED_WOS
    )

    lines = [
        f"overall accuracy (classified rows): {accuracy:.3f} ({len(correct)}/{len(classified)})",
        f"unclassified rate: {uncl_rate:.1%} ({len(unclassified)}/{len(rows)})",
        f"error split (real→real): {len(within_family_errors)} within-family, "
        f"{len(cross_family_errors)} cross-family (gate ≤ {MAX_CROSS_FAMILY_ERRORS})",
        f"false positives (true=unclassified → real mode): {len(false_positives)}",
        f"rows rescued by family rule (score≥thr, margin<{norm_margin}): {len(rescued)}",
        "per-family accuracy (by true-mode family):",
    ]
    for f in sorted(fam_total):
        acc = fam_correct[f] / fam_total[f]
        lines.append(f"  {f}: {acc:.3f} ({fam_correct[f]}/{fam_total[f]})")

    lines.append("cross-family errors (true -> predicted):")
    if cross_family_errors:
        for r in cross_family_errors:
            lines.append(
                f"  {r.wo_number}: {r.true_mode}[{fam(r.true_mode)}] -> "
                f"{r.predicted_code}[{fam(r.predicted_code)}] score={r.score:.3f}"
            )
    else:
        lines.append("  (none)")

    lines.append("top confused pairs (true -> predicted):")
    for (true_m, pred_m), n in confusion.most_common(5):
        if true_m == "unclassified":
            label = "false-positive"
        elif fam(true_m) == fam(pred_m):
            label = "same-family"
        else:
            label = "CROSS-family"
        lines.append(f"  {true_m} -> {pred_m}: {n} [{label}]")

    # Planted-trio decision diagnostics (criterion 1: no knife edges).
    lines.append("planted-WO decision margins:")
    for wo in PLANTED_WOS:
        r = next(x for x in rows if x.wo_number == wo)
        same_fam = fam(r.predicted_code) == fam(r.runner_code)
        lines.append(
            f"  {wo}: pred={r.predicted_code} score={r.score:.3f} "
            f"runner={r.runner_code}[{fam(r.runner_code)}] margin={r.margin:.3f} "
            f"{'(within-family: margin non-binding)' if same_fam else '(cross-family: margin binds)'}"
        )

    ok = (
        planted_ok
        and accuracy >= MIN_ACCURACY
        and UNCLASSIFIED_LO <= uncl_rate <= UNCLASSIFIED_HI
        and len(cross_family_errors) <= MAX_CROSS_FAMILY_ERRORS
    )

    if not planted_ok:
        lines.append("FAIL: planted WOs not all classified as mechanical_seal_leakage")
        for wo in PLANTED_WOS:
            r = next(x for x in rows if x.wo_number == wo)
            lines.append(f"  {wo}: predicted={r.predicted_code}")

    if accuracy < MIN_ACCURACY:
        lines.append(f"FAIL: accuracy {accuracy:.3f} < {MIN_ACCURACY}")
        lines.append("misclassified rows:")
        for r in errors:
            lines.append(
                f"  {r.wo_number}: true={r.true_mode} pred={r.predicted_code} score={r.score}"
            )

    if len(cross_family_errors) > MAX_CROSS_FAMILY_ERRORS:
        lines.append(
            f"FAIL: cross-family errors {len(cross_family_errors)} > {MAX_CROSS_FAMILY_ERRORS}"
        )

    if not (UNCLASSIFIED_LO <= uncl_rate <= UNCLASSIFIED_HI):
        lines.append(
            f"FAIL: unclassified rate {uncl_rate:.1%} outside [{UNCLASSIFIED_LO:.0%}, {UNCLASSIFIED_HI:.0%}]"
        )

    return ok, lines


def main() -> int:
    with SessionLocal() as session:
        ok, lines = run_audit(session)
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
