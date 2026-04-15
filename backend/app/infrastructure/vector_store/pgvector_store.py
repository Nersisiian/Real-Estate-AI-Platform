from typing import List, Optional
from uuid import UUID
import logging
from dataclasses import dataclass

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import EmbeddingModel, PropertyModel

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    property_id: UUID
    content: str
    score: float
    chunk_index: int
    embedding_id: UUID
    property_title: str
    property_price: float
    property_city: str


class PGVectorStore:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.vector_dim = 1536

    async def similarity_search_with_filters(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        min_score: float = 0.7,
        city: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rooms: Optional[int] = None,
        max_rooms: Optional[int] = None,
        property_type: Optional[str] = None,
        property_ids: Optional[List[UUID]] = None,
    ) -> List[SearchResult]:
        property_filters = []
        if city:
            property_filters.append(PropertyModel.city.ilike(f"%{city}%"))
        if min_price is not None:
            property_filters.append(PropertyModel.price >= min_price)
        if max_price is not None:
            property_filters.append(PropertyModel.price <= max_price)
        if min_rooms is not None:
            property_filters.append(PropertyModel.rooms >= min_rooms)
        if max_rooms is not None:
            property_filters.append(PropertyModel.rooms <= max_rooms)
        if property_type:
            property_filters.append(PropertyModel.property_type == property_type)
        if property_ids:
            property_filters.append(PropertyModel.id.in_(property_ids))

        distance_expr = EmbeddingModel.embedding.cosine_distance(query_embedding)
        score_expr = 1.0 - distance_expr

        stmt = (
            select(
                EmbeddingModel.id.label("embedding_id"),
                EmbeddingModel.property_id,
                EmbeddingModel.content,
                EmbeddingModel.chunk_index,
                score_expr.label("score"),
                PropertyModel.title.label("property_title"),
                PropertyModel.price.label("property_price"),
                PropertyModel.city.label("property_city"),
            )
            .join(PropertyModel, EmbeddingModel.property_id == PropertyModel.id)
            .where(
                score_expr >= min_score,
                PropertyModel.is_active == True,
                *property_filters,
            )
            .order_by(distance_expr)
            .limit(top_k)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            SearchResult(
                property_id=row.property_id,
                content=row.content,
                score=row.score,
                chunk_index=row.chunk_index,
                embedding_id=row.embedding_id,
                property_title=row.property_title,
                property_price=float(row.property_price),
                property_city=row.property_city,
            )
            for row in rows
        ]

    async def create_vector_index(
        self, index_type: str = "ivfflat", lists: int = 100
    ) -> None:
        check_query = text("""
            SELECT 1 FROM pg_indexes
            WHERE tablename = 'embeddings' AND indexname = 'embeddings_embedding_idx'
        """)
        result = await self.session.execute(check_query)
        if result.fetchone():
            logger.info("Vector index already exists")
            return

        logger.info(f"Creating vector index of type {index_type} with {lists} lists")

        if index_type.lower() == "ivfflat":
            create_index_sql = text(f"""
                CREATE INDEX embeddings_embedding_idx ON embeddings
                USING ivfflat (embedding vector_cosine_ops) WITH (lists = {lists})
            """)
        elif index_type.lower() == "hnsw":
            create_index_sql = text(f"""
                CREATE INDEX embeddings_embedding_idx ON embeddings
                USING hnsw (embedding vector_cosine_ops)
            """)
        else:
            raise ValueError(f"Unsupported index type: {index_type}")

        await self.session.execute(create_index_sql)
        await self.session.commit()
        logger.info("Vector index created successfully")
