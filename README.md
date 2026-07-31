# Doc-XRay: AI-Powered Visual Document Intelligence Platform

Doc-XRay is an advanced document processing platform utilizing Natural Language Processing (NLP), Machine Learning (ML), and Large Language Models (LLM) to perform complex analysis, entity extraction, and risk classification on PDFs and DOCX files.

## Project Execution Workflow

The complete end-to-end execution flow of the system runs precisely in this order:

```text
Python 3.11 (Required for dependency wheels)
    ↓
Create venv
    ↓
Install dependencies (pip install -r requirements.txt)
    ↓
Add Gemini API key to .env
    ↓
Train risk classifier (train_risk_classifier.py)
    ↓
Start FastAPI (uvicorn)
    ↓
Start Next.js (npm run dev)
    ↓
Open localhost:3000
    ↓
Upload PDF/DOCX
    ↓
NLP + NER (spaCy)
    ↓
ML Risk Classification (Scikit-Learn SGDClassifier)
    ↓
Embeddings (HuggingFace sentence-transformers)
    ↓
ChromaDB (Local vector storage)
    ↓
RAG (Retrieval-Augmented Generation)
    ↓
Gemini Explanation (Final Output)
```

## Setup Instructions
Please refer to `PROJECT_STATUS.md` and `ARCHITECTURE.md` for extended documentation on the system logic and local module structure.
