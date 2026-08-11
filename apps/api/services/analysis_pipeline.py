"""
Analysis Pipeline Orchestrator.
Runs in a background thread after document upload.
Stages: Extracting → Chunking → NLP → Classifying → Embedding → LLM Summary → Done
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from typing import Any

import spacy
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from db.database import AsyncSessionLocal
from models.db import Document, Chunk, Annotation
from models.schemas import StatusEvent
from services.document_processor import extract_document, PageText
from services.chunker import chunk_pages, TextChunk
from services.nlp_pipeline import NLPPipeline, NLPAnnotation
from services.risk_classifier import get_classifier
from services.embedding_service import get_embedding_service
from services.vector_store import get_vector_store
from services.summary_service import generate_summary
from services.document_classifier import classify_document, ClassificationResult

logger = logging.getLogger(__name__)

# In-memory status store: doc_id → list of StatusEvent dicts
_status_store: dict[str, list[dict]] = {}
_status_subscribers: dict[str, list[asyncio.Queue]] = {}

# Load spaCy model once
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        logger.info("Loading spaCy model: en_core_web_sm")
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def get_status_history(doc_id: str) -> list[dict]:
    return _status_store.get(doc_id, [])


def subscribe_to_status(doc_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _status_subscribers.setdefault(doc_id, []).append(q)
    return q


def unsubscribe_from_status(doc_id: str, q: asyncio.Queue) -> None:
    subs = _status_subscribers.get(doc_id, [])
    if q in subs:
        subs.remove(q)


async def _emit_status(doc_id: str, stage: str, percent: int, message: str) -> None:
    event = StatusEvent(stage=stage, percent=percent, message=message).model_dump()
    _status_store.setdefault(doc_id, []).append(event)
    for q in list(_status_subscribers.get(doc_id, [])):
        try:
            await q.put(event)
        except Exception:
            pass


async def _update_document_status(
    db: AsyncSession, doc_id: str, status: str, stage: str = "", error: str = ""
) -> None:
    await db.execute(
        update(Document)
        .where(Document.id == doc_id)
        .values(status=status, current_stage=stage, error_message=error)
    )
    await db.commit()


async def run_analysis_pipeline(doc_id: str, file_path: str) -> None:
    """
    Full analysis pipeline. Runs as a FastAPI BackgroundTask.
    Each stage emits a status event consumed by SSE endpoint.
    """
    from pathlib import Path

    async with AsyncSessionLocal() as db:
        try:
            await _update_document_status(db, doc_id, "PROCESSING", "Extracting")

            # ── Stage 1: Extract ──────────────────────────────────────
            await _emit_status(doc_id, "Extracting", 10, "Extracting text from document...")
            pages, page_count = extract_document(Path(file_path))

            if not pages:
                raise ValueError("No text could be extracted from this document.")

            # ── Stage 1b: Classify Document Type ─────────────────────────
            full_text = "\n".join(p.text for p in pages)
            doc_classification: ClassificationResult = classify_document(full_text)
            logger.info(
                f"Document {doc_id} classified as {doc_classification.document_type} "
                f"(confidence={doc_classification.confidence:.3f})"
            )

            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(
                    page_count=page_count,
                    document_type=doc_classification.document_type,
                    doc_type_confidence=doc_classification.confidence,
                )
            )
            await db.commit()

            # ── Stage 2: Chunk ────────────────────────────────────────
            await _emit_status(doc_id, "Chunking", 25, f"Splitting {page_count} pages into semantic chunks...")
            nlp = _get_nlp()
            text_chunks: list[TextChunk] = chunk_pages(pages, nlp)

            if not text_chunks:
                raise ValueError("Document produced no processable chunks.")

            # ── Stage 3: NLP ──────────────────────────────────────────
            await _emit_status(doc_id, "NLP", 40, f"Running NLP analysis on {len(text_chunks)} chunks...")
            nlp_pipeline = NLPPipeline(nlp)

            # Fit TF-IDF across all chunks first
            all_chunk_texts = [c.text for c in text_chunks]
            nlp_pipeline.fit_tfidf(all_chunk_texts)
            keywords = nlp_pipeline.get_top_keywords(n=30)

            # Persist chunks and run NLP
            db_chunks: list[Chunk] = []
            all_annotations: list[NLPAnnotation] = []

            for tc in text_chunks:
                chunk_id = str(uuid.uuid4())
                tfidf_score = nlp_pipeline.get_chunk_tfidf_score(tc.text)

                db_chunk = Chunk(
                    id=chunk_id,
                    document_id=doc_id,
                    page_num=tc.page_num,
                    text=tc.text,
                    char_start=tc.char_start,
                    char_end=tc.char_end,
                    token_count=tc.token_count,
                    tfidf_score=tfidf_score,
                )
                db.add(db_chunk)
                db_chunks.append(db_chunk)

                chunk_annotations = nlp_pipeline.analyze_chunk(
                    text=tc.text,
                    page_num=tc.page_num,
                    chunk_id=chunk_id,
                    chunk_char_offset=tc.char_start,
                )
                all_annotations.extend(chunk_annotations)

            await db.commit()

            # ── Stage 4: Risk Classification ──────────────────────────
            await _emit_status(doc_id, "Classifying", 60, "Running risk classification...")
            classifier = get_classifier()

            for db_chunk, tc in zip(db_chunks, text_chunks):
                result = classifier.classify(tc.text, document_type=doc_classification.document_type)
                await db.execute(
                    update(Chunk)
                    .where(Chunk.id == db_chunk.id)
                    .values(
                        risk_level=result.risk_level,
                        risk_score=result.risk_score,
                        prediction_source=result.prediction_source,
                    )
                )

                # Create a RISK annotation for high/medium risk chunks
                if result.risk_level in ("HIGH_RISK", "MEDIUM_RISK"):
                    db.add(Annotation(
                        id=str(uuid.uuid4()),
                        chunk_id=db_chunk.id,
                        document_id=doc_id,
                        type="RISK",
                        label=result.risk_level,
                        text=tc.text[:200],  # preview of the risky text
                        char_start=tc.char_start,
                        char_end=min(tc.char_start + 200, tc.char_end),
                        confidence=result.risk_score,
                        page_num=tc.page_num,
                    ))

            await db.commit()

            # Persist NLP annotations
            for ann in all_annotations:
                # Translate chunk-relative offsets to document-relative offsets
                chunk_offset = 0
                for db_chunk, tc in zip(db_chunks, text_chunks):
                    if db_chunk.id == ann.chunk_id:
                        chunk_offset = tc.char_start
                        break

                db.add(Annotation(
                    id=str(uuid.uuid4()),
                    chunk_id=ann.chunk_id,
                    document_id=doc_id,
                    type=ann.type,
                    label=ann.label,
                    text=ann.text,
                    char_start=ann.char_start + chunk_offset,
                    char_end=ann.char_end + chunk_offset,
                    confidence=ann.confidence,
                    page_num=ann.page_num,
                ))

            await db.commit()

            # ── Stage 5: Embeddings ───────────────────────────────────
            await _emit_status(doc_id, "Embedding", 75, "Generating semantic embeddings...")
            embedding_svc = get_embedding_service()
            vector_store = get_vector_store()

            # Reload chunks with risk data
            from sqlalchemy import select
            result_q = await db.execute(
                select(Chunk).where(Chunk.document_id == doc_id)
            )
            final_chunks = result_q.scalars().all()

            chunk_ids = [c.id for c in final_chunks]
            chunk_texts = [c.text for c in final_chunks]
            embeddings = embedding_svc.encode(chunk_texts)

            metadatas = [
                {
                    "document_id": doc_id,
                    "chunk_id": c.id,
                    "page_num": c.page_num,
                    "risk_level": c.risk_level or "LOW_RISK",
                    "risk_score": c.risk_score or 0.0,
                }
                for c in final_chunks
            ]

            vector_store.upsert_chunks(doc_id, chunk_ids, chunk_texts, embeddings, metadatas)

            # Update chroma_id on chunks
            for c in final_chunks:
                await db.execute(
                    update(Chunk).where(Chunk.id == c.id).values(chroma_id=c.id)
                )
            await db.commit()

            # ── Stage 6: Summary ──────────────────────────────────────
            await _emit_status(doc_id, "Summarizing", 88, "Generating document summary with AI...")
            try:
                await generate_summary(doc_id, db)
            except Exception as e:
                logger.warning(f"Summary generation failed (non-fatal): {e}")

            # ── Done ──────────────────────────────────────────────────
            await _update_document_status(db, doc_id, "DONE", "Done")
            await _emit_status(doc_id, "Done", 100, "Analysis complete!")

            # Send sentinel to close SSE subscribers
            for q in list(_status_subscribers.get(doc_id, [])):
                try:
                    await q.put(None)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Pipeline failed for doc {doc_id}: {e}", exc_info=True)
            await _update_document_status(db, doc_id, "FAILED", "Failed", str(e))
            await _emit_status(doc_id, "Failed", 0, f"Error: {str(e)}")
            for q in list(_status_subscribers.get(doc_id, [])):
                try:
                    await q.put(None)
                except Exception:
                    pass
