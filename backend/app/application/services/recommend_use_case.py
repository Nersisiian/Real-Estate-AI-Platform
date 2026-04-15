from typing import List, Dict, Any
from uuid import UUID
import logging

from app.domain.entities import Property
from app.domain.repositories import PropertyRepository, EmbeddingRepository
from app.infrastructure.llm.embeddings import EmbeddingGenerator
from app.infrastructure.vector_store.pgvector_store import PGVectorStore

logger = logging.getLogger(__name__)


class RecommendUseCase:
    def __init__(
        self,
        property_repo: PropertyRepository,
        embedding_repo: EmbeddingRepository,
        embedding_generator: EmbeddingGenerator,
        vector_store: PGVectorStore,
    ):
        self.property_repo = property_repo
        self.embedding_repo = embedding_repo
        self.embedding_generator = embedding_generator
        self.vector_store = vector_store

    async def find_similar(self, property_id: UUID, limit: int = 5) -> List[Property]:
        embeddings = await self.embedding_repo.find_by_property_id(property_id)
        if not embeddings:
            raise ValueError(f"No embeddings found for property {property_id}")

        query_embedding = embeddings[0].embedding

        results = await self.vector_store.similarity_search_with_filters(
            query_embedding=query_embedding,
            top_k=limit + 1,
            min_score=0.7,
        )

        similar_props = []
        for r in results:
            if r.property_id != property_id:
                prop = await self.property_repo.get(r.property_id)
                if prop:
                    similar_props.append(prop)
                if len(similar_props) >= limit:
                    break

        return similar_props

    async def personalized_recommend(
        self,
        preferences: Dict[str, Any],
        limit: int = 10,
    ) -> List[Property]:
        query_text = self._build_query_from_preferences(preferences)
        query_embedding = await self.embedding_generator.generate(query_text)

        filters = {
            "min_price": preferences.get("min_price"),
            "max_price": preferences.get("max_price"),
            "min_rooms": preferences.get("min_rooms"),
            "max_rooms": preferences.get("max_rooms"),
            "city": preferences.get("city"),
            "property_type": preferences.get("property_type"),
        }

        results = await self.vector_store.similarity_search_with_filters(
            query_embedding=query_embedding,
            top_k=limit * 2,
            min_score=0.6,
            **{k: v for k, v in filters.items() if v is not None},
        )

        property_ids = list(set(r.property_id for r in results))
        properties = await self.property_repo.find_by_ids(property_ids)

        return properties[:limit]

    def _build_query_from_preferences(self, preferences: Dict[str, Any]) -> str:
        parts = []
        if "description" in preferences:
            parts.append(preferences["description"])
        else:
            if "city" in preferences:
                parts.append(f"in {preferences['city']}")
            if "property_type" in preferences:
                parts.append(f"{preferences['property_type']}")
            if "min_rooms" in preferences:
                parts.append(f"at least {preferences['min_rooms']} bedrooms")
            if "amenities" in preferences:
                parts.append(f"with {', '.join(preferences['amenities'])}")

        query = "Looking for a property " + " ".join(parts)
        return query
