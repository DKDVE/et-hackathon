"""SourceViewer backends (TDD §7): WO records, chunk deep-links, PDF serving.

Evidence chips (``WO-…`` / ``CH-…``) resolve here. Chunk responses carry a
``file_url`` that the frontend opens in react-pdf AT the cited page; the PDF
route streams the rendered artifact from the read-only dataset mount.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from app.api.deps import DbDep
from app.api.schemas import ChunkSource, PidDrawingSource, WorkOrderSource
from app.memory.ingestion.document_ingestor import resolve_dataset_path
from app.memory.repositories import chunks, documents, work_orders

router = APIRouter(prefix="/api/sources", tags=["sources"])


def _file_url(document_id: int) -> str:
    return f"/api/sources/file/{document_id}"


@router.get("/pid/asset/{asset_id}", response_model=list[PidDrawingSource])
def get_pid_for_asset(asset_id: int, db: DbDep) -> list[PidDrawingSource]:
    rows = documents.get_pid_drawings_for_asset(db, asset_id)
    return [PidDrawingSource(**r) for r in rows]


@router.get("/wo/{wo_number}", response_model=WorkOrderSource)
def get_work_order(wo_number: str, db: DbDep) -> WorkOrderSource:
    row = work_orders.get_work_order_source(db, wo_number)
    if row is None:
        raise HTTPException(404, f"work order '{wo_number}' not found")
    wo, asset_tag, asset_name, mode_code, mode_name = row
    return WorkOrderSource(
        wo_number=wo.wo_number,
        citation_id=wo.wo_number if wo.wo_number.startswith("WO-") else f"WO-{wo.wo_number}",
        asset_tag=asset_tag,
        asset_name=asset_name,
        opened_on=wo.opened_on,
        closed_on=wo.closed_on,
        raw_description=wo.raw_description,
        actions_taken=wo.actions_taken,
        downtime_hours=float(wo.downtime_hours) if wo.downtime_hours is not None else None,
        failure_mode_code=mode_code,
        failure_mode_name=mode_name,
    )


@router.get("/chunk/{chunk_id}", response_model=ChunkSource)
def get_chunk(chunk_id: int, db: DbDep) -> ChunkSource:
    row = chunks.get_chunk_source(db, chunk_id)
    if row is None:
        raise HTTPException(404, f"chunk {chunk_id} not found")
    chunk, document = row
    return ChunkSource(
        chunk_id=chunk.id,
        citation_id=f"CH-{chunk.id}",
        document_id=document.id,
        doc_type=str(document.doc_type),
        document_title=document.title,
        page=chunk.page,
        section_ref=chunk.section_ref,
        content=chunk.content,
        file_url=_file_url(document.id),
    )


@router.get("/file/{document_id}")
def get_file(document_id: int, db: DbDep) -> Response:
    """Stream a rendered PDF from the read-only dataset mount (react-pdf source).

  ponytail: Cache-Control assumes artifacts only change via re-seed (P10); safe
  to treat rendered PDFs as immutable for 24h at demo scale.
    """
    document = chunks.get_document(db, document_id)
    if document is None:
        raise HTTPException(404, f"document {document_id} not found")
    try:
        path = resolve_dataset_path(document.file_path)
    except FileNotFoundError as exc:
        raise HTTPException(404, f"file for document {document_id} not found") from exc
    media = "application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream"
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        media = f"image/{path.suffix.lower().lstrip('.')}"
        if media == "image/jpg":
            media = "image/jpeg"
    return FileResponse(
        path,
        media_type=media,
        filename=path.name,
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )
