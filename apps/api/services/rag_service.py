"""
RAG Service — Retrieval-Augmented Generation for Doc-XRay.

Flow:
1. Encode span_text with embedding model
2. Retrieve top-k semantically similar chunks from ChromaDB (same document)
3. Build a grounded system + user prompt
4. Call LLM (default: Gemini)
5. Return structured ExplainOut

The LLM is explicitly instructed to:
- Only use provided document context
- Cite source pages
- State when context is insufficient
- Not invent facts
"""
from __future__ import annotations
import logging
import json
import re

from models.schemas import ExplainOut, SourceChunk
from services.embedding_service import get_embedding_service
from services.vector_store import get_vector_store, ScoredChunk
from services.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are Doc-XRay, an expert document analyst.

Your task is to explain a highlighted term or clause from the provided document context.

RULES:
1. Only use information from the provided document context.
2. If the context does not contain enough information, explicitly say "The provided context does not contain sufficient information about this term."
3. Never invent facts, statistics, or legal interpretations not present in the context.
4. Clearly distinguish between what the document says (fact) and your interpretation.
5. Always cite the source page number(s) from the context.
6. Provide both a detailed expert explanation AND a simplified plain-language explanation.

RESPONSE FORMAT (JSON only, no markdown code blocks):
{
  "explanation": "Detailed explanation grounded in the document context...",
  "simplified_explanation": "Plain language version for non-experts...",
  "risk_assessment": "Based on the context, this represents [LOW/MEDIUM/HIGH] risk because...",
  "source_pages": [1, 2],
  "context_sufficient": true
}"""


def _parse_llm_response(raw: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    # Strip markdown code block if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: extract the JSON object
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    # If all parsing fails, return the raw text as explanation
    return {
        "explanation": raw,
        "simplified_explanation": raw[:300] + "..." if len(raw) > 300 else raw,
        "risk_assessment": "Unable to determine",
        "source_pages": [],
        "context_sufficient": False,
    }


def _extract_risk_level(risk_assessment: str) -> str:
    assessment_upper = risk_assessment.upper()
    if "HIGH" in assessment_upper:
        return "HIGH_RISK"
    elif "MEDIUM" in assessment_upper:
        return "MEDIUM_RISK"
    return "LOW_RISK"


async def explain_span(
    doc_id: str,
    span_text: str,
    chunk_id: str,
    annotation_type: str | None = None,
) -> ExplainOut:
    """
    Core RAG function:
    1. Embed the span text
    2. Retrieve relevant context from ChromaDB
    3. Build grounded prompt
    4. Call LLM
    5. Return structured response
    """
    embedding_svc = get_embedding_service()
    vector_store = get_vector_store()

    # Step 1: Embed the query span
    query_embedding = embedding_svc.encode_single(span_text)

    # Step 2: Retrieve top-5 relevant chunks restricted to this document
    similar_chunks: list[ScoredChunk] = vector_store.query(
        doc_id=doc_id,
        query_embedding=query_embedding,
        top_k=5,
    )

    if not similar_chunks:
        return ExplainOut(
            explanation="No document context could be retrieved for this term. Please ensure the document has been fully processed.",
            simplified_explanation="No context found.",
            risk_level="LOW_RISK",
            confidence=None,
            source_chunks=[],
            source_pages=[],
            provider="none",
        )

    # Step 3: Build context block
    context_lines = []
    for i, chunk in enumerate(similar_chunks, 1):
        context_lines.append(f"[Context {i} — Page {chunk.page_num}]:\n{chunk.text}")
    context_block = "\n\n".join(context_lines)

    # Step 4: Build user prompt
    user_prompt = f"""Document Context:
{context_block}

Highlighted Text to Explain:
"{span_text}"

Annotation Type: {annotation_type or "UNKNOWN"}

Please provide your JSON analysis."""

    # Step 5: Call LLM
    llm = get_llm_provider()
    try:
        raw_response = llm.complete(SYSTEM_PROMPT, user_prompt)
        parsed = _parse_llm_response(raw_response)
    except Exception as e:
        logger.error(f"LLM call failed in RAG explain: {e}")
        return ExplainOut(
            explanation=f"LLM service unavailable: {str(e)}. Check your API key configuration.",
            simplified_explanation="AI explanation service is currently unavailable.",
            risk_level="LOW_RISK",
            confidence=None,
            source_chunks=[],
            source_pages=[],
            provider=llm.provider_name if hasattr(llm, 'provider_name') else "unknown",
        )

    # Step 6: Build response
    source_chunk_objs = [
        SourceChunk(
            chunk_id=c.chunk_id,
            text=c.text[:300] + "..." if len(c.text) > 300 else c.text,
            page_num=c.page_num,
            similarity_score=c.similarity_score,
        )
        for c in similar_chunks
    ]

    source_pages = list(set(parsed.get("source_pages", [c.page_num for c in similar_chunks])))
    source_pages.sort()

    risk_assessment = parsed.get("risk_assessment", "")
    risk_level = _extract_risk_level(risk_assessment)

    return ExplainOut(
        explanation=parsed.get("explanation", raw_response),
        simplified_explanation=parsed.get("simplified_explanation", ""),
        risk_level=risk_level,
        confidence=None,  # Not fabricated — LLM doesn't produce calibrated confidence
        source_chunks=source_chunk_objs,
        source_pages=source_pages,
        provider=llm.provider_name,
    )
