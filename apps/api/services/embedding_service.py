"""
Embedding service using sentence-transformers.
Model: all-MiniLM-L6-v2 (384-dimensional dense vectors).
Loaded once at startup and cached in memory.
"""
from __future__ import annotations
import logging
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"


class EmbeddingService:
    def __init__(self):
        self._model: Optional[SentenceTransformer] = None

    def load(self) -> None:
        """Load the model. Call once at application startup."""
        logger.info(f"Loading embedding model: {MODEL_NAME}")
        self._model = SentenceTransformer(MODEL_NAME)
        logger.info("Embedding model loaded.")

    def encode(self, texts: list[str]) -> list[list[float]]:
        """
        Encode a list of texts to dense vectors.
        Returns list of 384-dim float lists.
        """
        if self._model is None:
            raise RuntimeError("Embedding model not loaded. Call load() first.")
        if not texts:
            return []
        embeddings = self._model.encode(texts, batch_size=32, show_progress_bar=False)
        return embeddings.tolist()

    def encode_single(self, text: str) -> list[float]:
        return self.encode([text])[0]


# Module-level singleton
_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _service
    if _service is None:
        _service = EmbeddingService()
        _service.load()
    return _service
