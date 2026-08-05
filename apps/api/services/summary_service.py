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
        summary_text = "Summary temporarily unavailable — please try again"

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


ACTION_ITEMS_SYSTEM_PROMPT = """You are a document analysis assistant.
Given the document excerpts below, extract a concise list of important things the reader should know or act on.

RULES:
1. Use only information from the provided excerpts.
2. Be concise — 3 to 7 bullet items maximum.
3. Each item must be one short sentence (plain language, no jargon).
4. Start each item with a relevant emoji (✓, ⚠, 📄, 💰, 📅, 👤, 🔴, etc.)
5. Do NOT include legal interpretations not stated in the document.

RESPONSE FORMAT (JSON only, no markdown):
{"items": ["✓ Payment of ₹29,120 received", "📅 Exam: December 2026", ...]}"""


async def generate_action_items(doc_id: str, db: AsyncSession) -> list[str]:
    """
    Select top chunks and generate a bullet list of actionable insights.
    Returns list of short strings.
    """
    result = await db.execute(
        select(Chunk)
        .where(Chunk.document_id == doc_id)
        .order_by(Chunk.tfidf_score.desc())
        .limit(8)
    )
    chunks = result.scalars().all()
    if not chunks:
        return []

    context_parts = [f"[Excerpt {i} — Page {c.page_num}]:\n{c.text}" for i, c in enumerate(chunks, 1)]
    context = "\n\n".join(context_parts)
    user_prompt = f"Document Excerpts:\n{context}\n\nPlease provide the action items JSON."

    try:
        import json, re
        llm = get_llm_provider()
        raw = llm.complete(ACTION_ITEMS_SYSTEM_PROMPT, user_prompt)
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        data = json.loads(cleaned)
        items = data.get("items", [])
        return [str(i) for i in items if i]
    except Exception as e:
        logger.error(f"Action items generation failed for doc {doc_id}: {e}")
        return []

