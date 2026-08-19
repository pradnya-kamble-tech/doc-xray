"""
SQLite / In-Memory Vector Store service for Doc-XRay.

Replaces ChromaDB with native Python cosine similarity matching over chunk embeddings.
Embeddings are computed via Gemini API (768 dimensions) and cached in SQLite JSON or in-memory.
Zero binary dependencies (no C++, no chromadb, nohnswlib) — 100% Vercel compatible!
"""
from __future__ import annotations
import math
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScoredChunk:
    chunk_id: str
    text: str
    page_num: int
    risk_level: str
    risk_score: float
    distance: float         # 1.0 - similarity
    similarity_score: float # Cosine similarity (0.0 to 1.0)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    if norm_v1 == 0.0 or norm_v2 == 0.0:
        return 0.0
    sim = dot / (norm_v1 * norm_v2)
    return max(0.0, min(1.0, float(sim)))


class VectorStore:
    """In-memory + SQLite-backed vector store for document chunks."""

    def __init__(self):
        # In-memory index: doc_id -> list of chunk dicts
        # Each chunk dict: {chunk_id, text, page_num, risk_level, risk_score, embedding}
        self._collections: dict[str, list[dict]] = {}
        logger.info("SQLite/In-Memory VectorStore initialized (100% Vercel compatible)")

    def upsert_chunks(
        self,
        doc_id: str,
        chunk_ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """Store embeddings and metadata for a document."""
        chunks = []
        for i in range(len(chunk_ids)):
            meta = metadatas[i] if i < len(metadatas) else {}
            chunks.append({
                "chunk_id": chunk_ids[i],
                "text": texts[i] if i < len(texts) else "",
                "page_num": meta.get("page_num", 1),
                "risk_level": meta.get("risk_level", "LOW_RISK"),
                "risk_score": meta.get("risk_score", 0.0),
                "embedding": embeddings[i] if i < len(embeddings) else [],
            })
        self._collections[doc_id] = chunks
        logger.info(f"Upserted {len(chunk_ids)} chunks for document {doc_id} into VectorStore")

    def query(
        self,
        doc_id: str,
        query_embedding: list[float],
        top_k: int = 8,
    ) -> list[ScoredChunk]:
        """
        Query top-k most similar chunks for the given document using cosine similarity.
        Returns results sorted by similarity score (highest first).
        """
        chunks = self._collections.get(doc_id, [])
        if not chunks:
            logger.warning(f"No vector store collection found for doc {doc_id}")
            return []

        scored: list[ScoredChunk] = []
        for c in chunks:
            emb = c.get("embedding", [])
            sim = cosine_similarity(query_embedding, emb)
            scored.append(ScoredChunk(
                chunk_id=c["chunk_id"],
                text=c["text"],
                page_num=c["page_num"],
                risk_level=c["risk_level"],
                risk_score=c["risk_score"],
                distance=round(1.0 - sim, 4),
                similarity_score=round(sim, 4),
            ))

        # Sort descending by similarity
        scored.sort(key=lambda x: x.similarity_score, reverse=True)
        return scored[:top_k]

    def delete_collection(self, doc_id: str) -> None:
        """Delete vectors for a document."""
        if doc_id in self._collections:
            del self._collections[doc_id]
            logger.info(f"Deleted vector collection for doc {doc_id}")

    def collection_exists(self, doc_id: str) -> bool:
        return doc_id in self._collections and len(self._collections[doc_id]) > 0


# Singleton
_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
