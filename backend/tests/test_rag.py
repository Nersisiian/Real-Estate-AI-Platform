import os
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from app.domain.entities import Property
from app.application.services.rag_service import ChunkingStrategy, RAGIngestionService
from app.infrastructure.llm.embeddings import EmbeddingGenerator
from app.infrastructure.db.repositories_impl import PropertyRepositoryImpl, EmbeddingRepositoryImpl

def test_chunking_strategy():
    chunker = ChunkingStrategy(chunk_size=500, chunk_overlap=50)
    text = "This is a test. " * 50
    chunks = chunker.chunk_text(text)
    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk) <= 600

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set or quota exceeded")
async def test_rag_ingestion(db_session):
    prop_repo = PropertyRepositoryImpl(db_session)
    emb_repo = EmbeddingRepositoryImpl(db_session)
    # Mock the embedding generator to avoid real API calls
    emb_gen = AsyncMock(spec=EmbeddingGenerator)
    emb_gen.generate_batch.return_value = [[0.1] * 1536]
    ingestion = RAGIngestionService(prop_repo, emb_repo, emb_gen)

    prop = Property.create(
        title="Test Property",
        description="A beautiful test home.",
        price=Decimal("500000"),
        area=2000,
        rooms=3,
        bathrooms=2,
        location="123 Test St",
        city="Test City",
        state="TS",
        zip_code="12345",
    )
    await prop_repo.save(prop)

    count = await ingestion.ingest_property(prop)
    assert count == 1
    embeddings = await emb_repo.find_by_property_id(prop.id)
    assert len(embeddings) == count