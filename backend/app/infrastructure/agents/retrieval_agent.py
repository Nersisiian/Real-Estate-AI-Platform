from typing import List, Dict, Any
import logging

from app.infrastructure.vector_store.pgvector_store import PGVectorStore
from app.infrastructure.llm.embeddings import EmbeddingGenerator
from app.domain.repositories import PropertyRepository
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RetrievalAgent:
    def __init__(
        self,
        vector_store: PGVectorStore,
        embedding_generator: EmbeddingGenerator,
        property_repo: PropertyRepository,
    ):
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator
        self.property_repo = property_repo

    async def retrieve(
        self,
        query: str,
        filters: Dict[str, Any],
        top_k: int = None,
    ) -> List[Dict[str, Any]]:
        top_k = top_k or settings.TOP_K_RETRIEVAL

        query_embedding = await self.embedding_generator.generate(query)

        search_results = await self.vector_store.similarity_search_with_filters(
            query_embedding=query_embedding,
            top_k=top_k,
            min_score=0.65,
            city=filters.get("city"),
            min_price=filters.get("min_price"),
            max_price=filters.get("max_price"),
            min_rooms=filters.get("min_rooms"),
            max_rooms=filters.get("max_rooms"),
            property_type=filters.get("property_type"),
        )

        if not search_results:
            return []

        unique_ids = list(set(r.property_id for r in search_results))
        properties = await self.property_repo.find_by_ids(unique_ids)
        prop_map = {str(p.id): p for p in properties}

        context_items = []
        for result in search_results:
            prop = prop_map.get(str(result.property_id))
            if prop:
                context_items.append({
                    "property_id": str(prop.id),
                    "title": prop.title,
                    "price": float(prop.price),
                    "location": f"{prop.city}, {prop.state}",
                    "rooms": prop.rooms,
                    "area": prop.area,
                    "content": result.content,
                    "score": result.score,
                })

        deduped = {}
        for item in context_items:
            pid = item["property_id"]
            if pid not in deduped or item["score"] > deduped[pid]["score"]:
                deduped[pid] = item

        return list(deduped.values())