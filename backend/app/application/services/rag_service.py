import re
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import logging

from app.domain.entities import Property, Embedding
from app.domain.repositories import PropertyRepository, EmbeddingRepository
from app.infrastructure.llm.embeddings import EmbeddingGenerator
from app.infrastructure.vector_store.pgvector_store import PGVectorStore, SearchResult
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ChunkingStrategy:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_len = len(sentence)
            if current_length + sentence_len > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append(chunk_text)
                overlap_tokens = (
                    " ".join(current_chunk[-2:]) if len(current_chunk) >= 2 else ""
                )
                current_chunk = [overlap_tokens] if overlap_tokens else []
                current_length = len(overlap_tokens)
            current_chunk.append(sentence)
            current_length += sentence_len

        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(chunk_text)

        return chunks

    def chunk_property(self, property: Property) -> List[str]:
        parts = [
            f"Property: {property.title}",
            f"Type: {property.property_type}",
            f"Location: {property.location}, {property.city}, {property.state} {property.zip_code}",
            f"Price: ${property.price:,.2f}",
            f"Area: {property.area} sq ft",
            f"Rooms: {property.rooms} bedrooms, {property.bathrooms} bathrooms",
        ]
        if property.year_built:
            parts.append(f"Year Built: {property.year_built}")
        if property.amenities:
            parts.append(f"Amenities: {', '.join(property.amenities)}")
        parts.append(f"Description: {property.description}")
        if property.metadata:
            additional = ", ".join(
                f"{k}: {v}"
                for k, v in property.metadata.items()
                if isinstance(v, (str, int, float))
            )
            if additional:
                parts.append(f"Additional Info: {additional}")

        full_text = "\n".join(parts)
        return self.chunk_text(full_text)


class RAGIngestionService:
    def __init__(
        self,
        property_repo: PropertyRepository,
        embedding_repo: EmbeddingRepository,
        embedding_generator: EmbeddingGenerator,
        chunking_strategy: Optional[ChunkingStrategy] = None,
    ):
        self.property_repo = property_repo
        self.embedding_repo = embedding_repo
        self.embedding_generator = embedding_generator
        self.chunking = chunking_strategy or ChunkingStrategy(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

    async def ingest_property(self, property: Property) -> int:
        await self.embedding_repo.delete_by_property_id(property.id)

        chunks = self.chunking.chunk_property(property)
        if not chunks:
            logger.warning(f"No chunks generated for property {property.id}")
            return 0

        embeddings = await self.embedding_generator.generate_batch(chunks)

        embedding_entities = []
        for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            embedding = Embedding.create(
                property_id=property.id,
                content=chunk,
                embedding=vector,
                chunk_index=idx,
            )
            embedding_entities.append(embedding)

        await self.embedding_repo.save_batch(embedding_entities)
        logger.info(
            f"Ingested property {property.id} with {len(embedding_entities)} chunks"
        )
        return len(embedding_entities)

    async def ingest_properties_batch(
        self, properties: List[Property]
    ) -> Dict[UUID, int]:
        results = {}
        for prop in properties:
            count = await self.ingest_property(prop)
            results[prop.id] = count
        return results

    async def reindex_all(self) -> Dict[str, Any]:
        properties = await self.property_repo.find_by_criteria(limit=10000)
        results = await self.ingest_properties_batch(properties)
        return {
            "total_properties": len(properties),
            "embeddings_created": sum(results.values()),
            "details": results,
        }


class RAGRetrievalService:
    def __init__(
        self,
        vector_store: PGVectorStore,
        embedding_generator: EmbeddingGenerator,
        property_repo: PropertyRepository,
    ):
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator
        self.property_repo = property_repo

    async def retrieve_context(
        self,
        query: str,
        top_k: int = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[SearchResult], List[Property]]:
        top_k = top_k or settings.TOP_K_RETRIEVAL
        filters = filters or {}

        query_embedding = await self.embedding_generator.generate(query)

        search_results = await self.vector_store.similarity_search_with_filters(
            query_embedding=query_embedding,
            top_k=top_k,
            min_score=0.7,
            city=filters.get("city"),
            min_price=filters.get("min_price"),
            max_price=filters.get("max_price"),
            min_rooms=filters.get("min_rooms"),
            max_rooms=filters.get("max_rooms"),
            property_type=filters.get("property_type"),
            property_ids=filters.get("property_ids"),
        )

        unique_property_ids = list(set(r.property_id for r in search_results))
        properties = await self.property_repo.find_by_ids(unique_property_ids)

        return search_results, properties

    async def retrieve_with_rerank(
        self,
        query: str,
        top_k: int = None,
        filters: Optional[Dict[str, Any]] = None,
        reranker: Optional[Any] = None,
    ) -> Tuple[List[SearchResult], List[Property]]:
        search_results, properties = await self.retrieve_context(query, top_k, filters)
        if reranker and search_results:
            search_results = await reranker.rerank(
                query, search_results, top_n=settings.RERANK_TOP_K
            )
            prop_map = {p.id: p for p in properties}
            unique_props = []
            seen = set()
            for r in search_results:
                if r.property_id not in seen:
                    seen.add(r.property_id)
                    prop = prop_map.get(r.property_id)
                    if prop:
                        unique_props.append(prop)
            properties = unique_props
        return search_results, properties
