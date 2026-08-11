"""
Document Type Classifier for Doc-XRay.

Lightweight keyword-weighted scoring approach.
No GPU or external model download required — runs on CPU using pure Python.

Supported types:
  RECEIPT, INVOICE, CONTRACT, FORM, ACADEMIC, REPORT, EMAIL, GENERAL

Returns:
  {"document_type": "...", "confidence": 0.0}

If the highest score confidence < CONFIDENCE_THRESHOLD:
  document_type = "GENERAL"

Design: Each document type has a list of weighted keyword patterns.
We compute a normalised score for each type: sum(weight for matched patterns) / total_weights.
Tiebreaking: the type with the highest normalised score wins, subject to the confidence threshold.

This is a deterministic rule-based classifier.
It is NOT ML — no model is trained or loaded.
Do not present this as a trained classifier.
"""
from __future__ import annotations
import re
import logging
import math
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────
# Confidence threshold — below this → GENERAL
# ──────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.30   # 30% of max possible score for the winning type

# ──────────────────────────────────────────────────
# Emoji labels for each document type
# ──────────────────────────────────────────────────
DOC_TYPE_EMOJIS: dict[str, str] = {
    "RECEIPT":  "🧾",
    "INVOICE":  "🧾",
    "CONTRACT": "📝",
    "FORM":     "📋",
    "ACADEMIC": "🎓",
    "REPORT":   "📊",
    "EMAIL":    "📧",
    "GENERAL":  "📄",
}

# ──────────────────────────────────────────────────
# Short explanation templates per document type
# ──────────────────────────────────────────────────
DOC_TYPE_EXPLANATIONS: dict[str, str] = {
    "RECEIPT":  "Doc-XRay identified this as a payment receipt. Risk analysis focuses on transaction completeness and amount accuracy.",
    "INVOICE":  "Doc-XRay identified this as an invoice. Risk analysis focuses on payment terms, due dates, and missing fields.",
    "CONTRACT": "Doc-XRay identified this as a legal contract. Risk analysis focuses on liability, penalty, confidentiality, and termination clauses.",
    "FORM":     "Doc-XRay identified this as a form. Risk analysis focuses on missing required fields and incomplete entries.",
    "ACADEMIC": "Doc-XRay identified this as an academic document. Risk analysis focuses on student information, fees, and key dates.",
    "REPORT":   "Doc-XRay identified this as a report. Risk analysis focuses on key entities, metrics, dates, and unusual statements.",
    "EMAIL":    "Doc-XRay identified this as an email. Standard analysis applied.",
    "GENERAL":  "Doc-XRay could not determine a specific document type with high confidence. General analysis applied.",
}

