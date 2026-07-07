"""Orchestrate document parse → chunk → embed → bulk insert."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.db.models import Chunk, DocType, Document, FailureMode, WorkOrder
from app.llm.embeddings import get_embedder
from app.memory.ingestion.chunker import TextChunk, chunk_document
from app.memory.ingestion.csv_parser import CsvChunk, parse_csv
from app.memory.ingestion.pdf_parser import ocr_pages, parse_pdf, reset_ocr_log
from app.memory.ingestion.wo_normalizer import embed_failure_modes, normalize_work_orders

logger = logging.getLogger(__name__)

_PDF_TYPES = {
    DocType.oem_manual,
    DocType.sop,
    DocType.inspection_report,
    DocType.incident_report,
}
_CSV_TYPES = {DocType.spares_catalogue, DocType.pm_schedule}
_SKIP_TYPES = {DocType.pid_drawing}


@dataclass
class IngestStats:
    chunks_total: int
    chunks_manual: int
    chunks_sop: int
    chunks_reports: int
    chunks_csv: int
    failure_modes_embedded: int
    wos_classified: int
    wos_unclassified: int
    zero_chunk_docs: int
    clause_mode_docs: int
    fallback_mode_docs: int


def resolve_dataset_path(file_path: str) -> Path:
    """Resolve repo-relative documents.file_path to an on-disk path."""
    p = Path(file_path)
    if p.is_file():
        return p
    if file_path.startswith("dataset/"):
        for root in (os.environ.get("DATASET_DIR"), "/dataset", Path(__file__).resolve().parents[4] / "dataset"):
            if not root:
                continue
            candidate = Path(root) / file_path.removeprefix("dataset/")
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(file_path)


def reset_ingest_state(session: Session) -> None:
    """Idempotent prep: wipe chunks and normalization artifacts."""
    session.execute(delete(Chunk))
    session.execute(
        update(WorkOrder).values(failure_mode_id=None, normalization_score=None)
    )
    session.execute(update(FailureMode).values(embedding=None))
    session.commit()


_CLAUSE_DOC_TYPES = {DocType.oem_manual, DocType.sop}


def _ingest_document(
    session: Session, doc: Document, path: Path
) -> tuple[list[TextChunk | CsvChunk], str, str]:
    """Parse one document; return (chunks, category, chunk_mode).

    chunk_mode is "skip"/"csv" for non-PDF paths, else "clause"/"fallback"/"plain".
    """
    if doc.doc_type in _SKIP_TYPES:
        return [], "skip", "skip"
    if doc.doc_type in _CSV_TYPES:
        chunks = parse_csv(path, section_ref=doc.title)
        return chunks, "csv", "csv"
    if doc.doc_type not in _PDF_TYPES:
        logger.warning("Unknown doc_type %s for %s — skipping", doc.doc_type, path)
        return [], "skip", "skip"

    pages = parse_pdf(path)
    chunks, mode = chunk_document(
        pages, clause_boundaries=doc.doc_type in _CLAUSE_DOC_TYPES, doc_id=doc.id
    )
    if doc.doc_type == DocType.oem_manual:
        return chunks, "manual", mode
    if doc.doc_type == DocType.sop:
        return chunks, "sop", mode
    return chunks, "reports", mode


def ingest_all(session: Session) -> IngestStats:
    """Full ingest pipeline: reset → embed modes → documents → normalize WOs."""
    reset_ocr_log()
    reset_ingest_state(session)

    n_modes = embed_failure_modes(session)

    docs = session.scalars(select(Document).order_by(Document.id)).all()
    embedder = get_embedder()
    counts = {"manual": 0, "sop": 0, "reports": 0, "csv": 0}
    mode_counts = {"clause": 0, "fallback": 0}
    all_chunk_rows: list[Chunk] = []

    for doc in docs:
        try:
            path = resolve_dataset_path(doc.file_path)
        except FileNotFoundError:
            logger.error("Missing file for document %s: %s", doc.id, doc.file_path)
            raise

        parsed, category, mode = _ingest_document(session, doc, path)
        if category == "skip":
            continue

        # Silent data-loss guard: a non-skipped document must yield ≥1 chunk.
        if not parsed:
            raise RuntimeError(
                f"Document {doc.id} ({doc.doc_type} {doc.file_path}) produced 0 chunks — "
                "ingest aborted to prevent silent data loss."
            )

        if mode in mode_counts:
            mode_counts[mode] += 1

        texts = [c.content for c in parsed]
        embeddings = embedder.embed_batch(texts)
        for chunk_data, emb in zip(parsed, embeddings, strict=True):
            all_chunk_rows.append(
                Chunk(
                    document_id=doc.id,
                    page=chunk_data.page,
                    section_ref=chunk_data.section_ref,
                    content=chunk_data.content,
                    embedding=emb,
                )
            )
        counts[category] += len(parsed)

    session.add_all(all_chunk_rows)
    session.commit()

    classified, unclassified = normalize_work_orders(session)

    return IngestStats(
        chunks_total=sum(counts.values()),
        chunks_manual=counts["manual"],
        chunks_sop=counts["sop"],
        chunks_reports=counts["reports"],
        chunks_csv=counts["csv"],
        failure_modes_embedded=n_modes,
        wos_classified=classified,
        wos_unclassified=unclassified,
        zero_chunk_docs=0,
        clause_mode_docs=mode_counts["clause"],
        fallback_mode_docs=mode_counts["fallback"],
    )


def ocr_page_count() -> int:
    return len(ocr_pages())
