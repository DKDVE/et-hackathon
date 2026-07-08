"""Memory layer read models — knowledge health queries (D-012/P11)."""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import (
    Asset,
    AssetClass,
    Chunk,
    DocType,
    Document,
    FailureMode,
    HumanVerdict,
    WoDisposition,
    WorkOrder,
)
from app.memory.candidates import top_mode_candidates
from app.memory.effective_mode import effective_failure_mode_id


def _coverage_tier(
    *,
    manual_available: bool,
    sop_count: int,
    wo_count: int,
    classified_ratio: float,
) -> str:
    s = get_settings()
    if (
        manual_available
        and sop_count >= s.memory_coverage_good_min_sops
        and wo_count >= s.memory_coverage_good_min_wos
        and classified_ratio >= s.memory_coverage_good_classified_ratio
    ):
        return "Good"
    if manual_available or sop_count > 0 or wo_count >= s.memory_coverage_partial_min_wos:
        return "Partial"
    return "Thin"


def get_overview(session: Session) -> dict:
    wo_total = session.scalar(select(func.count()).select_from(WorkOrder)) or 0
    routine = session.scalar(
        select(func.count())
        .select_from(WorkOrder)
        .where(WorkOrder.disposition == WoDisposition.routine)
    ) or 0
    auto_classified = session.scalar(
        select(func.count())
        .select_from(WorkOrder)
        .where(
            WorkOrder.disposition == WoDisposition.failure,
            WorkOrder.failure_mode_id.isnot(None),
        )
    ) or 0
    wo_unclassified = session.scalar(
        select(func.count())
        .select_from(WorkOrder)
        .where(
            WorkOrder.disposition == WoDisposition.failure,
            WorkOrder.failure_mode_id.is_(None),
        )
    ) or 0
    human_reviewed = session.scalar(
        select(func.count()).select_from(WorkOrder).where(WorkOrder.human_reviewed_at.isnot(None))
    ) or 0
    return {
        "asset_count": session.scalar(select(func.count()).select_from(Asset)) or 0,
        "document_count": session.scalar(select(func.count()).select_from(Document)) or 0,
        "chunk_count": session.scalar(select(func.count()).select_from(Chunk)) or 0,
        "work_order_count": wo_total,
        "wo_failure_classified": auto_classified,
        "wo_routine_closures": routine,
        "wo_unclassified": wo_unclassified,
        "wo_human_reviewed": human_reviewed,
        # legacy keys — same semantics, kept for API compat
        "wo_auto_classified": auto_classified,
        "taxonomy_size": session.scalar(select(func.count()).select_from(FailureMode)) or 0,
    }


def get_assets(session: Session) -> list[dict]:
    eff = effective_failure_mode_id()
    rows = session.execute(
        select(
            Asset,
            AssetClass.class_name,
            func.count(WorkOrder.id).label("wo_count"),
            func.sum(case((eff.isnot(None), 1), else_=0)).label("classified"),
            func.max(WorkOrder.closed_on).label("last_date"),
        )
        .join(AssetClass, Asset.asset_class_id == AssetClass.id)
        .outerjoin(WorkOrder, WorkOrder.asset_id == Asset.id)
        .where(WorkOrder.disposition == WoDisposition.failure)
        .group_by(Asset.id, AssetClass.class_name)
        .order_by(Asset.tag)
    ).all()

    # Class-level manual + per-asset SOP counts (batch).
    class_ids = {a.asset_class_id for a, *_ in rows}
    manual_classes = set(
        session.scalars(
            select(Document.asset_class_id).where(
                Document.asset_class_id.in_(class_ids),
                Document.doc_type == DocType.oem_manual,
            )
        ).all()
    )
    sop_by_class = dict(
        session.execute(
            select(Document.asset_class_id, func.count())
            .where(Document.asset_class_id.in_(class_ids), Document.doc_type == DocType.sop)
            .group_by(Document.asset_class_id)
        ).all()
    )

    out: list[dict] = []
    for asset, class_name, wo_count, classified, last_date in rows:
        wo_count = int(wo_count or 0)
        classified = int(classified or 0)
        ratio = classified / wo_count if wo_count else 0.0
        manual = asset.asset_class_id in manual_classes
        sop_count = int(sop_by_class.get(asset.asset_class_id, 0))
        out.append(
            {
                "asset_id": asset.id,
                "tag": asset.tag,
                "name": asset.name,
                "asset_class": class_name,
                "manual_available": manual,
                "sop_count": sop_count,
                "wo_count": wo_count,
                "last_inspection_date": last_date,
                "classified_ratio": round(ratio, 3),
                "coverage_tier": _coverage_tier(
                    manual_available=manual,
                    sop_count=sop_count,
                    wo_count=wo_count,
                    classified_ratio=ratio,
                ),
            }
        )
    return out


