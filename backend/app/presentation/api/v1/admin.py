from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from uuid import UUID

from app.core.dependencies import get_rag_ingestion_service, get_property_repository
from app.application.services.rag_service import RAGIngestionService
from app.domain.repositories import PropertyRepository
import logging

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


@router.post("/reindex")
async def reindex_all_properties(
    background_tasks: BackgroundTasks,
    ingestion_service: RAGIngestionService = Depends(get_rag_ingestion_service),
):
    async def _reindex():
        try:
            result = await ingestion_service.reindex_all()
            logger.info(f"Reindex completed: {result}")
        except Exception as e:
            logger.error(f"Reindex failed: {e}")

    background_tasks.add_task(_reindex)
    return {"status": "Reindexing started in background"}


@router.post("/properties/{property_id}/reindex")
async def reindex_single_property(
    property_id: UUID,
    ingestion_service: RAGIngestionService = Depends(get_rag_ingestion_service),
    property_repo: PropertyRepository = Depends(get_property_repository),
):
    prop = await property_repo.get(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    count = await ingestion_service.ingest_property(prop)
    return {"property_id": str(property_id), "chunks_created": count}


@router.post("/vector-index")
async def create_vector_index_endpoint(
    ingestion_service: RAGIngestionService = Depends(get_rag_ingestion_service),
):
    from app.infrastructure.vector_store.pgvector_store import PGVectorStore
    from app.infrastructure.db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        vector_store = PGVectorStore(session)
        await vector_store.create_vector_index()
    return {"status": "Vector index creation triggered"}
