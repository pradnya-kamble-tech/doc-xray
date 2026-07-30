"""
Analysis router: get analysis results and SSE status stream.
"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from models.db import Document, Chunk, Annotation, Summary
from models.schemas import AnalysisOut, AnnotationOut, ChunkOut
from services.analysis_pipeline import (
    get_status_history,
    subscribe_to_status,
    unsubscribe_from_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/{doc_id}", response_model=AnalysisOut)
async def get_analysis(doc_id: str, db: AsyncSession = Depends(get_db)):
    # Get document
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found.")

    # Get chunks
    chunks_result = await db.execute(
        select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.page_num, Chunk.char_start)
    )
    chunks = chunks_result.scalars().all()

    # Get annotations
    ann_result = await db.execute(
        select(Annotation).where(Annotation.document_id == doc_id).order_by(Annotation.char_start)
    )
    annotations = ann_result.scalars().all()

    # Get summary
    sum_result = await db.execute(
        select(Summary).where(Summary.document_id == doc_id)
    )
    summary_row = sum_result.scalar_one_or_none()

    # Build keyword list from KEYWORD annotations (deduplicated, top 30)
    keywords = list(dict.fromkeys(
        ann.text.lower() for ann in annotations if ann.type == "KEYWORD"
    ))[:30]

    # Entity counts
    entity_counts: dict[str, int] = {}
    for ann in annotations:
        if ann.type == "ENTITY":
            entity_counts[ann.label] = entity_counts.get(ann.label, 0) + 1

    # Risk counts
    risk_counts = {"HIGH_RISK": 0, "MEDIUM_RISK": 0, "LOW_RISK": 0}
    for chunk in chunks:
        level = chunk.risk_level or "LOW_RISK"
        risk_counts[level] = risk_counts.get(level, 0) + 1

    return AnalysisOut(
        document_id=doc_id,
        status=doc.status,
        page_count=doc.page_count or 0,
        summary=summary_row.text if summary_row else None,
        keywords=keywords,
        annotations=[
            AnnotationOut(
                id=ann.id,
                chunk_id=ann.chunk_id,
                type=ann.type,
                label=ann.label,
                text=ann.text,
                char_start=ann.char_start,
                char_end=ann.char_end,
                confidence=ann.confidence,
                page_num=ann.page_num,
            )
            for ann in annotations
        ],
        chunks=[
            ChunkOut(
                id=c.id,
                page_num=c.page_num,
                text=c.text,
                char_start=c.char_start,
                char_end=c.char_end,
                risk_level=c.risk_level or "LOW_RISK",
                risk_score=c.risk_score or 0.0,
                prediction_source=c.prediction_source or "ml",
                tfidf_score=c.tfidf_score or 0.0,
            )
            for c in chunks
        ],
        entity_counts=entity_counts,
        risk_counts=risk_counts,
    )


@router.get("/{doc_id}/status")
async def analysis_status_stream(doc_id: str):
    """
    SSE endpoint — streams processing stage events.
    Client receives: data: {"stage": "...", "percent": 50, "message": "..."}
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        # Send past events first (for late subscribers)
        history = get_status_history(doc_id)
        for event in history:
            yield f"data: {json.dumps(event)}\n\n"

        if history and history[-1].get("stage") in ("Done", "Failed"):
            return  # Pipeline already finished

        q = subscribe_to_status(doc_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield "data: {\"stage\": \"heartbeat\", \"percent\": -1, \"message\": \"waiting...\"}\n\n"
                    continue

                if event is None:  # Sentinel from pipeline
                    break

                yield f"data: {json.dumps(event)}\n\n"

                if event.get("stage") in ("Done", "Failed"):
                    break
        finally:
            unsubscribe_from_status(doc_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