def get_documents(session: Session) -> list[dict]:
    rows = session.execute(
        select(
            Document,
            Asset.tag,
            AssetClass.class_name,
            func.count(Chunk.id).label("chunk_count"),
            func.count(func.distinct(Chunk.page)).label("page_count"),
        )
        .outerjoin(Asset, Document.asset_id == Asset.id)
        .outerjoin(AssetClass, Document.asset_class_id == AssetClass.id)
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .group_by(Document.id, Asset.tag, AssetClass.class_name)
        .order_by(Document.title)
    ).all()
    return [
        {
            "document_id": doc.id,
            "title": doc.title,
            "doc_type": str(doc.doc_type),
            "owner_asset_tag": tag,
            "owner_class": class_name,
            "chunk_count": int(chunk_count or 0),
            "ocr_page_count": int(page_count or 0),
            "file_url": f"/api/sources/file/{doc.id}",
        }
        for doc, tag, class_name, chunk_count, page_count in rows
    ]


def get_taxonomy(session: Session) -> list[dict]:
    modes = session.scalars(
        select(FailureMode).order_by(FailureMode.family, FailureMode.code)
    ).all()
    auto_counts = dict(
        session.execute(
            select(WorkOrder.failure_mode_id, func.count())
            .where(WorkOrder.failure_mode_id.isnot(None))
            .group_by(WorkOrder.failure_mode_id)
        ).all()
    )
    human_counts = dict(
        session.execute(
            select(WorkOrder.human_failure_mode_id, func.count())
            .where(
                WorkOrder.human_failure_mode_id.isnot(None),
                WorkOrder.human_verdict.in_(
                    (HumanVerdict.confirmed, HumanVerdict.corrected)
                ),
            )
            .group_by(WorkOrder.human_failure_mode_id)
        ).all()
    )
    mean_scores = dict(
        session.execute(
            select(WorkOrder.failure_mode_id, func.avg(WorkOrder.normalization_score))
            .where(WorkOrder.failure_mode_id.isnot(None))
            .group_by(WorkOrder.failure_mode_id)
        ).all()
    )
    by_family: dict[str, list[dict]] = {}
    for m in modes:
        by_family.setdefault(m.family, []).append(
            {
                "mode_id": m.id,
                "code": m.code,
                "name": m.name,
                "auto_wo_count": int(auto_counts.get(m.id, 0)),
                "human_override_count": int(human_counts.get(m.id, 0)),
                "mean_normalization_score": round(float(mean_scores[m.id]), 3)
                if m.id in mean_scores and mean_scores[m.id] is not None
                else None,
            }
        )
    return [
        {"family": family, "modes": modes_list}
        for family, modes_list in sorted(by_family.items())
    ]


def get_review_queue(session: Session) -> list[dict]:
    settings = get_settings()
    thr = settings.norm_threshold
    band_top = thr + 0.05
    stmt = (
        select(WorkOrder, Asset.tag, FailureMode.code, FailureMode.family)
        .join(Asset, WorkOrder.asset_id == Asset.id)
        .outerjoin(FailureMode, WorkOrder.failure_mode_id == FailureMode.id)
        .where(WorkOrder.disposition == WoDisposition.failure)
        .where(WorkOrder.human_reviewed_at.is_(None))
        .where(
            (WorkOrder.failure_mode_id.is_(None))
            | (
                (WorkOrder.normalization_score >= thr)
                & (WorkOrder.normalization_score < band_top)
            )
        )
        .order_by(WorkOrder.normalization_score.asc().nullsfirst(), WorkOrder.wo_number)
    )
    rows = session.execute(stmt).all()
    out: list[dict] = []
    for wo, tag, auto_code, family in rows:
        candidates = [
            {"mode_id": mid, "code": code, "name": name, "score": round(score, 3)}
            for mid, code, name, score in top_mode_candidates(session, wo.raw_description, limit=3)
        ]
        out.append(
            {
                "wo_id": wo.id,
                "wo_number": wo.wo_number,
                "asset_tag": tag,
                "raw_description": wo.raw_description,
                "auto_failure_mode_code": auto_code,
                "auto_failure_mode_family": family,
                "normalization_score": float(wo.normalization_score)
                if wo.normalization_score is not None
                else None,
                "candidates": candidates,
            }
        )
    return out


def coverage_footnote() -> str:
    return get_settings().memory_coverage_footnote
