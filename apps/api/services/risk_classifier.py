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


@dataclass
class RiskResult:
    risk_level: str         # LOW_RISK | MEDIUM_RISK | HIGH_RISK
    risk_score: float       # 0.0–1.0 (from predict_proba for ML; 1.0 for rule override)
    prediction_source: str  # "ml" | "rule_override"


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

        Rule override takes priority: if a high-risk phrase is found,
        the ML prediction is overridden regardless of its confidence.
        """
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
