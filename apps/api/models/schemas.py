"""Pydantic request/response schemas for Doc-XRay API."""
from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


# ──────────────────────────────────────────────
# Document schemas
# ──────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    status: str
    current_stage: Optional[str] = None
    error_message: Optional[str] = None
    page_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListOut(BaseModel):
    documents: list[DocumentOut]
    total: int


# ──────────────────────────────────────────────
# Annotation schemas
# ──────────────────────────────────────────────

class AnnotationOut(BaseModel):
    id: str
    chunk_id: str
    type: str           # ENTITY | KEYWORD | JARGON | RISK | CONCEPT
    label: str          # e.g. "ORG", "HIGH_RISK", "FINANCIAL_TERM"
    text: str
    char_start: int
    char_end: int
    confidence: Optional[float] = None   # null if not naturally produced
    page_num: int

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Chunk schemas
# ──────────────────────────────────────────────

class ChunkOut(BaseModel):
    id: str
    page_num: int
    text: str
    char_start: int
    char_end: int
    risk_level: str
    risk_score: float
    prediction_source: str   # "ml" | "rule_override"
    tfidf_score: float

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Analysis schemas
# ──────────────────────────────────────────────

class AnalysisOut(BaseModel):
    document_id: str
    status: str
    page_count: int
    summary: Optional[str] = None
    keywords: list[str] = []
    annotations: list[AnnotationOut] = []
    chunks: list[ChunkOut] = []
    entity_counts: dict[str, int] = {}
    risk_counts: dict[str, int] = {}


class StatusEvent(BaseModel):
    stage: str
    percent: int
    message: str


# ──────────────────────────────────────────────
# Search schemas
# ──────────────────────────────────────────────

class SearchRequest(BaseModel):
    doc_id: str
    query: str
    top_k: int = 8


class SearchResultOut(BaseModel):
    chunk_id: str
    text: str
    page_num: int
    similarity_score: float
    risk_level: str
    risk_score: float


class SearchResponse(BaseModel):
    results: list[SearchResultOut]
    query: str
    total: int


# ──────────────────────────────────────────────
# Explain schemas
# ──────────────────────────────────────────────

class ExplainRequest(BaseModel):
    doc_id: str
    chunk_id: str
    span_text: str
    annotation_type: Optional[str] = None


class SourceChunk(BaseModel):
    chunk_id: str
    text: str
    page_num: int
    similarity_score: float


class ExplainOut(BaseModel):
    explanation: str
    simplified_explanation: str
    risk_level: str
    confidence: Optional[float] = None   # only if meaningfully derived
    source_chunks: list[SourceChunk] = []
    source_pages: list[int] = []
    provider: str  # which LLM provider was used


# ──────────────────────────────────────────────
# Chat schemas
# ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class ChatSourceOut(BaseModel):
    page: int
    chunk_id: str
    similarity: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSourceOut]
