"""
Explain router: RAG-based explanation of highlighted spans.
"""
from __future__ import annotations
import logging

from fastapi import APIRouter, HTTPException

from models.schemas import ExplainRequest, ExplainOut
from services.rag_service import explain_span

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/explain", tags=["explain"])


@router.post("/", response_model=ExplainOut)
async def explain(request: ExplainRequest):
    if not request.span_text.strip():
        raise HTTPException(400, "span_text cannot be empty.")

    if len(request.span_text) > 2000:
        raise HTTPException(400, "span_text too long (max 2000 characters).")

    try:
        result = await explain_span(
            doc_id=request.doc_id,
            span_text=request.span_text,
            chunk_id=request.chunk_id,
            annotation_type=request.annotation_type,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        logger.error(f"Explain endpoint error: {e}", exc_info=True)
        raise HTTPException(500, f"Internal error: {e}")
