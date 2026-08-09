"""
Compare service — compares two documents using LLM.
Retrieves top chunks from Doc A, finds semantic matches in Doc B,
calculates real vector-based similarity, and outputs structured differences.
"""
from __future__ import annotations
import logging
import json
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.db import Document, Chunk
from services.vector_store import get_vector_store
from services.embedding_service import get_embedding_service
from services.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)

COMPARE_SYSTEM_PROMPT = """You are an expert legal AI document analysis engine.
You are given matched text chunks from two documents (Document A and Document B).
Your task is to compare them and produce a structured JSON report.
Be highly analytical, concise, and accurate. Do not hallucinate.

Focus on:
1. Categorizing diffs into ADDED, REMOVED, or MODIFIED.
2. Providing a clear short title/clause name.
3. Describing the specific difference.
4. Keeping track of the source chunk_id and page for each document referenced in that clause.

OUTPUT FORMAT (JSON only! No markdown blocks):
{
  "differences": [
    {
      "type": "MODIFIED",
      "clause": "Payment Terms",
      "description": "Document A requires 30 days, B requires 15 days.",
      "sources": [
        {"doc": "A", "page": 1, "chunk_id": "abc-123"},
        {"doc": "B", "page": 1, "chunk_id": "xyz-987"}
      ]
    },
    {
      "type": "ADDED",
      "clause": "Confidentiality",
      "description": "Document B added a new 5-year NDA clause.",
      "sources": [
         {"doc": "B", "page": 2, "chunk_id": "bbb-444"}
      ]
    }
  ],
  "ai_suggestions": ["Review the shortened payment window.", "Ensure NDA aligns with standard policy."]
}
"""

async def compare_documents(doc1_id: str, doc2_id: str, db: AsyncSession) -> dict:
    doc1 = (await db.execute(select(Document).where(Document.id == doc1_id))).scalar_one_or_none()
    doc2 = (await db.execute(select(Document).where(Document.id == doc2_id))).scalar_one_or_none()
    
    if not doc1 or not doc2:
        return _fallback_response("One or both documents not found.")

    # 1. Fetch chunks for both to assess risk profiles
    chunks_1 = (await db.execute(select(Chunk).where(Chunk.document_id == doc1_id))).scalars().all()
    chunks_2 = (await db.execute(select(Chunk).where(Chunk.document_id == doc2_id))).scalars().all()

    if not chunks_1:
        return _fallback_response("No content available in Document A to compare.")
        
    def aggregate_risk(chunks: list[Chunk]) -> dict:
        if not chunks:
            return {"level": "UNKNOWN", "score": 0.0}
        max_score = max(c.risk_score for c in chunks)
        # Determine highest risk level
        levels = [c.risk_level for c in chunks]
        if "HIGH_RISK" in levels:
            overall = "HIGH_RISK"
        elif "MEDIUM_RISK" in levels:
            overall = "MEDIUM_RISK"
        else:
            overall = "LOW_RISK"
        return {"level": overall, "score": max_score}

    doc_a_risk = aggregate_risk(chunks_1)
    doc_b_risk = aggregate_risk(chunks_2)
    
    # 2. Select Top chunks from A for semantic comparison
    # Choose top 10 by tfidf_score or if very small, all chunks
    sorted_a = sorted(chunks_1, key=lambda c: c.tfidf_score or 0.0, reverse=True)[:10]

    vector_store = get_vector_store()
    emb_service = get_embedding_service()

    context_parts = []
    total_similarity = 0.0
    matched_count = 0
    
    for i, c_a in enumerate(sorted_a):
        emb_a = emb_service.encode_single(c_a.text)
        b_chunks = vector_store.query(doc2_id, emb_a, top_k=1)
        
        text_a = c_a.text
        text_b = "No corresponding matching chunk found in Document B."
        match_chunk_id = "none"
        match_page_num = 0
        
        if b_chunks:
            match = b_chunks[0]
            # Accumulate vector based similarity score (cosine based, 0 to 1)
            total_similarity += match.similarity_score
            matched_count += 1
            
            # If similarity is decently high it's a structural match
            if match.similarity_score > 0.3:
                text_b = match.text
                match_chunk_id = match.chunk_id
                match_page_num = match.page_num
                
        context_parts.append(
            f"--- MATCH {i+1} ---\n"
            f"Document A [chunk_id: {c_a.id}, page: {c_a.page_num}]:\n{text_a}\n\n"
            f"Document B [chunk_id: {match_chunk_id}, page: {match_page_num}]:\n{text_b}\n"
        )
        
    context = "\n".join(context_parts)
    
    avg_similarity = (total_similarity / matched_count) if matched_count > 0 else 0.0
    real_similarity_score = round(avg_similarity * 100)
    
    try:
        user_prompt = f"Matched Excerpts:\n{context}\n\nPlease provide the JSON diff."
        llm = get_llm_provider()
        raw = llm.complete(COMPARE_SYSTEM_PROMPT, user_prompt)
        
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        data = json.loads(cleaned)
        
        differences = data.get("differences", [])
        ai_suggestions = data.get("ai_suggestions", [])
        
        return {
            "similarity_score": real_similarity_score,
            "doc_a_risk": doc_a_risk,
            "doc_b_risk": doc_b_risk,
            "differences": differences,
            "ai_suggestions": ai_suggestions,
            "error_msg": None
        }
    except Exception as e:
        logger.error(f"Comparison generation failed for {doc1_id} vs {doc2_id}: {e}")
        fallback = _fallback_response(f"Generation failed: {str(e)}")
        # Still return calculated similarity & risks
        fallback["similarity_score"] = real_similarity_score
        fallback["doc_a_risk"] = doc_a_risk
        fallback["doc_b_risk"] = doc_b_risk
        return fallback


def _fallback_response(reason: str = "Comparison temporarily unavailable.") -> dict:
    return {
        "similarity_score": 0,
        "doc_a_risk": {"level": "UNKNOWN", "score": 0.0},
        "doc_b_risk": {"level": "UNKNOWN", "score": 0.0},
        "differences": [],
        "ai_suggestions": [],
        "error_msg": reason
    }
