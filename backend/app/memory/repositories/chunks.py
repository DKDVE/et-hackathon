"""Chunk repository — pgvector semantic search + deterministic lexical channel.

Two retrieval channels (D-015, hybrid-lite):
  * semantic — pgvector cosine top-k, scoped by document ownership;
  * lexical  — Postgres ILIKE over exact tokens, same scope.
The union/dedup/tagging that combines them lives in the assembler (business
logic); this module only runs the two scoped queries.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.orm import Session

from app.db.models import Chunk, DocType, Document

ScopeKind = str  # "asset_or_class" | "asset_or_sisters"


def get_chunk_source(
    session: Session, chunk_id: int
) -> tuple[Chunk, Document] | None:
    """A single chunk + its owning document, for the PDF deep-link SourceViewer."""
    row = session.execute(
        select(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .where(Chunk.id == chunk_id)
    ).first()
    return (row[0], row[1]) if row else None


def get_document(session: Session, document_id: int) -> Document | None:
    return session.get(Document, document_id)


def _scope(
    kind: ScopeKind, asset_id: int, class_id: int | None, sister_ids: Sequence[int]
) -> ColumnElement[bool]:
    if kind == "asset_or_class":
        # Manuals/SOPs: docs owned by the asset or its class.
        return or_(Document.asset_id == asset_id, Document.asset_class_id == class_id)
    if kind == "asset_or_sisters":
        # Reports: docs owned by the asset OR any sister (cross-sister thread).
        owner_ids = [asset_id, *sister_ids]
        return Document.asset_id.in_(owner_ids)
    raise ValueError(f"unknown scope kind: {kind}")


def semantic_search(
    session: Session,
    query_embedding: Sequence[float],
    doc_types: Sequence[DocType],
    *,
    scope_kind: ScopeKind,
    asset_id: int,
    class_id: int | None,
    sister_ids: Sequence[int],
    k: int,
) -> list[tuple[Chunk, float, str]]:
    """pgvector cosine top-k within scope. Returns (chunk, distance, doc_type)."""
    distance = Chunk.embedding.cosine_distance(list(query_embedding))
    stmt = (
        select(Chunk, distance, Document.doc_type)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.doc_type.in_(doc_types))
        .where(Chunk.embedding.isnot(None))
        .where(_scope(scope_kind, asset_id, class_id, sister_ids))
        .order_by(distance)
        .limit(k)
    )
    return [(c, float(d), str(dt)) for c, d, dt in session.execute(stmt)]


def lexical_search(
    session: Session,
    tokens: Sequence[str],
    doc_types: Sequence[DocType],
    *,
    scope_kind: ScopeKind,
    asset_id: int,
    class_id: int | None,
    sister_ids: Sequence[int],
    limit: int,
) -> list[tuple[Chunk, str]]:
    """ILIKE over exact tokens within scope. Returns (chunk, doc_type).

    Ordered by chunk id for determinism. Empty tokens → no query.
    """
    tokens = [t for t in tokens if t and t.strip()]
    if not tokens:
        return []
    conditions = [Chunk.content.ilike(f"%{t}%") for t in tokens]
    stmt = (
        select(Chunk, Document.doc_type)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.doc_type.in_(doc_types))
        .where(_scope(scope_kind, asset_id, class_id, sister_ids))
        .where(or_(*conditions))
        .order_by(Chunk.id)
        .limit(limit)
    )
    return [(c, str(dt)) for c, dt in session.execute(stmt)]
