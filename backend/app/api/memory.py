"""Memory layer API — knowledge health surface (D-012, D-023)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbDep
from app.api.schemas import (
    MemoryAssetRow,
    MemoryAssetsResponse,
    MemoryDocumentRow,
    MemoryOverview,
    ReviewQueueRow,
    ReviewVerdictRequest,
    ReviewVerdictResponse,
    TaxonomyFamilyGroup,
    TaxonomyModeRow,
)
from app.db.models import HumanVerdict
from app.memory.repositories import memory, review

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/overview", response_model=MemoryOverview)
def memory_overview(db: DbDep) -> MemoryOverview:
    return MemoryOverview(**memory.get_overview(db))


@router.get("/assets", response_model=MemoryAssetsResponse)
def memory_assets(db: DbDep) -> MemoryAssetsResponse:
    rows = memory.get_assets(db)
    return MemoryAssetsResponse(
        assets=[MemoryAssetRow(**r) for r in rows],
        coverage_footnote=memory.coverage_footnote(),
    )


@router.get("/documents", response_model=list[MemoryDocumentRow])
def memory_documents(db: DbDep) -> list[MemoryDocumentRow]:
    return [MemoryDocumentRow(**r) for r in memory.get_documents(db)]


@router.get("/taxonomy", response_model=list[TaxonomyFamilyGroup])
def memory_taxonomy(db: DbDep) -> list[TaxonomyFamilyGroup]:
    return [
        TaxonomyFamilyGroup(
            family=g["family"],
            modes=[TaxonomyModeRow(**m) for m in g["modes"]],
        )
        for g in memory.get_taxonomy(db)
    ]


@router.get("/review-queue", response_model=list[ReviewQueueRow])
def memory_review_queue(db: DbDep) -> list[ReviewQueueRow]:
    return [ReviewQueueRow(**r) for r in memory.get_review_queue(db)]


@router.post("/review/{wo_id}", response_model=ReviewVerdictResponse)
def submit_review(wo_id: int, body: ReviewVerdictRequest, db: DbDep) -> ReviewVerdictResponse:
    wo = review.submit_review(
        db,
        wo_id,
        verdict=HumanVerdict(body.verdict),
        failure_mode_id=body.failure_mode_id,
    )
    return ReviewVerdictResponse(
        wo_id=wo.id,
        wo_number=wo.wo_number,
        human_verdict=str(wo.human_verdict),
        human_failure_mode_id=wo.human_failure_mode_id,
        human_failure_mode_code=review.get_mode_code(db, wo.human_failure_mode_id),
        human_reviewed_at=wo.human_reviewed_at,  # type: ignore[arg-type]
        failure_mode_id=wo.failure_mode_id,
        normalization_score=float(wo.normalization_score)
        if wo.normalization_score is not None
        else None,
    )
