"""
NLP Analysis Pipeline — Deterministic, no LLM.

Components:
1. Named Entity Recognition (spaCy NER)
2. Keyword Extraction (TF-IDF on noun phrases)
3. Jargon Detection (domain wordlist + low-doc-frequency outlier)
4. Concept Detection (chunks with high entity density + top TF-IDF)

All confidence values here are either omitted or produced by the algorithm
itself (e.g., TF-IDF score). No values are fabricated.
"""
from __future__ import annotations
import logging
import re
from dataclasses import dataclass, field
from collections import Counter, defaultdict
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Domain jargon wordlist — legal / financial / technical
# (Deterministic: no ML involved)
# ──────────────────────────────────────────────
JARGON_WORDLIST = {
    # Legal
    "indemnification", "indemnify", "subrogation", "arbitration", "liquidated",
    "covenant", "fiduciary", "lien", "encumbrance", "waiver", "estoppel",
    "tortious", "promissory", "annuity", "escrow", "collateral",
    "conveyance", "easement", "injunction", "statutory", "jurisdiction",
    "jurisprudence", "pleadings", "affidavit", "deposition", "interrogatories",
    "mandamus", "certiorari", "amicus", "habeas", "corpus",
    # Financial
    "amortization", "depreciation", "ebitda", "leverage", "securitization",
    "tranches", "derivatives", "arbitrage", "hedging", "liquidity",
    "solvency", "collateralized", "subordinated", "mezzanine", "dilution",
    "accretion", "recapitalization", "syndication", "hypothecation",
    # Technical / Scientific
    "asymptotic", "stochastic", "heuristic", "ontology", "taxonomy",
    "proliferation", "pursuant", "thereto", "heretofore", "notwithstanding",
    "aforementioned", "hereinafter", "ipso", "facto", "de facto", "pro rata",
    "pari passu", "sine qua non", "prima facie", "inter alia",
}


@dataclass
class NLPAnnotation:
    type: str           # ENTITY | KEYWORD | JARGON | CONCEPT
    label: str          # spaCy entity type OR "KEYWORD", "JARGON", "CONCEPT"
    text: str
    char_start: int     # relative to chunk text
    char_end: int       # relative to chunk text
    page_num: int
    chunk_id: str = ""
    confidence: Optional[float] = None   # TF-IDF score for keywords; None otherwise


class NLPPipeline:
    def __init__(self, nlp):
        self._nlp = nlp
        self._tfidf: Optional[TfidfVectorizer] = None
        self._tfidf_scores: dict[str, float] = {}

    def fit_tfidf(self, chunk_texts: list[str]) -> None:
        """Fit TF-IDF on all chunk texts to identify important terms."""
        if not chunk_texts:
            return
        self._tfidf = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=500,
            stop_words="english",
            min_df=1,
        )
        matrix = self._tfidf.fit_transform(chunk_texts)
        # Mean TF-IDF score per term across all chunks
        scores = np.asarray(matrix.mean(axis=0)).flatten()
        terms = self._tfidf.get_feature_names_out()
        self._tfidf_scores = {term: float(scores[i]) for i, term in enumerate(terms)}

    def get_top_keywords(self, n: int = 30) -> list[str]:
        """Return top-n terms by mean TF-IDF score."""
        if not self._tfidf_scores:
            return []
        sorted_terms = sorted(self._tfidf_scores.items(), key=lambda x: x[1], reverse=True)
        return [term for term, _ in sorted_terms[:n]]

    def get_chunk_tfidf_score(self, text: str) -> float:
        """Return mean TF-IDF score for terms in a given chunk text."""
        if not self._tfidf or not self._tfidf_scores:
            return 0.0
        words = re.findall(r"\b\w+\b", text.lower())
        scores = [self._tfidf_scores.get(w, 0.0) for w in words]
        return float(np.mean(scores)) if scores else 0.0

    def analyze_chunk(
        self,
        text: str,
        page_num: int,
        chunk_id: str,
        chunk_char_offset: int = 0,
    ) -> list[NLPAnnotation]:
        """
        Run all NLP annotations on a single chunk.
        Returns a list of NLPAnnotation objects.
        char_start/char_end are relative to chunk text.
        """
        annotations: list[NLPAnnotation] = []
        doc = self._nlp(text)

        # 1. Named Entity Recognition
        seen_spans: set[tuple[int, int]] = set()
        for ent in doc.ents:
            key = (ent.start_char, ent.end_char)
            if key in seen_spans:
                continue
            seen_spans.add(key)
            annotations.append(NLPAnnotation(
                type="ENTITY",
                label=ent.label_,
                text=ent.text,
                char_start=ent.start_char,
                char_end=ent.end_char,
                page_num=page_num,
                chunk_id=chunk_id,
                confidence=None,  # spaCy NER doesn't expose per-span probability in sm model
            ))

        # 2. Keyword Detection (intersection with top TF-IDF terms)
        text_lower = text.lower()
        for keyword in self._tfidf_scores:
            if len(keyword) < 4:
                continue
            score = self._tfidf_scores[keyword]
            if score < 0.01:
                continue
            pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                span_key = (match.start(), match.end())
                if span_key in seen_spans:
                    continue
                seen_spans.add(span_key)
                annotations.append(NLPAnnotation(
                    type="KEYWORD",
                    label="KEYWORD",
                    text=match.group(),
                    char_start=match.start(),
                    char_end=match.end(),
                    page_num=page_num,
                    chunk_id=chunk_id,
                    confidence=round(score, 4),
                ))

        # 3. Jargon Detection (wordlist + low common-word filter)
        for jargon in JARGON_WORDLIST:
            pattern = re.compile(r'\b' + re.escape(jargon) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                span_key = (match.start(), match.end())
                if span_key in seen_spans:
                    continue
                seen_spans.add(span_key)
                annotations.append(NLPAnnotation(
                    type="JARGON",
                    label="JARGON",
                    text=match.group(),
                    char_start=match.start(),
                    char_end=match.end(),
                    page_num=page_num,
                    chunk_id=chunk_id,
                    confidence=None,  # Deterministic rule, not probabilistic
                ))

        # 4. Concept Detection — noun phrases with multiple entities or high TF-IDF
        entity_count = len([a for a in annotations if a.type == "ENTITY"])
        chunk_tfidf = self.get_chunk_tfidf_score(text)
        if entity_count >= 2 or chunk_tfidf > 0.05:
            for np_span in doc.noun_chunks:
                if len(np_span.text.split()) >= 2 and len(np_span.text) > 6:
                    span_key = (np_span.start_char, np_span.end_char)
                    if span_key in seen_spans:
                        continue
                    seen_spans.add(span_key)
                    annotations.append(NLPAnnotation(
                        type="CONCEPT",
                        label="CONCEPT",
                        text=np_span.text,
                        char_start=np_span.start_char,
                        char_end=np_span.end_char,
                        page_num=page_num,
                        chunk_id=chunk_id,
                        confidence=round(chunk_tfidf, 4) if chunk_tfidf > 0 else None,
                    ))

        return annotations

    def get_entity_counts(self, annotations: list[NLPAnnotation]) -> dict[str, int]:
        """Count entity types from annotation list."""
        counts: dict[str, int] = Counter(
            a.label for a in annotations if a.type == "ENTITY"
        )
        return dict(counts)
