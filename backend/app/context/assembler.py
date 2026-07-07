"""OCE Context Service — ``build_shared_context`` (P1/P2, TDD §5, D-015).

The single deterministic assembly step: a pure function of database state that
freezes the event-relevant slice of the Operational Memory Layer into an
immutable ``SharedContext`` before any LLM reasoning begins. No LLM calls, no
mid-run retrieval — retrieval happens exactly once, here (P1).
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Sequence
from contextlib import nullcontext
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.context import evidence
from app.db.engine import SessionLocal
from app.db.models import DocType, Dossier, DossierStatus
from app.domain.models import ChunkRecord, SharedContext
from app.domain.symptom_map import expansion_terms, symptom_modes
from app.llm.embeddings import get_embedder
from app.memory.repositories import assets, chunks, events, work_orders

logger = logging.getLogger(__name__)

# Exact-token patterns for the D-015 lexical channel. Industrial text is dense
# with identifiers that embeddings blur; these recover them verbatim.
_TAG_RE = re.compile(r"\b[A-Z]{1,2}-\d{3,4}\b")
_WO_RE = re.compile(r"\bWO-\d{4}-\d{4}\b")
_SOP_RE = re.compile(r"\bSOP-\d+\b", re.IGNORECASE)
_PART_RE = re.compile(r"\b[A-Z]{2,}(?:-[A-Za-z0-9.]+){1,}\b")
_QUOTED_RE = re.compile(r'"([^"]+)"')


def extract_tokens(text: str) -> list[str]:
    """Exact identifiers/phrases from event text for the lexical channel."""
    if not text:
        return []
    tokens: set[str] = set()
    for pattern in (_TAG_RE, _WO_RE, _SOP_RE, _PART_RE):
        tokens.update(pattern.findall(text))
    tokens.update(m.strip() for m in _QUOTED_RE.findall(text))
    return sorted(t for t in tokens if len(t.strip()) >= 2)


def _build_query(symptom_category: str, note: str | None, terms: Sequence[str]) -> str:
    parts = [symptom_category.replace("_", " ")]
    if note:
        parts.append(note)
    parts.extend(terms)
    return " ".join(parts)


def _assemble_bucket(
    session: Session,
    query_embedding: Sequence[float],
    tokens: Sequence[str],
    doc_types: Sequence[DocType],
    *,
    scope_kind: str,
    asset_id: int,
    class_id: int | None,
    sister_ids: Sequence[int],
    k: int,
    overflow: int,
) -> list[ChunkRecord]:
    """Semantic top-k unioned with lexical hits (D-015): dedupe, tag channel.

    Semantic-only → ``semantic``; also a lexical hit → ``both``; lexical-only →
    ``lexical`` (capped at ``overflow`` extra per bucket)."""
    semantic = chunks.semantic_search(
        session, query_embedding, doc_types,
        scope_kind=scope_kind, asset_id=asset_id, class_id=class_id,
        sister_ids=sister_ids, k=k,
    )
    lexical = chunks.lexical_search(
        session, tokens, doc_types,
        scope_kind=scope_kind, asset_id=asset_id, class_id=class_id,
        sister_ids=sister_ids, limit=k + overflow,
    )
    lexical_ids = {c.id for c, _dt in lexical}

    records: list[ChunkRecord] = []
    seen: set[int] = set()
    for chunk, _distance, doc_type in semantic:
        seen.add(chunk.id)
        channel = "both" if chunk.id in lexical_ids else "semantic"
        records.append(_to_record(chunk, doc_type, channel))

    added = 0
    for chunk, doc_type in lexical:
        if chunk.id in seen:
            continue
        if added >= overflow:
            break
        records.append(_to_record(chunk, doc_type, "lexical"))
        seen.add(chunk.id)
        added += 1
    return records


def _to_record(chunk: object, doc_type: str, channel: str) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk.id,  # type: ignore[attr-defined]
        document_id=chunk.document_id,  # type: ignore[attr-defined]
        doc_type=doc_type,
        page=chunk.page,  # type: ignore[attr-defined]
        section_ref=chunk.section_ref,  # type: ignore[attr-defined]
        content=chunk.content,  # type: ignore[attr-defined]
        retrieval_channel=channel,
    )


def build_shared_context(
    event_id: int,
    session: Session | None = None,
    *,
    timings: dict[str, float] | None = None,
) -> SharedContext:
    """Assemble the immutable Shared Context for an event (P1/P2, TDD §5).

    Pure function of DB state — no LLM. Persists the frozen snapshot into
    ``dossiers.shared_context`` (dossier created in ``assembling`` status) and
    returns the ``SharedContext``. Per-stage timings are logged and, if a
    ``timings`` dict is passed, populated into it.
    """
    owns_session = session is None
    ctx_mgr = SessionLocal() if owns_session else nullcontext(session)
    stage: dict[str, float] = {}

    with ctx_mgr as sess:
        assert sess is not None
        t_total = time.perf_counter()

        def _mark(name: str, start: float) -> None:
            stage[name] = round((time.perf_counter() - start) * 1000, 2)

        t = time.perf_counter()
        event = events.get_event(sess, event_id)
        if event is None:
            raise ValueError(f"event {event_id} not found")
        profile = assets.get_asset_profile(sess, _asset_id := _require_asset(sess, event.asset_tag))
        class_id = assets.get_asset_class_id(sess, _asset_id)
        sister_ids = assets.get_sister_asset_ids(sess, _asset_id)
        _mark("profile_sisters", t)

        modes = symptom_modes(event.symptom_category)

        t = time.perf_counter()
        cfg = get_settings()
        failure_history = work_orders.get_failure_history(
            sess, _asset_id, cap=cfg.failure_history_cap
        )
        _mark("failure_history", t)

        t = time.perf_counter()
        sister_incidents = work_orders.get_sister_incidents(
            sess, sister_ids, modes, cap=cfg.sister_incidents_cap
        )
        _mark("sister_incidents", t)

        t = time.perf_counter()
        terms = expansion_terms(event.symptom_category)
        query = _build_query(event.symptom_category, event.note, terms)
        query_embedding = get_embedder().embed_query(query)
        tokens = extract_tokens(f"{event.note or ''} {event.symptom_category}")
        _mark("query_embed", t)

        t = time.perf_counter()
        manual_chunks = _assemble_bucket(
            sess, query_embedding, tokens, [DocType.oem_manual],
            scope_kind="asset_or_class", asset_id=_asset_id, class_id=class_id,
            sister_ids=sister_ids, k=cfg.retrieval_manual_k,
            overflow=cfg.retrieval_lexical_overflow,
        )
        sop_chunks = _assemble_bucket(
            sess, query_embedding, tokens, [DocType.sop],
            scope_kind="asset_or_class", asset_id=_asset_id, class_id=class_id,
            sister_ids=sister_ids, k=cfg.retrieval_sop_k,
            overflow=cfg.retrieval_lexical_overflow,
        )
        report_chunks = _assemble_bucket(
            sess, query_embedding, tokens,
            [DocType.inspection_report, DocType.incident_report],
            scope_kind="asset_or_sisters", asset_id=_asset_id, class_id=class_id,
            sister_ids=sister_ids, k=cfg.retrieval_reports_k,
            overflow=cfg.retrieval_lexical_overflow,
        )
        _mark("chunks", t)

        t = time.perf_counter()
        pattern_stats = work_orders.get_pattern_stats(
            sess, [_asset_id, *sister_ids], modes
        )
        _mark("pattern_stats", t)

        pool = evidence.pool_from_records(
            failure_history, sister_incidents, manual_chunks, sop_chunks, report_chunks
        )

        shared = SharedContext(
            event=event,
            asset_profile=profile,
            failure_history=failure_history,
            sister_incidents=sister_incidents,
            manual_chunks=manual_chunks,
            sop_chunks=sop_chunks,
            report_chunks=report_chunks,
            pattern_stats=pattern_stats,
            evidence_pool=pool,
            assembled_at=datetime.now(UTC),
        ).with_hash()

        t = time.perf_counter()
        _persist_snapshot(sess, event_id, shared)
        _mark("persist", t)

        stage["total"] = round((time.perf_counter() - t_total) * 1000, 2)
        logger.info("assembler timings (ms): %s", stage)
        if timings is not None:
            timings.update(stage)
        return shared


def _require_asset(session: Session, tag: str) -> int:
    asset_id = assets.get_asset_id_by_tag(session, tag)
    if asset_id is None:
        raise ValueError(f"asset {tag} not found")
    return asset_id


def _persist_snapshot(session: Session, event_id: int, shared: SharedContext) -> None:
    dossier = session.scalar(select(Dossier).where(Dossier.event_id == event_id))
    snapshot = shared.model_dump(mode="json")
    if dossier is None:
        dossier = Dossier(
            event_id=event_id,
            status=DossierStatus.assembling,
            shared_context=snapshot,
        )
        session.add(dossier)
    else:
        dossier.status = DossierStatus.assembling
        dossier.shared_context = snapshot
    session.commit()
