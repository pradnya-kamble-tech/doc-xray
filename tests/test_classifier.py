"""
Unit tests for Doc-XRay document_classifier.py and risk_classifier.py.

Tests covering:
1. Receipt classification
2. Invoice classification
3. Contract classification
4. Academic document classification
5. General (unclassified) document

Run with:
    cd apps/api
    venv\\Scripts\\python.exe -m pytest ../../tests/test_classifier.py -v
"""
import sys
import os

# Add apps/api to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))

from pathlib import Path

DOCS_DIR = Path(__file__).parent / "test_documents"


def _load(filename: str) -> str:
    return (DOCS_DIR / filename).read_text(encoding="utf-8")


# ═══════════════════════════════════════════
# document_classifier tests
# ═══════════════════════════════════════════

def test_classify_receipt():
    from services.document_classifier import classify_document
    result = classify_document(_load("receipt_sample.txt"))
    assert result.document_type == "RECEIPT", (
        f"Expected RECEIPT, got {result.document_type} (confidence={result.confidence})"
    )
    assert result.confidence >= 0.30, f"Confidence too low: {result.confidence}"
    assert result.emoji == "🧾"
    assert result.explanation  # not empty


def test_classify_invoice():
    from services.document_classifier import classify_document
    result = classify_document(_load("invoice_sample.txt"))
    assert result.document_type == "INVOICE", (
        f"Expected INVOICE, got {result.document_type} (confidence={result.confidence})"
    )
    assert result.confidence >= 0.30


def test_classify_contract():
    from services.document_classifier import classify_document
    result = classify_document(_load("contract_sample.txt"))
    assert result.document_type == "CONTRACT", (
        f"Expected CONTRACT, got {result.document_type} (confidence={result.confidence})"
    )
    assert result.confidence >= 0.30


def test_classify_academic():
    from services.document_classifier import classify_document
    result = classify_document(_load("academic_sample.txt"))
    assert result.document_type == "ACADEMIC", (
        f"Expected ACADEMIC, got {result.document_type} (confidence={result.confidence})"
    )
    assert result.confidence >= 0.30


def test_classify_general():
    from services.document_classifier import classify_document
    result = classify_document(_load("general_sample.txt"))
    # General text should either be GENERAL or at least have low confidence
    # (ISRO news article — no strong signals for any specific type)
    assert result.document_type == "GENERAL" or result.confidence < 0.50, (
        f"Expected GENERAL or low confidence, got {result.document_type} ({result.confidence})"
    )


def test_classify_empty_text():
    from services.document_classifier import classify_document
    result = classify_document("")
    assert result.document_type == "GENERAL"
    assert result.confidence == 0.0


# ═══════════════════════════════════════════
# risk_classifier tests (document-type-aware)
# ═══════════════════════════════════════════

def test_risk_receipt_is_low():
    """A normal receipt should not be HIGH_RISK."""
    from services.risk_classifier import get_classifier
    clf = get_classifier()
    result = clf.classify(_load("receipt_sample.txt"), document_type="RECEIPT")
    assert result.risk_level != "HIGH_RISK", (
        f"Receipt should not be HIGH_RISK (got {result.risk_level}, source={result.prediction_source})"
    )


def test_risk_contract_with_indemnification():
    """A contract with indemnification should be HIGH_RISK."""
    from services.risk_classifier import get_classifier
    clf = get_classifier()
    text = _load("contract_sample.txt")
    result = clf.classify(text, document_type="CONTRACT")
    # Contract contains "indemnif", "limitation of liability", "termination"
    assert result.risk_level in ("HIGH_RISK", "MEDIUM_RISK"), (
        f"Contract with legal clauses should be HIGH or MEDIUM risk (got {result.risk_level})"
    )


def test_risk_general_document():
    """A general news article should not be HIGH_RISK."""
    from services.risk_classifier import get_classifier
    clf = get_classifier()
    result = clf.classify(_load("general_sample.txt"), document_type="GENERAL")
    assert result.risk_level != "HIGH_RISK", (
        f"General news article should not be HIGH_RISK (got {result.risk_level})"
    )


def test_risk_result_has_source():
    """RiskResult should always have a non-empty prediction_source."""
    from services.risk_classifier import get_classifier
    clf = get_classifier()
    result = clf.classify("Some random text without any keywords.", document_type="GENERAL")
    assert result.prediction_source in ("ml", "rule_override", "heuristic", "doc_type_rule")

# ═══════════════════════════════════════════
# type_extractor tests
# ═══════════════════════════════════════════

def test_extract_receipt_info():
    from services.type_extractor import extract_document_intelligence
    text = _load("receipt_sample.txt")
    result = extract_document_intelligence(text, "RECEIPT")
    data, actions = result["extracted_data"], result["recommended_actions"]
    assert "Total Amount" in data
    assert "Date" in data
    assert len(actions) > 0
    assert any("receipt" in a.lower() or "expense" in a.lower() for a in actions)

def test_extract_contract_info():
    from services.type_extractor import extract_document_intelligence
    text = _load("contract_sample.txt")
    result = extract_document_intelligence(text, "CONTRACT")
    data, actions = result["extracted_data"], result["recommended_actions"]
    assert len(actions) > 0
    assert any("indemnification" in a.lower() for a in actions)

def test_extract_invoice_info():
    from services.type_extractor import extract_document_intelligence
    text = _load("invoice_sample.txt")
    result = extract_document_intelligence(text, "INVOICE")
    data, actions = result["extracted_data"], result["recommended_actions"]
    assert "Invoice No" in data
    assert len(actions) > 0

