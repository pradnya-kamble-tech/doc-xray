"""
Search router: semantic search over document chunks using ChromaDB.
"""
from __future__ import annotations
import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from models.schemas import SearchRequest, SearchResponse, SearchResultOut
from services.embedding_service import get_embedding_service
from services.vector_store import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    if not request.query.strip():
        raise HTTPException(400, "Query cannot be empty.")

    if request.top_k < 1 or request.top_k > 20:
        raise HTTPException(400, "top_k must be between 1 and 20.")

    # Encode the query
    embedding_svc = get_embedding_service()
    query_vector = embedding_svc.encode_single(request.query)

    # Query ChromaDB
    vector_store = get_vector_store()
    if not vector_store.collection_exists(request.doc_id):
        raise HTTPException(
            404,
            f"No vector index found for document {request.doc_id}. "
            "Ensure processing has completed."
        )

    results = vector_store.query(
        doc_id=request.doc_id,
        query_embedding=query_vector,
        top_k=request.top_k,
    )

    return SearchResponse(
        results=[
            SearchResultOut(
                chunk_id=r.chunk_id,
                text=r.text,
                page_num=r.page_num,
                similarity_score=r.similarity_score,
                risk_level=r.risk_level,
                risk_score=r.risk_score,
            )
            for r in results
        ],
        query=request.query,
        total=len(results),
    )
