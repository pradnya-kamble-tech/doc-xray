"""SQLAlchemy ORM models for Doc-XRay."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mime_type: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    # PENDING | PROCESSING | DONE | FAILED
    current_stage: Mapped[str] = mapped_column(String, nullable=True, default="")
    error_message: Mapped[str] = mapped_column(Text, nullable=True, default="")
    page_count: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    # Document type classification (added in phase 2 upgrade)
    document_type: Mapped[str] = mapped_column(String, nullable=True, default="GENERAL")
    doc_type_confidence: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    chunks: Mapped[list["Chunk"]] = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    annotations: Mapped[list["Annotation"]] = relationship("Annotation", back_populates="document", cascade="all, delete-orphan")
    summaries: Mapped[list["Summary"]] = relationship("Summary", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"), nullable=False)
    page_num: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tfidf_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    risk_level: Mapped[str] = mapped_column(String, nullable=True, default="LOW_RISK")
    risk_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    prediction_source: Mapped[str] = mapped_column(String, nullable=True, default="ml")
    # "ml" | "rule_override"
    chroma_id: Mapped[str] = mapped_column(String, nullable=True, default="")

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    annotations: Mapped[list["Annotation"]] = relationship("Annotation", back_populates="chunk", cascade="all, delete-orphan")


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id: Mapped[str] = mapped_column(String, ForeignKey("chunks.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    # ENTITY | KEYWORD | JARGON | RISK | CONCEPT
    label: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    page_num: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    document: Mapped["Document"] = relationship("Document", back_populates="annotations")
    chunk: Mapped["Chunk"] = relationship("Chunk", back_populates="annotations")


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped["Document"] = relationship("Document", back_populates="summaries")
