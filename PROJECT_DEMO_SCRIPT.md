# Doc-XRay: Project Demo Script

This script provides a 5-minute flow for presenting the Doc-XRay platform.

## 1. Context & Problem (30s)
*   **The Problem:** Legal and financial analysts spend countless hours reading verbose documents, trying to identify risk, jargons, and specific entities.
*   **The Solution:** Doc-XRay, an AI-powered visual document intelligence platform. It automates reading, highlights key insights deterministically, classifies risk via Machine Learning, and allows semantic communication with the document using RAG.


## 2. Platform Overview (30s)
*   Show the main landing page.
*   Highlight the drag-and-drop feature and supported formats (PDF/DOCX).

## 3. The Extraction Process (1m)
*   **Action:** Upload a sample `risk_training_data.csv` based PDF or a sample high-risk contract.
*   **Talking points:** Watch the progress indicators.
    *   **Text Extraction:** Reading the structural content of the PDF.
    *   **NLP Pipeline:** spaCy breaks text into semantic chunks and identifies Named Entities.
    *   **ML Pipeline:** A custom-trained Scikit-Learn TF-IDF model scores each chunk for Risk.
    *   **Embedding Pipeline:** We use local MiniLM embeddings to convert chunks into vectors and store them in ChromaDB.

## 4. The Interactive Canvas (1m 30s)
*   **Action:** Open the uploaded document inside the Viewer.
*   **Talking points:**
    *   Notice the visual highlights: Red for Risk, Yellow for Jargon, Blue for Entities, Green for Key Info.
    *   This is not a black-box AI model highlighting randomly—these are deterministic NLP and traditional ML outputs.

## 5. RAG & Intelligent Explainability (1m)
*   **Action:** Click on a red (High Risk) highlighted chunk to open the Explainer Panel.
*   **Talking points:**
    *   The Explainer panel opens.
    *   We use Semantic Search + RAG. The user can ask questions, or the panel can explain the highlighted text using the Gemini LLM.
    *   Show that the LLM is citing specific page numbers and *only* answering based on retrieved chunk context (No Hallucination).

## 6. Closing & Future Roadmap (30s)
*   Review how the dual AI architecture (Local ML/NLP + Generative AI) ensures auditability and reduces hallucination risk.
*   **Future Improvements:** Optical Character Recognition (OCR) for scanned PDFs, multi-document semantic search, fine-tuned LLaMA local model fallback.
