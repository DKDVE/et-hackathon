"""Phased, idempotent seeder for the Meridian dataset (M2).

Phases:
  --phase structure  (default)  wipe -> load classes/failure_modes/assets/WOs ->
                                register documents -> print verification block,
                                exit non-zero if any check fails.
  --phase ingest                embed failure modes, chunk+embed documents,
                                normalize WOs, print verification block;
                                exits non-zero on failure.

The relational truth is dataset/design/meridian.yaml (P10). Work orders are
loaded from dataset/rendered/work_orders.csv (the M3 ingestion input) with the
true failure mode DELIBERATELY absent — normalization must discover it.
failure_mode_id and normalization_score are left NULL for every WO.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import date, datetime
from pathlib import Path

# --- make backend app + dataset catalogue importable, in container or on host ---
_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent / "backend"))  # host layout


def _find_generators() -> Path:
    candidates = [
        os.environ.get("DATASET_DIR"),
        "/dataset",
        str(_HERE.parent.parent / "dataset"),
    ]
    for c in candidates:
        if c and (Path(c) / "generators" / "catalogue.py").exists():
            return Path(c) / "generators"
    raise SystemExit("ERROR: could not locate dataset/generators (set DATASET_DIR).")


sys.path.insert(0, str(_find_generators()))

import catalogue  # noqa: E402

from app.db.engine import SessionLocal, engine  # noqa: E402
from app.db.models import (  # noqa: E402
    Asset,
    AssetClass,
    Criticality,
    DocType,
    Document,
    FailureMode,
    WorkOrder,
)
from app.memory.ingestion.document_ingestor import ingest_all, ocr_page_count  # noqa: E402
from app.memory.ingestion.pdf_parser import ocr_pages  # noqa: E402
from sqlalchemy import func, select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

HERO_CLASS = "CP200"
HERO_SISTER_TAGS = ("P-3401", "P-3105", "P-3402")
PLANTED_WOS = ("WO-2024-0117", "WO-2025-0289", "WO-2026-0034")
EXPECTED = {"assets": 40, "classes": 8, "failure_modes": 25, "work_orders": 500, "documents": 60}

_WIPE_ORDER = (
    "reasoning_runs",
    "reasoning_fallback_cache",
    "evidence_links",
    "dossiers", "chunks", "documents", "operational_events",
    "work_orders", "assets", "failure_modes", "asset_classes",
)


def _to_date(value: object) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def wipe(session: Session) -> None:
    session.execute(
        text(f"TRUNCATE {', '.join(_WIPE_ORDER)} RESTART IDENTITY CASCADE")
    )
    session.commit()


def load_structure(session: Session, design: dict) -> None:
    # Location display maps (plants/units are string attributes on assets — the
    # schema has no plant/unit tables, D-004/§3).
    plant_name = {p["code"]: p["name"] for p in design["plants"]}
    unit_name = {u["code"]: u["name"] for u in design["units"]}

    # asset_classes
    class_id: dict[str, int] = {}
    for c in design["asset_classes"]:
        obj = AssetClass(
            manufacturer=c["manufacturer"],
            model=c["model"],
            class_name=c["class_name"],
            description=(c.get("description") or "").strip() or None,
        )
        session.add(obj)
        session.flush()
        class_id[c["key"]] = obj.id

    # failure_modes (embedding NULL — filled in M3)
    for f in design["failure_modes"]:
        session.add(
            FailureMode(
                code=f["code"],
                name=f["name"],
                family=(f.get("family") or "general").strip(),
                description=(f.get("description") or "").strip() or None,
            )
        )

    # assets
    asset_id: dict[str, int] = {}
    for a in design["assets"]:
        obj = Asset(
            tag=a["tag"],
            name=a["name"],
            asset_class_id=class_id[a["class"]],
            plant=plant_name.get(a["plant"], a["plant"]),
            unit=unit_name.get(a["unit"], a["unit"]),
            area=a["area"],
            service_duty=a["service_duty"],
            criticality=Criticality(a["criticality"]),
            installed_on=_to_date(a["installed_on"]),
        )
        session.add(obj)
        session.flush()
        asset_id[a["tag"]] = obj.id
    session.flush()

    # work_orders — from the rendered CSV, raw only (NO failure mode label)
    wo_csv = catalogue.RENDERED_DIR / "work_orders.csv"
    if not wo_csv.exists():
        raise SystemExit(f"ERROR: {wo_csv} missing — run `make dataset` first.")
    with open(wo_csv, newline="") as fh:
        for row in csv.DictReader(fh):
            session.add(
                WorkOrder(
                    wo_number=row["wo_number"],
                    asset_id=asset_id[row["asset_tag"]],
                    opened_on=_to_date(row["opened_on"]),
                    closed_on=_to_date(row["closed_on"]) if row["closed_on"] else None,
                    raw_description=row["raw_description"],
                    actions_taken=row["actions_taken"] or None,
                    downtime_hours=float(row["downtime_hours"]) if row["downtime_hours"] else None,
                    failure_mode_id=None,          # M3 fills this
                    normalization_score=None,       # M3 fills this
                )
            )

    # documents — metadata + file_path pointing into dataset/rendered/
    for meta in catalogue.all_documents(design):
        session.add(
            Document(
                doc_type=DocType(meta.doc_type),
                title=meta.title,
                file_path=meta.rel_path,
                asset_id=asset_id.get(meta.owner_tag) if meta.owner_tag else None,
                asset_class_id=class_id.get(meta.owner_class) if meta.owner_class else None,
            )
        )
    session.commit()


def verify(session: Session) -> tuple[bool, list[str]]:
    counts = {
        "classes": session.scalar(select(func.count()).select_from(AssetClass)),
        "assets": session.scalar(select(func.count()).select_from(Asset)),
        "failure_modes": session.scalar(select(func.count()).select_from(FailureMode)),
        "work_orders": session.scalar(select(func.count()).select_from(WorkOrder)),
        "documents": session.scalar(select(func.count()).select_from(Document)),
    }
    checks: list[tuple[str, bool]] = [
        (f"count {k}={counts[k]} (want {EXPECTED[k]})", counts[k] == EXPECTED[k])
        for k in EXPECTED
    ]

    # planted pattern: query by the three hard-coded WO numbers
    planted = session.execute(
        select(WorkOrder.wo_number, Asset.tag, WorkOrder.closed_on, WorkOrder.downtime_hours)
        .join(Asset, WorkOrder.asset_id == Asset.id)
        .where(WorkOrder.wo_number.in_(PLANTED_WOS))
    ).all()
    tags = {r.tag for r in planted}
    closed = [r.closed_on for r in planted if r.closed_on]
    downtime = sum(float(r.downtime_hours) for r in planted if r.downtime_hours is not None)
    span = 0
    if len(closed) == 3:
        lo, hi = min(closed), max(closed)
        span = (hi.year - lo.year) * 12 + (hi.month - lo.month)
    pattern_ok = (
        len(planted) == 3
        and tags == {"P-3401", "P-3105", "P-3402"}
        and span == 22
        and abs(downtime - 41.0) < 1e-6
    )
    checks.append((
        f"planted 3 WOs on {sorted(tags)}, span {span}mo, downtime {downtime:.1f}h",
        pattern_ok,
    ))

    # tier: hero class has a manual + SOP + reports registered
    hero_class_id = session.scalar(select(AssetClass.id).where(AssetClass.model == "MSC-CP200"))
    n_manual = session.scalar(
        select(func.count()).select_from(Document).where(
            Document.asset_class_id == hero_class_id, Document.doc_type == DocType.oem_manual
        )
    )
    n_sop = session.scalar(
        select(func.count()).select_from(Document).where(
            Document.asset_class_id == hero_class_id, Document.doc_type == DocType.sop
        )
    )
    hero_asset_ids = select(Asset.id).where(Asset.asset_class_id == hero_class_id).scalar_subquery()
    n_reports = session.scalar(
        select(func.count()).select_from(Document).where(
            Document.asset_id.in_(hero_asset_ids),
            Document.doc_type.in_([DocType.inspection_report, DocType.incident_report]),
        )
    )
    tier_ok = n_manual >= 1 and n_sop >= 1 and n_reports >= 1

    # ground-truth safety: no WO may carry a failure mode or normalization score
    leaked = session.scalar(
        select(func.count()).select_from(WorkOrder).where(
            (WorkOrder.failure_mode_id.isnot(None)) | (WorkOrder.normalization_score.isnot(None))
        )
    )
    null_ok = leaked == 0
    checks.append(("no true label leaked (failure_mode_id/normalization_score NULL)", null_ok))

    ok = all(passed for _, passed in checks) and pattern_ok and tier_ok

    lines = [
        f"assets: {counts['assets']} | classes: {counts['classes']} | "
        f"failure_modes: {counts['failure_modes']} | work_orders: {counts['work_orders']} | "
        f"documents: ~{counts['documents']}",
        f"PLANTED PATTERN CHECK: 3 WOs on {{P-3401,P-3105,P-3402}}, span {span}mo, "
        f"downtime {downtime:.1f}h {'OK' if pattern_ok else 'FAIL'}",
        f"TIER CHECK: hero class has manual+SOPs+reports registered "
        f"(manual={n_manual}, sop={n_sop}, reports={n_reports}) {'OK' if tier_ok else 'FAIL'}",
    ]
    if not ok:
        lines.append("FAILED CHECKS:")
        lines += [f"  - {name}" for name, passed in checks if not passed]
    return ok, lines


def run_ingest_phase() -> tuple[bool, list[str]]:
    with SessionLocal() as session:
        n_wo = session.scalar(select(func.count()).select_from(WorkOrder))
        if n_wo != EXPECTED["work_orders"]:
            raise SystemExit(
                f"ERROR: expected {EXPECTED['work_orders']} work orders — run `--phase structure` first."
            )
        stats = ingest_all(session)
        return verify_ingest(session, stats)


def verify_ingest(session: Session, stats) -> tuple[bool, list[str]]:
    total_wo = session.scalar(select(func.count()).select_from(WorkOrder))
    uncl = session.scalar(
        select(func.count()).select_from(WorkOrder).where(WorkOrder.failure_mode_id.is_(None))
    )
    uncl_pct = 100.0 * uncl / total_wo if total_wo else 0.0

    n_fm_embedded = session.scalar(
        select(func.count()).select_from(FailureMode).where(FailureMode.embedding.isnot(None))
    )

    pattern_ok, pattern_line = _pattern_query_check(session)

    zero_ok = stats.zero_chunk_docs == 0
    lines = [
        f"chunks: {stats.chunks_total} (manual: {stats.chunks_manual}, sop: {stats.chunks_sop}, "
        f"reports: {stats.chunks_reports}, csv: {stats.chunks_csv}) | "
        f"pages OCR'd: {ocr_page_count()}",
        f"docs with 0 chunks: {stats.zero_chunk_docs} {'✓' if zero_ok else 'FAIL'} | "
        f"clause-mode: {stats.clause_mode_docs} docs, fallback-mode: {stats.fallback_mode_docs} docs",
        f"failure_modes embedded: {n_fm_embedded}/25",
        f"WOs normalized: {stats.wos_classified + stats.wos_unclassified}/500 | "
        f"unclassified: {uncl} ({uncl_pct:.1f}%)",
        pattern_line,
    ]
    ok = (
        stats.chunks_total > 0
        and zero_ok
        and n_fm_embedded == 25
        and stats.wos_classified + stats.wos_unclassified == 500
        and pattern_ok
    )
    return ok, lines


def _pattern_query_check(session: Session) -> tuple[bool, str]:
    """FR-12: GROUP BY failure_mode_id over WOs on hero sister assets."""
    seal_id = session.scalar(
        select(FailureMode.id).where(FailureMode.code == "mechanical_seal_leakage")
    )
    sister_assets = select(Asset.id).where(Asset.tag.in_(HERO_SISTER_TAGS))

    row = session.execute(
        select(
            func.count(WorkOrder.id),
            func.min(WorkOrder.closed_on),
            func.max(WorkOrder.closed_on),
            func.sum(WorkOrder.downtime_hours),
        )
        .where(WorkOrder.asset_id.in_(sister_assets))
        .where(WorkOrder.failure_mode_id == seal_id)
    ).one()

    count, closed_min, closed_max, downtime = row
    span = 0
    if closed_min and closed_max:
        span = (closed_max.year - closed_min.year) * 12 + (closed_max.month - closed_min.month)
    downtime_f = float(downtime) if downtime is not None else 0.0
    ok = count == 3 and span == 22 and abs(downtime_f - 41.0) < 1e-6
    mark = "✓" if ok else "FAIL"
    line = (
        f"PATTERN QUERY (FR-12): mechanical_seal_leakage on hero sisters → "
        f"{count} WOs, {span}mo span, {downtime_f:.1f}h {mark}"
    )
    return ok, line


def run_structure_phase() -> tuple[bool, list[str]]:
    design = catalogue.load_design()
    with SessionLocal() as session:
        wipe(session)
        load_structure(session, design)
        return verify(session)


def main() -> None:
    parser = argparse.ArgumentParser(description="Meridian dataset seeder")
    parser.add_argument("--phase", choices=["structure", "ingest"], default="structure")
    args = parser.parse_args()

    if args.phase == "ingest":
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        ok, lines = run_ingest_phase()
        print("\n".join(lines))
        if ok and ocr_pages():
            print("OCR pages:", ", ".join(f"{Path(p).name}:{pg}" for p, pg in ocr_pages()))
        sys.exit(0 if ok else 1)

    # Fail fast if the schema is not migrated.
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    ok, lines = run_structure_phase()
    print("\n".join(lines))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
