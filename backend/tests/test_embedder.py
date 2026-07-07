"""Embedder smoke test — loads the real model (slow)."""

from __future__ import annotations

import pytest

from app.config import EMBEDDING_DIM
from app.llm.embeddings import Embedder, get_embedder


@pytest.mark.slow
def test_embed_batch_dim_and_normalized() -> None:
    embedder = get_embedder()
    vecs = embedder.embed_batch(["mechanical seal weeping at gland", "bearing vibration elevated"])
    assert len(vecs) == 2
    for v in vecs:
        assert len(v) == EMBEDDING_DIM
        assert abs(Embedder.l2_norm(v) - 1.0) < 1e-3


@pytest.mark.slow
def test_embed_query_differs_from_passage() -> None:
    embedder = get_embedder()
    text = "seal leakage at gland follower"
    q = embedder.embed_query(text)
    p = embedder.embed_batch([text])[0]
    # BGE query prefix should change the vector
    assert any(abs(a - b) > 1e-4 for a, b in zip(q, p, strict=True))
