"""
Risk Classifier Service for Doc-XRay.

Two-layer classification:
1. ML Layer: TF-IDF + SGDClassifier (scikit-learn pipeline)
   prediction_source = "ml"

2. Rule-Based Override Layer: Regex patterns for high-risk legal/financial phrases
   prediction_source = "rule_override"

These two layers are explicitly kept separate. The override layer is not ML.
Do not present rule-based results as machine learning predictions.

Phase 2 Addition:
  classify() now accepts an optional `document_type` parameter.
  Per-type risk logic ensures that normal receipts/invoices are not falsely
  flagged HIGH_RISK merely because they contain words like "payment" or "fee".
  Risk must be meaningful for the specific document type.
"""
from __future__ import annotations
import re
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import joblib
import numpy as np

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent.parent / "data" / "risk_classifier.pkl"

# ──────────────────────────────────────────────
# Rule-based HIGH-RISK phrase patterns
# These apply ONLY to documents where such language is meaningful risk
# (i.e., contracts, legal docs) — see _rule_override() for type gating.
# (Deterministic — not ML)
# ──────────────────────────────────────────────
HIGH_RISK_PATTERNS = [
    r"\bindemnif",
    r"\blimitation of liability\b",
    r"\bliquidated damages?\b",
    r"\bforce majeure\b",
    r"\bdefault\b",
    r"\barbitration\b",
    r"\bforeclos",
    r"\binsolvenc",
    r"\bbankruptcy\b",
    r"\bguarantor\b",
    r"\bcollateral\b",
    r"\baccelerat(e|ion)\b",
    r"\blien\b",
    r"\bpenalt",
    r"\bwaiver of rights\b",
    r"\bnon.compete\b",
    r"\bescrow forfeiture\b",
    r"\bpunitive damages?\b",
    r"\bsubrogation\b",
    r"\brescission\b",
    r"\binjunction\b",
    r"\bpari passu\b",
    r"\bpari-passu\b",
    r"\bpoison pill\b",
    r"\bclawback\b",
    r"\bchange of control\b",
    r"\bliquidation preference\b",
    r"\birrevocably\b",
    r"\bseverally liable\b",
    r"\bremedies\b.*\bcumulative\b",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in HIGH_RISK_PATTERNS]

# ──────────────────────────────────────────────
# Document types that are "benign by nature" —
# generic financial terms should NOT trigger HIGH_RISK on these
# ──────────────────────────────────────────────
_BENIGN_BY_NATURE = {"RECEIPT", "INVOICE", "ACADEMIC", "EMAIL", "FORM", "GENERAL"}

# ──────────────────────────────────────────────
# Per-document-type risk keyword sets (context-aware, not generic)
# These are the keywords that actually matter for each document type.
# ──────────────────────────────────────────────
_DOC_TYPE_RISK_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "CONTRACT": {
        "HIGH_RISK": [
            "indemnif", "liquidated damages", "limitation of liability",
            "force majeure", "bankruptcy", "insolvency", "foreclosure",
            "arbitration", "injunction", "punitive damages", "clawback",
            "rescission", "subrogation", "pari passu", "poison pill",
            "irrevocably", "non-compete", "escrow forfeiture",
        ],
        "MEDIUM_RISK": [
            "termination", "penalty", "breach", "liability", "waiver",
            "default", "obligations", "indemnity", "confidentiality",
            "intellectual property", "governing law", "jurisdiction",
            "warranty", "representations",
        ],
    },
    "RECEIPT": {
        "HIGH_RISK": [
            # Only flag truly anomalous receipt content
            "fraud", "unauthorized transaction", "disputed charge",
            "chargeback", "counterfeit",
        ],
        "MEDIUM_RISK": [
            # Missing key fields is medium risk for receipts
        ],
    },
    "INVOICE": {
        "HIGH_RISK": [
            "overdue", "final demand", "legal action",
            "debt collection", "court proceedings",
        ],
        "MEDIUM_RISK": [
            "past due", "late payment fee", "interest charged",
            "collection agency", "credit hold",
        ],
    },
    "ACADEMIC": {
        "HIGH_RISK": [
            "academic dishonesty", "plagiarism", "expulsion",
            "suspension", "dismissed", "termination of enrollment",
        ],
        "MEDIUM_RISK": [
            "probation", "warning", "failed", "incomplete",
            "deferred", "unpaid dues",
        ],
    },
    "FORM": {
        "HIGH_RISK": [
            "rejected", "fraud", "misrepresentation",
            "false declaration", "penalty for",
        ],
        "MEDIUM_RISK": [
            "incomplete", "missing information", "required field",
            "not applicable", "pending verification",
        ],
    },
    "REPORT": {
        "HIGH_RISK": [
            "material weakness", "going concern", "restatement",
            "regulatory action", "fraud", "audit failure",
            "breach of covenant",
        ],
        "MEDIUM_RISK": [
            "significant risk", "adverse finding", "non-compliance",
            "deficit", "loss", "write-off", "impairment",
        ],
    },
    "EMAIL": {
        "HIGH_RISK": [
            "phishing", "scam", "urgent wire transfer", "account compromised",
            "verify your account", "your account will be closed",
        ],
        "MEDIUM_RISK": [
            "urgent", "deadline", "overdue", "final notice",
        ],
    },
}

