import pytest
from decimal import Decimal
from app.domain.entities import Property
from app.application.services.rag_service import ChunkingStrategy
from app.infrastructure.llm.embeddings import EmbeddingGenerator
from app.infrastructure.db.repositories_impl import PropertyRepositoryImpl, EmbeddingRepositoryImpl
from app.application.services.rag_service import RAGIngestionService


def test_chunking_strategy():
    chunker = ChunkingStrategy(chunk_size=500, chunk_overlap=50)
    text = "This is a test. " * 50
    chunks = chunker.chunk_text(text)
    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk) <= 500


@pytest.mark.asyncio
async def test_rag_ingestion(db_session):
    prop_repo = PropertyRepositoryImpl(db_session)
    emb_repo = EmbeddingRepositoryImpl(db_session)
    emb_gen = EmbeddingGenerator()
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
    assert count > 0

    embeddings = await emb_repo.find_by_property_id(prop.id)
    assert len(embeddings) == count