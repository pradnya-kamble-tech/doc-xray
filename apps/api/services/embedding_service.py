"""
Embedding Service for Doc-XRay.

Uses Gemini text-embedding-004 API (768 dimensions) instead of sentence-transformers.
This is Vercel-compatible: no local model download required.

Falls back gracefully if Gemini API key is missing or quota is exhausted:
  returns zero vectors so the pipeline completes but vector search returns no results.
"""
from __future__ import annotations
import logging
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768  # Gemini text-embedding-004 output dimensions


class GeminiEmbeddingService:
    """Uses Gemini text-embedding-004 API to generate embeddings."""

    def __init__(self):
        if not settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set — embeddings will be zero vectors (search disabled)")
            self._available = False
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            self._genai = genai
            self._available = True
            logger.info("Gemini embedding service initialized (text-embedding-004)")
        except ImportError:
            logger.warning("google-generativeai not installed — embeddings disabled")
            self._available = False

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode a list of texts into embedding vectors."""
        if not self._available:
            return [[0.0] * EMBEDDING_DIM for _ in texts]
        embeddings = []
        for text in texts:
            emb = self._encode_one(text, "retrieval_document")
            embeddings.append(emb)
        return embeddings

    def encode_single(self, text: str) -> list[float]:
        """Encode a single query text."""
        if not self._available:
            return [0.0] * EMBEDDING_DIM
        return self._encode_one(text, "retrieval_query")

    def _encode_one(self, text: str, task_type: str) -> list[float]:
        try:
            result = self._genai.embed_content(
                model="models/text-embedding-004",
                content=text[:2048],
                task_type=task_type,
            )
            return result["embedding"]
        except Exception as e:
            err_str = str(e).lower()
            if "429" in str(e) or "quota" in err_str or "resource_exhausted" in err_str:
                logger.warning(f"Gemini embedding quota exhausted, using zero vector: {e}")
            else:
                logger.error(f"Gemini embedding error, using zero vector: {e}")
            return [0.0] * EMBEDDING_DIM


# ── Singleton ──────────────────────────────────────────────────────────────
_service: Optional[GeminiEmbeddingService] = None


def get_embedding_service() -> GeminiEmbeddingService:
    global _service
    if _service is None:
        _service = GeminiEmbeddingService()
    return _service
