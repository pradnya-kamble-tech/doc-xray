"""
Doc-XRay FastAPI application entry point.
Configures CORS, mounts all routers, and initializes DB and services on startup.
"""
import logging
import os
import sys
from contextlib import asynccontextmanager

# Ensure apps/api directory is in sys.path
api_dir = os.path.dirname(os.path.abspath(__file__))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all services on startup."""
    logger.info("=== Doc-XRay API starting ===")

    # Initialize database
    try:
        from db.database import init_db
        await init_db()
        logger.info("SQLite database initialized.")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")

    # Pre-load embedding model
    try:
        from services.embedding_service import get_embedding_service
        get_embedding_service()
        logger.info("Embedding model loaded.")
    except Exception as e:
        logger.warning(f"Embedding model pre-load failed: {e}")

    # Pre-load spaCy model
    try:
        from services.analysis_pipeline import _get_nlp
        _get_nlp()
        logger.info("spaCy model loaded.")
    except Exception as e:
        logger.warning(f"spaCy pre-load failed: {e}")

    # Pre-load risk classifier
    try:
        from services.risk_classifier import get_classifier
        get_classifier()
        logger.info("Risk classifier loaded.")
    except Exception as e:
        logger.warning(f"Risk classifier pre-load failed: {e}")

    logger.info("=== Doc-XRay API ready ===")
    yield
    logger.info("=== Doc-XRay API shutting down ===")


app = FastAPI(
    title="Doc-XRay API",
    description="AI-Powered Visual Document Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

from config import settings

# CORS — allow Next.js dev server and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        settings.frontend_url,
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
from routers import documents, analysis, search, explain, chat, compare

app.include_router(documents.router)
app.include_router(analysis.router)
app.include_router(search.router)
app.include_router(explain.router)
app.include_router(chat.router)
app.include_router(compare.router)


@app.get("/api/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "doc-xray-api", "version": "1.0.0"}
