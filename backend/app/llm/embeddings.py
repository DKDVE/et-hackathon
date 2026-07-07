"""Local embedding model — sole import site for sentence-transformers (D-014, P7)."""

from __future__ import annotations

import logging
import threading
from functools import lru_cache

import numpy as np

from app.config import EMBEDDING_DIM, get_settings

logger = logging.getLogger(__name__)

# BGE query prefix — passages use embed_batch without prefix.
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return Embedder()


def prewarm_embedder() -> None:
    """Load embedding model (blocks until ready). Safe from a background thread."""
    get_embedder()._load()


class Embedder:
    """Lazy-loaded BGE embedder; one instance per process."""

    def __init__(self) -> None:
        self._model = None
        self._load_lock = threading.Lock()
        settings = get_settings()
        self._model_name = settings.embedding_model
        self._batch_size = settings.embed_batch_size

    def _load(self) -> None:
        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:
                return
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model %s", self._model_name)
            self._model = SentenceTransformer(self._model_name)
            logger.info("Embedding model %s ready", self._model_name)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._load()
        assert self._model is not None
        out: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            vecs = self._model.encode(
                batch,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            for row in vecs:
                vec = [float(x) for x in row]
                if len(vec) != EMBEDDING_DIM:
                    raise ValueError(f"expected dim {EMBEDDING_DIM}, got {len(vec)}")
                out.append(vec)
        return out

    def embed_query(self, text: str) -> list[float]:
        return self.embed_batch([_QUERY_PREFIX + text])[0]

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self.embed_batch([_QUERY_PREFIX + t for t in texts])

    @staticmethod
    def l2_norm(vec: list[float]) -> float:
        return float(np.linalg.norm(np.asarray(vec, dtype=np.float64)))
