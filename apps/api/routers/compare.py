from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
import logging

from services.compare_service import compare_documents

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/compare", tags=["compare"])

@router.get("/{doc1_id}/{doc2_id}")
async def compare_docs(doc1_id: str, doc2_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await compare_documents(doc1_id, doc2_id, db)
        return result
    except Exception as e:
        logger.error(f"Compare error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
