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

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/pradnya-kamble-tech/doc-xray.git
   ```
2. **Navigate to the project**
   ```bash
   cd doc-xray
   ```
3. **Create Python 3.11 virtual environment**
   ```bash
   cd apps/api
   python -m venv venv
   ```
4. **Activate the virtual environment**
   ```bash
   .\venv\Scripts\activate
   ```
5. **Install backend dependencies**
   ```bash
   pip install -r requirements.txt
   ```
6. **Configure apps/api/.env**
   Copy `.env.example` to `.env` and fill in your Gemini API Key.
   ```env
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=your_gemini_api_key_here
   OPENAI_API_KEY=
   ```
   > **WARNING:** Do not commit your `.env` file. Only `.env.example` should be committed.

7. **Train the ML risk classifier**
   ```bash
   python scripts/train_risk_classifier.py
   ```
8. **Start the FastAPI backend**
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   > You can verify the backend is running by checking the health URL:
   > http://localhost:8000/api/health
   > It should return exactly: `{"status":"ok"}`

9. **Open a second terminal** (for the frontend)
   ```bash
   cd apps/web
   ```
10. **Start the Next.js frontend**
    ```bash
    npm install
    npm run dev
    ```
11. **Open http://localhost:3000** in your browser.

## AI/ML Pipeline

- **spaCy** → NER and NLP feature engineering.
- **TF-IDF + SGDClassifier** → Traditional ML risk classification pipeline.
- **Sentence Transformers** → Dense embeddings (`all-MiniLM-L6-v2`).
- **ChromaDB** → Local vector storage and fast semantic search.
- **RAG** → Retrieves relevant document context dynamically.
- **Gemini** → Grounded, hallucination-free explanation generation.

Please refer to `PROJECT_STATUS.md` and `ARCHITECTURE.md` for extended documentation on the system logic and local module structure.
