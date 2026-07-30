"""
Summary service — generates abstractive summary of a document via LLM.
Uses the top-ranked chunks (by TF-IDF score) as context.
Stores result in the summaries table.
"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.db import Chunk, Summary
from services.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


SUMMARY_SYSTEM_PROMPT = """You are a document summarization expert.
Summarize the provided document excerpts into a concise, informative paragraph.
Focus on:
- The main purpose and topic of the document
- Key parties involved (if any)
- Critical obligations, risks, or important clauses
- The overall risk profile

Keep the summary to 3–5 sentences. Be factual and rely only on the provided text."""


async def generate_summary(doc_id: str, db: AsyncSession) -> str:
    """
    Select top chunks by TF-IDF score and summarize them using the LLM.
    Stores the summary in the DB and returns the summary text.
    """
    # Get top-10 chunks by tfidf_score
    result = await db.execute(
        select(Chunk)
        .where(Chunk.document_id == doc_id)
        .order_by(Chunk.tfidf_score.desc())
        .limit(10)
    )
    chunks = result.scalars().all()

    if not chunks:
        return "No content available to summarize."

    # Build context
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[Excerpt {i} — Page {chunk.page_num}]:\n{chunk.text}")
    context = "\n\n".join(context_parts)

    user_prompt = f"""Document Excerpts:
{context}

Please provide a concise summary of this document."""

    try:
        llm = get_llm_provider()
        summary_text = llm.complete(SUMMARY_SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        logger.error(f"Summary generation failed for doc {doc_id}: {e}")
        summary_text = f"Summary unavailable: {str(e)}"

    # Store in DB
    existing = await db.execute(
        select(Summary).where(Summary.document_id == doc_id)
    )
    existing_row = existing.scalar_one_or_none()

    if existing_row:
        existing_row.text = summary_text
    else:
        db.add(Summary(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            text=summary_text,
            created_at=datetime.now(timezone.utc),
        ))

    await db.commit()
    return summary_text