# ──────────────────────────────────────────────────
# Keyword patterns per document type
# Each entry: (pattern, weight)
# Higher weight = stronger signal
# ──────────────────────────────────────────────────
_DOC_TYPE_PATTERNS: dict[str, list[tuple[str, float]]] = {

    "RECEIPT": [
        (r"\breceipt\b",                  3.0),
        (r"\bfee\s+receipt\b",            4.0),
        (r"\bpayment\s+receipt\b",        4.0),
        (r"\bpayment\s+successful\b",     3.5),
        (r"\bpayment\s+acknowledgement\b",3.5),
        (r"\breceived\s+with\s+thanks\b", 3.0),
        (r"\btransaction\s+id\b",         3.0),
        (r"\btransaction\s+no\b",         3.0),
        (r"\btransaction\s+number\b",     3.0),
        (r"\breceipt\s+no\b",             3.0),
        (r"\breceipt\s+number\b",         3.0),
        (r"\bpaid\s+amount\b",            2.5),
        (r"\bamount\s+paid\b",            2.5),
        (r"\bthank\s+you\s+for\s+your\s+payment\b", 3.0),
        (r"\bcash\s+received\b",          2.5),
        (r"\bchange\s+due\b",             2.5),
        (r"\bsubtotal\b",                 1.5),
        (r"\btax\b",                      1.0),
        (r"\bpayment\s+method\b",         2.0),
        (r"\bcredit\s+card\b",            1.5),
        (r"\bdebit\s+card\b",             1.5),
        (r"\bupi\b",                      1.5),
        (r"\bneft\b",                     1.5),
        (r"\brtgs\b",                     1.5),
        (r"\bimps\b",                     1.5),
    ],

    "INVOICE": [
        (r"\binvoice\b",                  3.0),
        (r"\binvoice\s+no\b",             4.0),
        (r"\binvoice\s+number\b",         4.0),
        (r"\bbill\s+to\b",                3.0),
        (r"\bship\s+to\b",                2.5),
        (r"\bdue\s+date\b",               2.5),
        (r"\bpayment\s+due\b",            2.5),
        (r"\bpayment\s+terms\b",          2.5),
        (r"\bline\s+items?\b",            2.0),
        (r"\bunit\s+price\b",             2.0),
        (r"\bquantity\b",                 1.5),
        (r"\bdescription\b",              1.0),
        (r"\bsubtotal\b",                 1.5),
        (r"\btotal\s+amount\s+due\b",     3.0),
        (r"\bnet\s+\d+\s+days\b",         3.0),
        (r"\bpurchase\s+order\b",         2.0),
        (r"\bvendor\b",                   2.0),
        (r"\bclient\b",                   1.0),
        (r"\bremittance\b",               2.0),
        (r"\bbalance\s+due\b",            2.5),
        (r"\bitem\s+no\b",                1.5),
    ],

    "CONTRACT": [
        (r"\bagreement\b",                2.0),
        (r"\bthis\s+agreement\b",         3.0),
        (r"\bnon.disclosure\b",           4.0),
        (r"\bnda\b",                      4.0),
        (r"\bindemnif",                   4.0),
        (r"\blimitation\s+of\s+liability\b", 4.0),
        (r"\bliability\b",                2.5),
        (r"\bconfidential(ity)?\b",       2.5),
        (r"\btermination\b",              2.5),
        (r"\bgovernin\b",                 2.0),
        (r"\bgoverning\s+law\b",          3.0),
        (r"\bjurisdiction\b",             2.5),
        (r"\bwhereas\b",                  3.0),
        (r"\bhereinafter\b",              3.0),
        (r"\bnotwithstanding\b",          2.5),
        (r"\bforce\s+majeure\b",          3.0),
        (r"\barbitration\b",              3.0),
        (r"\bbreach\b",                   2.0),
        (r"\bobligations?\b",             2.0),
        (r"\brepresentations?\s+and\s+warranties\b", 3.5),
        (r"\bintellectual\s+property\b",  2.5),
        (r"\bproprietary\b",              2.0),
        (r"\bexecution\s+of\s+this\s+agreement\b", 3.0),
        (r"\bparties\b",                  1.5),
        (r"\bin\s+witness\s+whereof\b",   4.0),
        (r"\bsignature\b",                1.5),
    ],

    "FORM": [
        (r"\bform\b",                     2.0),
        (r"\bplease\s+fill\b",            3.0),
        (r"\bfill\s+in\b",                2.5),
        (r"\bcheck\s+(one|box)\b",        2.5),
        (r"\btick\s+applicable\b",        2.5),
        (r"\bapplicant\s+name\b",         3.0),
        (r"\bdate\s+of\s+birth\b",        2.5),
        (r"\bgender\b",                   1.5),
        (r"\baddress\b",                  1.0),
        (r"\bsignature\b",                1.5),
        (r"\bauthorized\s+by\b",          2.0),
        (r"\bfor\s+office\s+use\b",       3.5),
        (r"\brequired\s+fields?\b",       2.5),
        (r"\bsubmission\b",               1.5),
        (r"\bapplication\s+form\b",       4.0),
        (r"\benrolment\s+form\b",         4.0),
        (r"\bregistration\s+form\b",      4.0),
        (r"\byes\b.*\bno\b",              1.5),
        (r"\bcheck\s+if\s+applicable\b",  2.5),
        (r"\bfield\b",                    1.0),
    ],

    "ACADEMIC": [
        (r"\buniversity\b",               2.0),
        (r"\bcollege\b",                  2.0),
        (r"\binstitut(e|ion)\b",          2.0),
        (r"\btranscript\b",               4.0),
        (r"\bgrades?\b",                  2.0),
        (r"\bsemester\b",                 2.5),
        (r"\bacademic\s+year\b",          3.0),
        (r"\bstudent\s+(id|name|number)\b", 3.5),
        (r"\broll\s+(no|number)\b",       3.0),
        (r"\benrolment\s+no\b",           3.0),
        (r"\bcourses?\b",                 1.5),
        (r"\bsubjects?\b",                1.5),
        (r"\bexam\s+fee\b",               3.5),
        (r"\btuition\s+fee\b",            3.5),
        (r"\badmission\s+fee\b",          3.5),
        (r"\bmarks\b",                    2.0),
        (r"\bc\.g\.p\.a\b",              3.5),
        (r"\bsgpa\b",                     3.5),
        (r"\bprincipal\b",                1.5),
        (r"\bdean\b",                     2.0),
        (r"\bdiploma\b",                  2.5),
        (r"\bdegree\b",                   2.0),
        (r"\bcertificate\b",              2.0),
        (r"\bexamination\b",              2.0),
    ],

    "REPORT": [
        (r"\breport\b",                   2.0),
        (r"\bexecutive\s+summary\b",      3.5),
        (r"\btable\s+of\s+contents\b",    2.5),
        (r"\bfindings\b",                 2.5),
        (r"\brecommendations?\b",         2.5),
        (r"\banalysis\b",                 2.0),
        (r"\bmetrics?\b",                 2.0),
        (r"\bkpi\b",                      3.0),
        (r"\bquarterly\b",                2.5),
        (r"\bannual\s+(report|review)\b", 4.0),
        (r"\bforecast\b",                 2.0),
        (r"\bperformance\b",              1.5),
        (r"\bprepared\s+by\b",            1.5),
        (r"\breviewed\s+by\b",            1.5),
        (r"\bappended\b",                 1.5),
        (r"\bfigure\s+\d+\b",             2.0),
        (r"\btable\s+\d+\b",              2.0),
        (r"\bchapter\s+\d+\b",            2.0),
        (r"\bconclusion\b",               2.5),
        (r"\babstract\b",                 2.0),
        (r"\bintroduction\b",             1.5),
        (r"\bmethodology\b",              2.5),
        (r"\breferences?\b",              1.5),
    ],

    "EMAIL": [
        (r"\bfrom\s*:\b",                 3.0),
        (r"\bto\s*:\b",                   3.0),
        (r"\bcc\s*:\b",                   3.5),
        (r"\bbcc\s*:\b",                  3.5),
        (r"\bsubject\s*:\b",              3.5),
        (r"\bdear\s+\w+",                 2.0),
        (r"\bregards\b",                  2.0),
        (r"\bsincerely\b",                2.0),
        (r"\battached\s+(please|you'll)\b",2.0),
        (r"\bplease\s+find\s+attached\b", 2.5),
        (r"\bdo\s+not\s+reply\b",         2.0),
        (r"\bsent\s+from\b",              2.0),
        (r"\bforwarded\s+message\b",      3.0),
        (r"\bunsubscribe\b",              2.0),
        (r"\bfollowup\b",                 1.5),
        (r"\bkind\s+regards\b",           2.5),
        (r"\bwrote\s*:\b",                2.5),
        (r"\bin\s+reply\s+to\b",          2.0),
    ],
}


