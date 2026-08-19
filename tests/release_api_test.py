"""
Release API integration tests for Doc-XRay.
Tests upload, analysis, chat, compare, history via HTTP API.
"""
import json
import sys
import time
from pathlib import Path

import httpx

API_BASE = "http://localhost:8000"
DOCS_DIR = Path(__file__).parent / "test_documents"
TEST_PDFS = [
    ("test_receipt.pdf", "RECEIPT"),
    ("test_invoice.pdf", "INVOICE"),
    ("test_contract.pdf", "CONTRACT"),
    ("test_academic.pdf", "ACADEMIC"),
    ("test_general.pdf", "GENERAL"),
]
TIMEOUT = 180
POLL_INTERVAL = 2


def wait_for_done(client: httpx.Client, doc_id: str) -> dict:
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        r = client.get(f"{API_BASE}/api/documents/{doc_id}")
        r.raise_for_status()
        doc = r.json()
        status = doc.get("status")
        if status == "DONE":
            return doc
        if status == "FAILED":
            raise RuntimeError(f"Document {doc_id} failed: {doc.get('error_message')}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Document {doc_id} did not reach DONE within {TIMEOUT}s")


def verify_analysis(analysis: dict, expected_type: str | None = None) -> list[str]:
    errors = []
    if analysis.get("status") != "DONE":
        errors.append(f"status={analysis.get('status')}, expected DONE")
    if not analysis.get("document_type"):
        errors.append("missing document_type")
    elif expected_type and analysis["document_type"] != expected_type:
        errors.append(
            f"document_type={analysis['document_type']}, expected {expected_type}"
        )
    if not analysis.get("risk_level"):
        errors.append("missing risk_level")
    if analysis.get("summary") is None:
        errors.append("missing summary")
    if not analysis.get("chunks"):
        errors.append("no chunks")
    if analysis.get("key_information") is None:
        errors.append("missing key_information")
    return errors


def main() -> int:
    results = {"passed": [], "failed": [], "skipped": []}
    uploaded_ids: dict[str, str] = {}

    with httpx.Client(timeout=120.0) as client:
        # Health
        try:
            r = client.get(f"{API_BASE}/api/health")
            r.raise_for_status()
            assert r.json().get("status") == "ok"
            results["passed"].append("health_check")
        except Exception as e:
            results["failed"].append(f"health_check: {e}")
            print(json.dumps(results, indent=2))
            return 1

        # Upload + analysis for each PDF
        for pdf_name, expected_type in TEST_PDFS:
            test_key = f"upload_{pdf_name}"
            pdf_path = DOCS_DIR / pdf_name
            if not pdf_path.exists():
                results["skipped"].append(f"{test_key}: file missing")
                continue
            try:
                with pdf_path.open("rb") as f:
                    r = client.post(
                        f"{API_BASE}/api/documents/upload",
                        files={"file": (pdf_name, f, "application/pdf")},
                    )
                r.raise_for_status()
                doc = r.json()
                doc_id = doc["id"]
                uploaded_ids[pdf_name] = doc_id

                wait_for_done(client, doc_id)

                r = client.get(f"{API_BASE}/api/analysis/{doc_id}")
                r.raise_for_status()
                analysis = r.json()
                errs = verify_analysis(analysis, expected_type)
                if errs:
                    results["failed"].append(f"{test_key}: " + "; ".join(errs))
                else:
                    results["passed"].append(
                        f"{test_key} (type={analysis['document_type']}, risk={analysis['risk_level']})"
                    )
            except Exception as e:
                results["failed"].append(f"{test_key}: {e}")

        # History (list documents)
        try:
            r = client.get(f"{API_BASE}/api/documents/")
            r.raise_for_status()
            data = r.json()
            if data.get("total", 0) < 1:
                results["failed"].append("history: no documents in list")
            else:
                results["passed"].append(f"history_list ({data['total']} docs)")
        except Exception as e:
            results["failed"].append(f"history: {e}")

        # Chat tests (use receipt doc if available)
        doc_id = uploaded_ids.get("test_receipt.pdf") or next(iter(uploaded_ids.values()), None)
        if doc_id:
            try:
                r = client.post(
                    f"{API_BASE}/api/chat/{doc_id}",
                    json={"message": "What is the total amount on this document?"},
                )
                r.raise_for_status()
                chat = r.json()
                if not chat.get("answer"):
                    results["failed"].append("chat_doc_question: empty answer")
                else:
                    results["passed"].append("chat_doc_question")
            except Exception as e:
                results["failed"].append(f"chat_doc_question: {e}")

            try:
                r = client.post(
                    f"{API_BASE}/api/chat/{doc_id}",
                    json={"message": "What is the capital of France?"},
                )
                r.raise_for_status()
                chat = r.json()
                if not chat.get("answer"):
                    results["failed"].append("chat_unrelated_question: empty answer")
                else:
                    results["passed"].append("chat_unrelated_question")
            except Exception as e:
                results["failed"].append(f"chat_unrelated_question: {e}")
        else:
            results["skipped"].append("chat: no uploaded doc")

        # Explain test
        if doc_id:
            try:
                r = client.get(f"{API_BASE}/api/analysis/{doc_id}")
                analysis = r.json()
                chunks = analysis.get("chunks") or []
                if chunks:
                    chunk = chunks[0]
                    span = chunk["text"][: min(40, len(chunk["text"]))]
                    r = client.post(
                        f"{API_BASE}/api/explain/",
                        json={
                            "doc_id": doc_id,
                            "chunk_id": chunk["id"],
                            "span_text": span,
                        },
                    )
                    r.raise_for_status()
                    explain = r.json()
                    if not explain.get("explanation"):
                        results["failed"].append("explain: empty explanation")
                    else:
                        results["passed"].append("explain_span")
                else:
                    results["skipped"].append("explain: no chunks")
            except Exception as e:
                results["failed"].append(f"explain: {e}")

        # Compare two documents
        id_a = uploaded_ids.get("test_contract.pdf")
        id_b = uploaded_ids.get("test_receipt.pdf")
        if id_a and id_b:
            try:
                r = client.get(f"{API_BASE}/api/compare/{id_a}/{id_b}")
                r.raise_for_status()
                compare = r.json()
                if compare.get("error_msg"):
                    results["failed"].append(f"compare: {compare['error_msg']}")
                elif "similarity_score" not in compare:
                    results["failed"].append("compare: missing similarity_score")
                else:
                    results["passed"].append(
                        f"compare (similarity={compare.get('similarity_score')})"
                    )
            except Exception as e:
                results["failed"].append(f"compare: {e}")
        else:
            results["skipped"].append("compare: missing doc ids")

    print("\n=== RELEASE API TEST RESULTS ===")
    print(f"PASSED ({len(results['passed'])}):")
    for p in results["passed"]:
        print(f"  ✓ {p}")
    print(f"FAILED ({len(results['failed'])}):")
    for f in results["failed"]:
        print(f"  ✗ {f}")
    print(f"SKIPPED ({len(results['skipped'])}):")
    for s in results["skipped"]:
        print(f"  - {s}")

    return 1 if results["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
