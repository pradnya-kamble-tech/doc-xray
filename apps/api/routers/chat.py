from __future__ import annotations
import logging

from fastapi import APIRouter, HTTPException

from models.schemas import ChatRequest, ChatResponse
from services.rag_service import chat_with_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{document_id}", response_model=ChatResponse)
async def chat(document_id: str, request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(400, "message cannot be empty.")

    if len(request.message) > 2000:
        raise HTTPException(400, "message too long (max 2000 characters).")

    try:
        result = await chat_with_document(
            doc_id=document_id,
            message=request.message,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(500, f"Internal error: {e}")
