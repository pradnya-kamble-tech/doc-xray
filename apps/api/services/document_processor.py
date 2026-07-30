"""
Document processor for PDF and DOCX files.
Uses PyMuPDF for PDFs and python-docx for DOCX.
Returns a list of PageText objects preserving page number and text.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PageText:
    page_num: int   # 1-indexed
    text: str


def extract_pdf(file_path: Path) -> list[PageText]:
    """Extract text from every page of a PDF using PyMuPDF."""
    import fitz  # PyMuPDF

    pages: list[PageText] = []
    try:
        doc = fitz.open(str(file_path))
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text.strip():
                pages.append(PageText(page_num=i, text=text))
        doc.close()
    except Exception as e:
        logger.error(f"PDF extraction failed for {file_path}: {e}")
        raise ValueError(f"Could not extract text from PDF: {e}") from e
    return pages


def extract_docx(file_path: Path) -> list[PageText]:
    """
    Extract text from a DOCX file.
    DOCX has no hard page breaks, so we approximate pages by grouping
    every 40 paragraphs as one logical "page".
    """
    from docx import Document as DocxDocument

    PARAS_PER_PAGE = 40
    pages: list[PageText] = []
    try:
        doc = DocxDocument(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        for i in range(0, max(len(paragraphs), 1), PARAS_PER_PAGE):
            page_num = (i // PARAS_PER_PAGE) + 1
            chunk_paras = paragraphs[i:i + PARAS_PER_PAGE]
            text = "\n".join(chunk_paras)
            if text.strip():
                pages.append(PageText(page_num=page_num, text=text))
    except Exception as e:
        logger.error(f"DOCX extraction failed for {file_path}: {e}")
        raise ValueError(f"Could not extract text from DOCX: {e}") from e
    return pages


def extract_document(file_path: Path) -> tuple[list[PageText], int]:
    """
    Detect file type and extract text.
    Returns (pages, page_count).
    """
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        pages = extract_pdf(file_path)
    elif suffix in (".docx", ".doc"):
        pages = extract_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    page_count = len(pages)
    return pages, page_count
