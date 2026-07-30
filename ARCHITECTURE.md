# Doc-XRay Architecture

## System Diagram
The Doc-XRay MVP relies on two primary applications:
1. **Frontend**: Next.js App Router (React, Tailwind, Framer Motion)
2. **Backend**: FastAPI (Python 3)

## Flow
1. **Upload**: User drags-and-drops PDF/DOCX to Next.js. Next.js pushes to FastAPI.
2. **Extraction**: FastAPI decodes PDF (PyMuPDF) or word document (python-docx).
3. **NLP**: spaCy segments text into Chunks and runs NER.
4. **Classification**: Pre-trained scikit-learn models run Risk detection on Chunks.
5. **Vectorizing**: `all-MiniLM-L6-v2` executes locally to encode Chunks.
6. **Storage**: Text structure and Risk data is stored in SQLite (SQLAlchemy 2). Vectors are stored in local ChromaDB.
7. **RAG Explanation**: When the user clicks an annotation on the Frontend, Next.js calls a RAG endpoint. The Backend retrieves K-Nearest Neighbors from ChromaDB and builds a semantic prompt for the Gemini LLM.

## Abstractions
- **Databases**: SQLite (Relational structure) + ChromaDB (Semantic structures)
- **Providers**: `LLMProvider` is an abstract interface allowing Gemini to be swapped for OpenAI without breaking the application logic.

## Security
- No GenAI fake stats. All scores presented on the UI are directly correlated to the scikit-learn probability arrays or rule-overrides. If the LLM generates a summary, it is stringently tied directly to the closest ChromaDB chunks, reducing the Hallucination probability.
