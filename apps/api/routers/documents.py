"""
Document router: upload, list, get, delete.
"""
from __future__ import annotations
import uuid
import os
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from db.database import get_db
from models.db import Document, Chunk, Annotation, Summary
from models.schemas import DocumentOut, DocumentListOut
from config import settings
from services.analysis_pipeline import run_analysis_pipeline
from services.vector_store import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_SIZE_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # ── Validate ──────────────────────────────────────────
    if not file.filename:
        raise HTTPException(400, "No filename provided.")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read content and validate size
    content = await file.read()
    if len(content) > MAX_SIZE_BYTES:
        raise HTTPException(
            413,
            f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
        )
    if len(content) == 0:
        raise HTTPException(400, "Uploaded file is empty.")

    # ── Save file ─────────────────────────────────────────
    doc_id = str(uuid.uuid4())
    safe_name = f"{doc_id}{ext}"
    save_path = settings.upload_dir / safe_name

    try:
        save_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(500, f"Could not save file: {e}")

    # ── Create DB record ──────────────────────────────────
    doc = Document(
        id=doc_id,
        filename=safe_name,
        original_filename=file.filename,
        file_path=str(save_path),
        file_size=len(content),
        mime_type=file.content_type or "",
        status="PENDING",
        current_stage="Queued",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # ── Trigger background pipeline ───────────────────────
    background_tasks.add_task(run_analysis_pipeline, doc_id, str(save_path))

    logger.info(f"Document uploaded: {file.filename} ({doc_id})")
    return doc


@router.get("/", response_model=DocumentListOut)
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return DocumentListOut(documents=list(docs), total=len(docs))


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found.")
    return doc


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found.")

    # Delete file from disk
    try:
        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.warning(f"Could not delete file {doc.file_path}: {e}")

    # Delete ChromaDB collection
    try:
        get_vector_store().delete_collection(doc_id)
    except Exception as e:
        logger.warning(f"Could not delete ChromaDB collection for {doc_id}: {e}")

    # Delete DB records (cascades to chunks/annotations/summaries)
    await db.delete(doc)
    await db.commit()

    return {"message": f"Document {doc_id} deleted successfully."}
