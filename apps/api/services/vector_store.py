"""
Vector Store service using ChromaDB with persistent local storage.
Each document gets its own ChromaDB collection: doc_{document_id}
"""
from __future__ import annotations
import logging
from typing import Optional
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings

from config import settings as app_settings

logger = logging.getLogger(__name__)


@dataclass
class ScoredChunk:
    chunk_id: str
    text: str
    page_num: int
    risk_level: str
    risk_score: float
    distance: float         # ChromaDB L2 distance (lower = more similar)
    similarity_score: float # Converted to 0–1 scale


class VectorStore:
    def __init__(self):
        self._client = chromadb.PersistentClient(
            path=str(app_settings.chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )

    def _collection_name(self, doc_id: str) -> str:
        # ChromaDB collection names must be valid identifiers
        return f"doc_{doc_id.replace('-', '_')}"

    def upsert_chunks(
        self,
        doc_id: str,
        chunk_ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """Store embeddings and metadata in a document-specific collection."""
        name = self._collection_name(doc_id)
        try:
            collection = self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
            collection.upsert(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            logger.info(f"Upserted {len(chunk_ids)} chunks for document {doc_id}")
        except Exception as e:
            logger.error(f"ChromaDB upsert failed for doc {doc_id}: {e}")
            raise

    def query(
        self,
        doc_id: str,
        query_embedding: list[float],
        top_k: int = 8,
    ) -> list[ScoredChunk]:
        """
        Query top-k most similar chunks for the given document.
        Returns results sorted by similarity (highest first).
        """
        name = self._collection_name(doc_id)
        try:
            collection = self._client.get_collection(name=name)
        except Exception:
            logger.warning(f"No ChromaDB collection found for doc {doc_id}")
            return []

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection.count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"ChromaDB query failed: {e}")
            return []

        chunks: list[ScoredChunk] = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, chunk_id in enumerate(ids):
            meta = metas[i] if i < len(metas) else {}
            dist = distances[i] if i < len(distances) else 1.0
            # Cosine similarity from cosine distance: similarity = 1 - distance
            similarity = max(0.0, round(1.0 - dist, 4))

            chunks.append(ScoredChunk(
                chunk_id=chunk_id,
                text=docs[i] if i < len(docs) else "",
                page_num=meta.get("page_num", 1),
                risk_level=meta.get("risk_level", "LOW_RISK"),
                risk_score=meta.get("risk_score", 0.0),
                distance=dist,
                similarity_score=similarity,
            ))

        return chunks

    def delete_collection(self, doc_id: str) -> None:
        """Delete all vectors for a document."""
        name = self._collection_name(doc_id)
        try:
            self._client.delete_collection(name=name)
            logger.info(f"Deleted ChromaDB collection: {name}")
        except Exception as e:
            logger.warning(f"Could not delete collection {name}: {e}")

    def collection_exists(self, doc_id: str) -> bool:
        try:
            self._client.get_collection(self._collection_name(doc_id))
            return True
        except Exception:
            return False


# Singleton
_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
