#!/usr/bin/env python3
import asyncio
import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.infrastructure.db.repositories_impl import (
    PropertyRepositoryImpl,
    EmbeddingRepositoryImpl,
)
from app.infrastructure.llm.embeddings import EmbeddingGenerator
from app.application.services.rag_service import RAGIngestionService, ChunkingStrategy
from app.domain.entities import Property

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SAMPLE_PROPERTIES = [
    {
        "title": "Modern Downtown Loft",
        "description": "Stunning 2-bedroom loft with floor-to-ceiling windows, exposed brick, and gourmet kitchen.",
        "price": 550000,
        "area": 1450,
        "rooms": 2,
        "bathrooms": 2,
        "location": "123 Main St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "property_type": "condo",
        "year_built": 2018,
        "amenities": ["pool", "gym", "rooftop deck"],
    },
    {
        "title": "Spacious Family Home",
        "description": "Beautiful 4-bedroom home in quiet suburban neighborhood with large backyard.",
        "price": 725000,
        "area": 2800,
        "rooms": 4,
        "bathrooms": 3,
        "location": "456 Oak Ave",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78745",
        "property_type": "house",
        "year_built": 2010,
        "amenities": ["pool", "fireplace", "two-car garage"],
    },
    {
        "title": "Luxury High-Rise Condo",
        "description": "Spectacular 3-bedroom corner unit with panoramic city views.",
        "price": 1250000,
        "area": 2100,
        "rooms": 3,
        "bathrooms": 3.5,
        "location": "789 Skyline Dr",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78703",
        "property_type": "condo",
        "year_built": 2022,
        "amenities": ["pool", "spa", "gym", "concierge"],
    },
    {
        "title": "Charming Bungalow",
        "description": "Adorable 3-bedroom bungalow in historic neighborhood.",
        "price": 475000,
        "area": 1600,
        "rooms": 3,
        "bathrooms": 2,
        "location": "321 Elm St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78702",
        "property_type": "house",
        "year_built": 1945,
        "amenities": ["fenced yard", "porch"],
    },
    {
        "title": "New Construction Townhome",
        "description": "Never lived in 3-story townhome with rooftop terrace.",
        "price": 625000,
        "area": 1950,
        "rooms": 3,
        "bathrooms": 2.5,
        "location": "567 Pine St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78704",
        "property_type": "townhouse",
        "year_built": 2024,
        "amenities": ["rooftop deck", "smart home", "EV charger"],
    },
]


async def create_sample_properties():
    async with AsyncSessionLocal() as session:
        repo = PropertyRepositoryImpl(session)
        for data in SAMPLE_PROPERTIES:
            prop = Property.create(
                title=data["title"],
                description=data["description"],
                price=Decimal(str(data["price"])),
                area=data["area"],
                rooms=data["rooms"],
                bathrooms=data["bathrooms"],
                location=data["location"],
                city=data["city"],
                state=data["state"],
                zip_code=data["zip_code"],
                property_type=data["property_type"],
                year_built=data.get("year_built"),
                amenities=data.get("amenities", []),
            )
            await repo.save(prop)
            logger.info(f"Created property: {prop.title}")


async def ingest_all_properties():
    async with AsyncSessionLocal() as session:
        settings = get_settings()
        prop_repo = PropertyRepositoryImpl(session)
        emb_repo = EmbeddingRepositoryImpl(session)
        emb_gen = EmbeddingGenerator()
        chunking = ChunkingStrategy(
            chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP
        )
        ingestion_service = RAGIngestionService(prop_repo, emb_repo, emb_gen, chunking)
        result = await ingestion_service.reindex_all()
        logger.info(f"Ingestion complete: {result}")


async def create_vector_index():
    from app.infrastructure.vector_store.pgvector_store import PGVectorStore

    async with AsyncSessionLocal() as session:
        vector_store = PGVectorStore(session)
        await vector_store.create_vector_index(index_type="ivfflat", lists=100)
        logger.info("Vector index created.")


async def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sample", action="store_true")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--create-index", action="store_true")
    args = parser.parse_args()

    if args.sample:
        await create_sample_properties()
        await ingest_all_properties()
    elif args.all:
        await ingest_all_properties()

    if args.create_index:
        await create_vector_index()


if __name__ == "__main__":
    asyncio.run(main())
