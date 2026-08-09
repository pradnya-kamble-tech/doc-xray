"""
Compare service — compares two documents using LLM.
Retrieves top chunks from Doc A, finds semantic matches in Doc B.
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
1. Identifying if chunks are exactly the same, slightly modified, heavily modified, or novel.
2. Summarizing the changed clauses, added clauses, and removed clauses.
3. Quantifying an overall semantic similarity score (0 to 100).
4. Extracting any differences in risk or obligations.
5. Providing specific AI suggestions or alerts for the user.

OUTPUT FORMAT (JSON only! No markdown blocks, no python blocks):
{
  "similarity_score": 85,
  "changed_clauses": [
    {
      "clause": "Payment Terms",
      "diff": "Document A requires payment in 30 days, B requires 15 days.",
      "type": "MODIFICATION"
    }
  ],
  "added_clauses": ["string clause title"],
  "removed_clauses": ["string clause title"],
  "risk_difference": "Document B has a higher risk profile due to stricter penalties.",
  "ai_suggestions": ["Review the shortened payment window."]
}
"""


async def compare_documents(doc1_id: str, doc2_id: str, db: AsyncSession) -> dict:
    doc1 = (await db.execute(select(Document).where(Document.id == doc1_id))).scalar_one_or_none()
    doc2 = (await db.execute(select(Document).where(Document.id == doc2_id))).scalar_one_or_none()
    
    if not doc1 or not doc2:
        return _fallback_response("One or both documents not found.")

    result1 = await db.execute(
        select(Chunk)
        .where(Chunk.document_id == doc1_id)
        .order_by(Chunk.tfidf_score.desc())
        .limit(8)
    )
    chunks_a = result1.scalars().all()

    if not chunks_a:
        return _fallback_response("No content available in Document A to compare.")

    vector_store = get_vector_store()
    emb_service = get_embedding_service()

    context_parts = []
    
    for i, c_a in enumerate(chunks_a):
        emb_a = emb_service.encode_single(c_a.text)
        b_chunks = vector_store.query(doc2_id, emb_a, top_k=1)
        
        risk_context_a = f"[Risk: {c_a.risk_level} ({c_a.risk_score:.2f})]"
        text_a = c_a.text
        
        text_b = "No corresponding matching chunk found in Document B."
        risk_context_b = "[No match]"
        
        if b_chunks:
            match = b_chunks[0]
            if match.similarity_score > 0.4:
                text_b = match.text
                risk_context_b = f"[Risk: {match.risk_level} ({match.risk_score:.2f})]"
                
        context_parts.append(
            f"--- MATCH {i+1} ---\n"
            f"Document A {risk_context_a}:\n{text_a}\n\n"
            f"Document B {risk_context_b}:\n{text_b}\n"
        )
        
    context = "\n".join(context_parts)
    
    try:
        user_prompt = f"Matched Excerpts:\n{context}\n\nPlease provide the comparison JSON."
        llm = get_llm_provider()
        raw = llm.complete(COMPARE_SYSTEM_PROMPT, user_prompt)
        
        cleaned = re.sub(r"```(json)?\s*", "", raw).strip().rstrip("`").strip()
        data = json.loads(cleaned)
        
        return {
            "similarity_score": data.get("similarity_score", 0),
            "changed_clauses": data.get("changed_clauses", []),
            "added_clauses": data.get("added_clauses", []),
            "removed_clauses": data.get("removed_clauses", []),
            "risk_difference": data.get("risk_difference", "No significant risk difference found."),
            "ai_suggestions": data.get("ai_suggestions", [])
        }
    except Exception as e:
        logger.error(f"Comparison generation failed for {doc1_id} vs {doc2_id}: {e}")
        return _fallback_response(str(e))


def _fallback_response(reason: str = "Comparison temporarily unavailable.") -> dict:
    return {
        "similarity_score": 0,
        "changed_clauses": [],
        "added_clauses": [],
        "removed_clauses": [],
        "risk_difference": reason,
        "ai_suggestions": []
    }
