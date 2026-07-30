# Doc-XRay - Project Status

## Status Overview
The Doc-XRay platform MVP has been completely scaffolded with the backend architecture, AI pipeline, frontend shell, and UI viewer application.

### 1. Features Completed
- ✅ Initial Next.js 14 Framework
- ✅ Next.js Tailwind & Framer Motion Integration
- ✅ FastAPI Backend Scaffolding
- ✅ PyMuPDF / python-docx Document Ingestion logic
- ✅ SQLite / SQLAlchemy Persistent Data Layer
- ✅ NLP SpaCy Chunking and Sentence Boundary Detection
- ✅ Embedding Models (using `sentence-transformers`) Setup
- ✅ Advanced UI interactive viewer component structure

### 2. Features partially completed
- 🚧 RAG generation prompt tuning (Requires valid LLM endpoint connection)
- 🚧 End-to-end full deployment sequence due to Python 3.8 limitations on ML binaries

### 3. Features not implemented
- ❌ OpenAI/Fallback integrations handling (currently prioritizes Gemini as requested)

## AI / ML Architecture Summary

**4. AI components**
- `google-genai` abstractions implemented.
 
**5. ML components**
- `SGDClassifier` implemented with `scikit-learn` in `analysis_pipeline.py`. Supports rule-based logic overlays.
 
**6. NLP components**
- `spaCy` NER and TF-IDF implementation running in core backend extraction pipeline. 
 
**7. Embedding system**
- Local `sentence-transformers/all-MiniLM-L6-v2` bindings created in `analysis_pipeline.py`.
 
**8. Vector database**
- `chromadb` client successfully wrapped. 
 
**9. RAG system**
- Retrieval architecture set up in backend orchestration logic (`run_analysis_pipeline`).

**10. LLM provider**
- Google Gemini via standard AI library.

## Known Limitations & Environment Requirements
**CRITICAL:** The target development environment uses Python 3.8 without Visual C++ Build Tools. Modern versions of `tokenizers` and `transformers` do not bundle Python 3.8 Windows wheels natively.
**Recommendation:** Upgrade your python installation to `Python 3.10` or higher to use the pre-built application endpoints perfectly.

## Exact Commands to Run

### Run Backend
```bash
cd apps/api
# Assumes Python 3.10+
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Run Frontend
```bash
cd apps/web
npm install
npm run dev
```

### Train ML
```bash
cd apps/api
python scripts/train_risk_classifier.py
```

*Note: The repository was successfully verified and synced with GitHub.*
