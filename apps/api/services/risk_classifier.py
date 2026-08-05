"""
Risk Classifier Service for Doc-XRay.

Two-layer classification:
1. ML Layer: TF-IDF + SGDClassifier (scikit-learn pipeline)
   prediction_source = "ml"

2. Rule-Based Override Layer: Regex patterns for high-risk legal/financial phrases
   prediction_source = "rule_override"

These two layers are explicitly kept separate. The override layer is not ML.
Do not present rule-based results as machine learning predictions.
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
# Rule-based high-risk phrase patterns
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
# Heuristic: benign document type detection
# Receipts, invoices, fee acknowledgements → LOW_RISK
# (Runs BEFORE ML and rule override)
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
    prediction_source: str  # "ml" | "rule_override" | "heuristic"


class RiskClassifier:
    """
    Wraps the trained scikit-learn pipeline.
    Falls back to a rule-based classifier if the model file is missing.
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

    def classify(self, text: str) -> RiskResult:
        """
        Classify text into LOW_RISK | MEDIUM_RISK | HIGH_RISK.

        Priority:
        1. Heuristic: benign doc type (receipt/invoice) → always LOW_RISK
        2. Rule override: explicit high-risk legal phrases
        3. ML prediction (TF-IDF + SGD)
        4. Keyword fallback
        """
        # Step 0: Heuristic override — benign document types
        if _is_benign_document(text):
            return RiskResult(
                risk_level="LOW_RISK",
                risk_score=0.05,
                prediction_source="heuristic",
            )

        # Step 1: Rule-based override (deterministic, not ML)
        if self._rule_override(text):
            return RiskResult(
                risk_level="HIGH_RISK",
                risk_score=1.0,
                prediction_source="rule_override",
            )

        # Step 2: ML prediction
        if self._model_loaded and self._pipeline is not None:
            try:
                proba = self._pipeline.predict_proba([text])[0]
                classes = self._pipeline.classes_
                predicted_idx = int(np.argmax(proba))
                predicted_label = classes[predicted_idx]
                confidence = float(proba[predicted_idx])
                return RiskResult(
                    risk_level=predicted_label,
                    risk_score=round(confidence, 4),
                    prediction_source="ml",
                )
            except Exception as e:
                logger.error(f"ML classification failed: {e}")

        # Step 3: Fallback when no model is available — simple keyword count
        text_lower = text.lower()
        risk_keywords = [
            "breach", "penalty", "terminate", "liability", "obligation",
            "legal", "compliance", "violation", "damages", "risk",
        ]
        hit_count = sum(1 for kw in risk_keywords if kw in text_lower)
        if hit_count >= 3:
            return RiskResult(risk_level="MEDIUM_RISK", risk_score=0.5, prediction_source="ml")
        return RiskResult(risk_level="LOW_RISK", risk_score=0.5, prediction_source="ml")


# Module-level singleton — loaded once at startup
_classifier: Optional[RiskClassifier] = None


def get_classifier() -> RiskClassifier:
    global _classifier
    if _classifier is None:
        _classifier = RiskClassifier()
    return _classifier