# Fallback keywords for GENERAL and unknown types
_GENERAL_RISK_KEYWORDS = {
    "HIGH_RISK": [
        "breach", "penalty", "terminate", "liability", "obligation",
        "legal", "compliance", "violation", "damages", "fraud",
    ],
    "MEDIUM_RISK": [
        "risk", "warning", "dispute", "irregular", "anomaly",
    ],
}

_COMPILED_DOC_TYPE_PATTERNS: dict[str, dict[str, list[re.Pattern]]] = {
    doc_type: {
        level: [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in kws]
        for level, kws in levels.items()
    }
    for doc_type, levels in _DOC_TYPE_RISK_KEYWORDS.items()
}


# ──────────────────────────────────────────────
# Heuristic: benign document type detection (legacy — kept for compatibility)
# ──────────────────────────────────────────────
BENIGN_DOC_PATTERNS = [
    r"\bfee\s+receipt\b",
    r"\bpayment\s+receipt\b",
    r"\bpayment\s+successful\b",
    r"\bpayment\s+acknowledgement\b",
    r"\bfee\s+acknowledgement\b",
    r"\btransaction\s+id\b",
    r"\btransaction\s+no\b",
    r"\breceived\s+with\s+thanks\b",
    r"\bexam\s+fee\b",
    r"\bcollege\s+fee\b",
    r"\btuition\s+fee\b",
    r"\badmission\s+fee\b",
    r"\binvoice\s+no\b",
    r"\binvoice\s+number\b",
    r"\breceipt\s+no\b",
    r"\breceipt\s+number\b",
    r"\bpaid\s+amount\b",
    r"\bamount\s+paid\b",
    r"\bthank\s+you\s+for\s+your\s+payment\b",
]

_COMPILED_BENIGN = [re.compile(p, re.IGNORECASE) for p in BENIGN_DOC_PATTERNS]


def _is_benign_document(text: str) -> bool:
    """Return True if text looks like a receipt/invoice/acknowledgement."""
    hits = sum(1 for p in _COMPILED_BENIGN if p.search(text))
    return hits >= 2  # require at least 2 matches to be safe


@dataclass
class RiskResult:
    risk_level: str         # LOW_RISK | MEDIUM_RISK | HIGH_RISK
    risk_score: float       # 0.0–1.0 (from predict_proba for ML; 1.0 for rule override)
    prediction_source: str  # "ml" | "rule_override" | "heuristic" | "doc_type_rule"