@dataclass
class ClassificationResult:
    document_type: str
    confidence: float
    emoji: str
    explanation: str


def _precompile() -> dict[str, list[tuple[re.Pattern, float]]]:
    compiled: dict[str, list[tuple[re.Pattern, float]]] = {}
    for doc_type, patterns in _DOC_TYPE_PATTERNS.items():
        compiled[doc_type] = [
            (re.compile(pat, re.IGNORECASE), weight)
            for pat, weight in patterns
        ]
    return compiled


_COMPILED_PATTERNS = _precompile()

# Total possible weight per type (sum of all weights)
_MAX_WEIGHTS: dict[str, float] = {
    doc_type: sum(w for _, w in patterns)
    for doc_type, patterns in _DOC_TYPE_PATTERNS.items()
}


def classify_document(text: str) -> ClassificationResult:
    """
    Classify a document into one of the supported types.

    Parameters
    ----------
    text : str
        Full document text (concatenated from all pages).

    Returns
    -------
    ClassificationResult
        document_type, confidence (0.0–1.0), emoji, explanation.
    """
    if not text or not text.strip():
        return ClassificationResult(
            document_type="GENERAL",
            confidence=0.0,
            emoji=DOC_TYPE_EMOJIS["GENERAL"],
            explanation=DOC_TYPE_EXPLANATIONS["GENERAL"],
        )

    scores: dict[str, float] = {}
    for doc_type, pat_list in _COMPILED_PATTERNS.items():
        raw_score = sum(weight for pattern, weight in pat_list if pattern.search(text))
        max_possible = _MAX_WEIGHTS[doc_type]
        # Normalise against a soft cap of 60% of max weights for realistic scores
        soft_cap = max_possible * 0.60
        normalised = min(raw_score / soft_cap, 1.0) if soft_cap > 0 else 0.0
        scores[doc_type] = normalised

    # Pick best
    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]

    logger.info(f"Document classification scores: {scores}")
    logger.info(f"Best type: {best_type} (confidence={best_score:.3f})")

    if best_score < CONFIDENCE_THRESHOLD:
        return ClassificationResult(
            document_type="GENERAL",
            confidence=round(best_score, 4),
            emoji=DOC_TYPE_EMOJIS["GENERAL"],
            explanation=DOC_TYPE_EXPLANATIONS["GENERAL"],
        )

    return ClassificationResult(
        document_type=best_type,
        confidence=round(best_score, 4),
        emoji=DOC_TYPE_EMOJIS.get(best_type, "📄"),
        explanation=DOC_TYPE_EXPLANATIONS.get(best_type, DOC_TYPE_EXPLANATIONS["GENERAL"]),
    )
