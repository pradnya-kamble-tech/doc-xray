"""
Semantic chunker using spaCy sentence segmentation.
Groups sentences into chunks of approximately 300 tokens.
Tracks character offsets across the full document text.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

TARGET_TOKENS = 300
APPROX_TOKEN_CHARS = 5  # rough chars-per-token estimate for splitting


@dataclass
class TextChunk:
    text: str
    page_num: int
    char_start: int
    char_end: int
    token_count: int = 0


def chunk_pages(pages: list, nlp) -> list[TextChunk]:
    """
    Split page texts into semantic chunks using spaCy sentence segmentation.
    'pages' is a list of PageText(page_num, text).
    Returns a flat list of TextChunk objects with absolute char offsets.
    """
    chunks: list[TextChunk] = []
    global_offset = 0  # tracks position in the concatenated full-doc string

    for page in pages:
        text = page.text
        page_num = page.page_num

        # Parse with spaCy to get sentence boundaries
        doc = nlp(text[:1000000])  # guard against huge pages
        sentences = list(doc.sents)

        current_sents: list[str] = []
        current_tokens = 0
        current_start = global_offset

        for sent in sentences:
            sent_text = sent.text.strip()
            if not sent_text:
                continue

            sent_tokens = len(sent)

            # If adding this sentence exceeds target, flush current chunk
            if current_tokens + sent_tokens > TARGET_TOKENS and current_sents:
                joined = " ".join(current_sents)
                chunks.append(TextChunk(
                    text=joined,
                    page_num=page_num,
                    char_start=current_start,
                    char_end=current_start + len(joined),
                    token_count=current_tokens,
                ))
                current_start = current_start + len(joined) + 1
                current_sents = []
                current_tokens = 0

            current_sents.append(sent_text)
            current_tokens += sent_tokens

        # Flush remaining sentences
        if current_sents:
            joined = " ".join(current_sents)
            chunks.append(TextChunk(
                text=joined,
                page_num=page_num,
                char_start=current_start,
                char_end=current_start + len(joined),
                token_count=current_tokens,
            ))

        # Advance global offset by page text length + separator
        global_offset += len(text) + 1

    return chunks