class RiskClassifier:
    """
    Wraps the trained scikit-learn pipeline.
    Falls back to a rule-based classifier if the model file is missing.

    classify() now accepts an optional document_type parameter to apply
    context-aware risk logic per document type.
    """

    def __init__(self):
        self._pipeline = None
        self._model_loaded = False
        self._load_model()

    def _load_model(self) -> None:
        if MODEL_PATH.exists():
            try:
                self._pipeline = joblib.load(MODEL_PATH)
                self._model_loaded = True
                logger.info(f"Risk classifier model loaded from {MODEL_PATH}")
            except Exception as e:
                logger.warning(f"Could not load risk model: {e}. Rule-based fallback active.")
        else:
            logger.warning(
                f"Risk model not found at {MODEL_PATH}. "
                "Run scripts/train_risk_classifier.py to train it. "
                "Using rule-based fallback."
            )

    def _rule_override(self, text: str) -> bool:
        """Check if text matches any explicit high-risk pattern."""
        for pattern in _COMPILED_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def _doc_type_classify(self, text: str, document_type: str) -> Optional["RiskResult"]:
        """
        Apply document-type-specific risk logic.

        Returns a RiskResult if a type-specific rule fires, or None to
        fall through to ML/generic classification.
        """
        patterns = _COMPILED_DOC_TYPE_PATTERNS.get(document_type)
        if not patterns:
            return None

        # Check HIGH_RISK patterns for this doc type
        high_patterns = patterns.get("HIGH_RISK", [])
        for pattern in high_patterns:
            if pattern.search(text):
                return RiskResult(
                    risk_level="HIGH_RISK",
                    risk_score=0.90,
                    prediction_source="doc_type_rule",
                )

        # Check MEDIUM_RISK patterns for this doc type
        medium_patterns = patterns.get("MEDIUM_RISK", [])
        hits = sum(1 for p in medium_patterns if p.search(text))
        if hits >= 2:
            return RiskResult(
                risk_level="MEDIUM_RISK",
                risk_score=0.60,
                prediction_source="doc_type_rule",
            )
        if hits == 1:
            return RiskResult(
                risk_level="LOW_RISK",
                risk_score=0.20,
                prediction_source="doc_type_rule",
            )

        return None  # fall through

    def classify(self, text: str, document_type: str = "GENERAL") -> RiskResult:
        """
        Classify text into LOW_RISK | MEDIUM_RISK | HIGH_RISK.

        Priority:
        1. Heuristic: benign doc type (receipt/invoice) → always LOW_RISK
        2. Document-type-specific rules (if document_type is known)
        3. Rule override: explicit high-risk legal phrases (only for non-benign types)
        4. ML prediction (TF-IDF + SGD)
        5. Keyword fallback
        """
        # Step 0: Heuristic override — benign document types (legacy safety net)
        if document_type in _BENIGN_BY_NATURE and _is_benign_document(text):
            return RiskResult(
                risk_level="LOW_RISK",
                risk_score=0.05,
                prediction_source="heuristic",
            )

        # Step 1: Document-type-specific rules
        if document_type and document_type != "GENERAL":
            doc_type_result = self._doc_type_classify(text, document_type)
            if doc_type_result is not None:
                return doc_type_result

        # Step 2: Rule-based override (deterministic, not ML)
        # Only apply generic high-risk patterns to contract/report/general — not receipts
        if document_type not in _BENIGN_BY_NATURE:
            if self._rule_override(text):
                return RiskResult(
                    risk_level="HIGH_RISK",
                    risk_score=1.0,
                    prediction_source="rule_override",
                )

        # Step 3: ML prediction
        if self._model_loaded and self._pipeline is not None:
            try:
                proba = self._pipeline.predict_proba([text])[0]
                classes = self._pipeline.classes_
                predicted_idx = int(np.argmax(proba))
                predicted_label = classes[predicted_idx]
                confidence = float(proba[predicted_idx])

                # For benign doc types, cap at MEDIUM_RISK from ML
                if document_type in _BENIGN_BY_NATURE and predicted_label == "HIGH_RISK":
                    predicted_label = "MEDIUM_RISK"
                    confidence = min(confidence, 0.6)

                return RiskResult(
                    risk_level=predicted_label,
                    risk_score=round(confidence, 4),
                    prediction_source="ml",
                )
            except Exception as e:
                logger.error(f"ML classification failed: {e}")

        # Step 4: Fallback when no model is available — simple keyword count
        text_lower = text.lower()
        risk_keywords = [
            "breach", "penalty", "terminate", "liability", "obligation",
            "legal", "compliance", "violation", "damages", "risk",
        ]
        # For benign types, require more keyword hits before flagging
        threshold = 5 if document_type in _BENIGN_BY_NATURE else 3
        hit_count = sum(1 for kw in risk_keywords if kw in text_lower)
        if hit_count >= threshold:
            return RiskResult(risk_level="MEDIUM_RISK", risk_score=0.5, prediction_source="ml")
        return RiskResult(risk_level="LOW_RISK", risk_score=0.5, prediction_source="ml")


# Module-level singleton — loaded once at startup
_classifier: Optional[RiskClassifier] = None


def get_classifier() -> RiskClassifier:
    global _classifier
    if _classifier is None:
        _classifier = RiskClassifier()
    return _classifier
