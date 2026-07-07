"""WO failure-mode normalization via embedding similarity (D-008)."""

from __future__ import annotations

import logging

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import FailureMode, WorkOrder
from app.llm.embeddings import get_embedder

logger = logging.getLogger(__name__)


def classify_vector(
    query: np.ndarray,
    mode_matrix: np.ndarray,
    *,
    threshold: float,
    margin: float,
    families: list[str] | None = None,
) -> tuple[int | None, float]:
    """Return (best_index, top_score); index is None if the top mode is rejected.

    D-017 rule: assign the top mode iff it clears ``threshold`` AND either it
    clears ``margin`` over the runner-up OR the runner-up is in the same family.
    The margin is therefore a cross-family confusion guard only — within a
    family, adjacent modes are expected to near-tie and the best score wins.
    """
    scores = mode_matrix @ query
    top_idx = int(np.argmax(scores))
    top_score = float(scores[top_idx])
    if top_score < threshold:
        return None, top_score
    if len(scores) < 2:
        return top_idx, top_score

    runner_idx = int(np.argsort(scores)[-2])
    runner_up = float(scores[runner_idx])
    margin_ok = (top_score - runner_up) >= margin
    same_family = (
        families is not None and families[top_idx] == families[runner_idx]
    )
    if margin_ok or same_family:
        return top_idx, top_score
    return None, top_score


def embed_failure_modes(session: Session) -> int:
    """Embed all failure_mode descriptions; return count embedded."""
    modes = session.scalars(select(FailureMode).order_by(FailureMode.id)).all()
    texts = [(m.description or m.name or m.code) for m in modes]
    embedder = get_embedder()
    vectors = embedder.embed_batch(texts)
    for mode, vec in zip(modes, vectors, strict=True):
        mode.embedding = vec
    session.commit()
    return len(modes)


def normalize_work_orders(session: Session) -> tuple[int, int]:
    """Normalize all WOs; return (classified_count, unclassified_count)."""
    settings = get_settings()
    threshold = settings.norm_threshold
    margin = settings.norm_margin

    modes = session.scalars(select(FailureMode).order_by(FailureMode.id)).all()
    if not modes or modes[0].embedding is None:
        raise RuntimeError("failure_modes not embedded — run embed_failure_modes first")

    mode_matrix = np.asarray([m.embedding for m in modes], dtype=np.float64)
    mode_ids = [m.id for m in modes]
    families = [m.family for m in modes]

    work_orders = session.scalars(select(WorkOrder).order_by(WorkOrder.id)).all()
    embedder = get_embedder()
    query_vectors = np.asarray(
        embedder.embed_batch([wo.raw_description for wo in work_orders]),
        dtype=np.float64,
    )

    classified = 0
    for wo, qvec in zip(work_orders, query_vectors, strict=True):
        idx, score = classify_vector(
            qvec, mode_matrix, threshold=threshold, margin=margin, families=families
        )
        wo.normalization_score = score
        if idx is not None:
            wo.failure_mode_id = mode_ids[idx]
            classified += 1
        else:
            wo.failure_mode_id = None

    session.commit()
    unclassified = len(work_orders) - classified
    logger.info("Normalized %d WOs (%d classified, %d unclassified)", len(work_orders), classified, unclassified)
    return classified, unclassified
