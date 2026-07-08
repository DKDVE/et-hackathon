"""Top failure-mode candidates for review-queue picker (P2)."""

from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import FailureMode
from app.llm.embeddings import get_embedder


def top_mode_candidates(
    session: Session, raw_description: str, *, limit: int = 3
) -> list[tuple[int, str, str, float]]:
    """Return [(mode_id, code, name, score), ...] sorted by score desc."""
    modes = session.scalars(select(FailureMode).order_by(FailureMode.id)).all()
    if not modes or modes[0].embedding is None:
        return []
    matrix = np.asarray([m.embedding for m in modes], dtype=np.float64)
    q = np.asarray(get_embedder().embed_batch([raw_description])[0], dtype=np.float64)
    scores = matrix @ q
    order = np.argsort(scores)[::-1][:limit]
    return [
        (modes[i].id, modes[i].code, modes[i].name, float(scores[i])) for i in order
    ]
