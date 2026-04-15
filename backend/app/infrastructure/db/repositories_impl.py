from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID
from decimal import Decimal
import logging

from sqlalchemy import select, delete, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.domain.repositories import (
    PropertyRepository,
    EmbeddingRepository,
    UserSessionRepository,
)
from app.domain.entities import Property, Embedding, UserSession
from app.infrastructure.db.models import PropertyModel, EmbeddingModel, UserSessionModel

logger = logging.getLogger(__name__)


class PropertyRepositoryImpl(PropertyRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: UUID) -> Optional[Property]:
        stmt = select(PropertyModel).where(PropertyModel.id == id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, property: Property) -> Property:
        model = self._to_model(property)
        stmt = (
            insert(PropertyModel)
            .values(**model)
            .on_conflict_do_update(
                index_elements=[PropertyModel.id],
                set_={
                    "title": model["title"],
                    "description": model["description"],
                    "price": model["price"],
                    "area": model["area"],
                    "rooms": model["rooms"],
                    "bathrooms": model["bathrooms"],
                    "location": model["location"],
                    "city": model["city"],
                    "state": model["state"],
                    "zip_code": model["zip_code"],
                    "latitude": model["latitude"],
                    "longitude": model["longitude"],
                    "property_type": model["property_type"],
                    "year_built": model["year_built"],
                    "amenities": model["amenities"],
                    "images": model["images"],
                    "metadata": model["metadata"],
                    "updated_at": model["updated_at"],
                    "is_active": model["is_active"],
                },
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return property

    async def delete(self, id: UUID) -> bool:
        stmt = delete(PropertyModel).where(PropertyModel.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def find_by_criteria(
        self,
        city: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        min_rooms: Optional[int] = None,
        max_rooms: Optional[int] = None,
        property_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Property]:
        query = select(PropertyModel).where(PropertyModel.is_active == True)

        if city:
            query = query.where(PropertyModel.city.ilike(f"%{city}%"))
        if min_price is not None:
            query = query.where(PropertyModel.price >= min_price)
        if max_price is not None:
            query = query.where(PropertyModel.price <= max_price)
        if min_rooms is not None:
            query = query.where(PropertyModel.rooms >= min_rooms)
        if max_rooms is not None:
            query = query.where(PropertyModel.rooms <= max_rooms)
        if property_type:
            query = query.where(PropertyModel.property_type == property_type)

        query = (
            query.limit(limit).offset(offset).order_by(PropertyModel.created_at.desc())
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def find_by_ids(self, ids: List[UUID]) -> List[Property]:
        if not ids:
            return []
        stmt = select(PropertyModel).where(PropertyModel.id.in_(ids))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    @staticmethod
    def _to_entity(model: PropertyModel) -> Property:
        return Property(
            id=model.id,
            title=model.title,
            description=model.description,
            price=model.price,
            area=model.area,
            rooms=model.rooms,
            bathrooms=model.bathrooms,
            location=model.location,
            city=model.city,
            state=model.state,
            zip_code=model.zip_code,
            latitude=model.latitude,
            longitude=model.longitude,
            property_type=model.property_type,
            year_built=model.year_built,
            amenities=model.amenities or [],
            images=model.images or [],
            metadata=model.metadata or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_active=model.is_active,
        )

    @staticmethod
    def _to_model(entity: Property) -> dict:
        return {
            "id": entity.id,
            "title": entity.title,
            "description": entity.description,
            "price": entity.price,
            "area": entity.area,
            "rooms": entity.rooms,
            "bathrooms": entity.bathrooms,
            "location": entity.location,
            "city": entity.city,
            "state": entity.state,
            "zip_code": entity.zip_code,
            "latitude": entity.latitude,
            "longitude": entity.longitude,
            "property_type": entity.property_type,
            "year_built": entity.year_built,
            "amenities": entity.amenities,
            "images": entity.images,
            "metadata": entity.metadata,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "is_active": entity.is_active,
        }


class EmbeddingRepositoryImpl(EmbeddingRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, embedding: Embedding) -> Embedding:
        model = self._to_model(embedding)
        stmt = (
            insert(EmbeddingModel)
            .values(**model)
            .on_conflict_do_update(
                index_elements=[EmbeddingModel.id],
                set_={
                    "content": model["content"],
                    "embedding": model["embedding"],
                    "chunk_index": model["chunk_index"],
                },
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return embedding

    async def save_batch(self, embeddings: List[Embedding]) -> List[Embedding]:
        if not embeddings:
            return []
        models = [self._to_model(e) for e in embeddings]
        stmt = insert(EmbeddingModel).values(models)
        await self.session.execute(stmt)
        await self.session.commit()
        return embeddings

    async def find_by_property_id(self, property_id: UUID) -> List[Embedding]:
        stmt = (
            select(EmbeddingModel)
            .where(EmbeddingModel.property_id == property_id)
            .order_by(EmbeddingModel.chunk_index)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def delete_by_property_id(self, property_id: UUID) -> int:
        stmt = delete(EmbeddingModel).where(EmbeddingModel.property_id == property_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def similarity_search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        min_score: float = 0.7,
        property_ids_filter: Optional[List[UUID]] = None,
    ) -> List[Tuple[Embedding, float]]:
        distance_expr = EmbeddingModel.embedding.cosine_distance(query_embedding)
        score_expr = 1.0 - distance_expr

        query = select(EmbeddingModel, score_expr.label("score")).where(
            distance_expr <= (1.0 - min_score)
        )

        if property_ids_filter:
            query = query.where(EmbeddingModel.property_id.in_(property_ids_filter))

        query = query.order_by(distance_expr).limit(limit)

        result = await self.session.execute(query)
        rows = result.all()

        return [(self._to_entity(row.EmbeddingModel), row.score) for row in rows]

    @staticmethod
    def _to_entity(model: EmbeddingModel) -> Embedding:
        return Embedding(
            id=model.id,
            property_id=model.property_id,
            content=model.content,
            embedding=(
                model.embedding.tolist()
                if hasattr(model.embedding, "tolist")
                else model.embedding
            ),
            chunk_index=model.chunk_index,
            created_at=model.created_at,
        )

    @staticmethod
    def _to_model(entity: Embedding) -> dict:
        return {
            "id": entity.id,
            "property_id": entity.property_id,
            "content": entity.content,
            "embedding": entity.embedding,
            "chunk_index": entity.chunk_index,
            "created_at": entity.created_at,
        }


class UserSessionRepositoryImpl(UserSessionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: UUID) -> Optional[UserSession]:
        stmt = select(UserSessionModel).where(UserSessionModel.id == id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, session: UserSession) -> UserSession:
        model = self._to_model(session)
        stmt = (
            insert(UserSessionModel)
            .values(**model)
            .on_conflict_do_update(
                index_elements=[UserSessionModel.id],
                set_={
                    "user_id": model["user_id"],
                    "messages": model["messages"],
                    "context": model["context"],
                    "updated_at": model["updated_at"],
                    "expires_at": model["expires_at"],
                },
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return session

    async def delete(self, id: UUID) -> bool:
        stmt = delete(UserSessionModel).where(UserSessionModel.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def update_messages(
        self, id: UUID, messages: List[Dict[str, Any]]
    ) -> Optional[UserSession]:
        from datetime import datetime

        stmt = (
            update(UserSessionModel)
            .where(UserSessionModel.id == id)
            .values(messages=messages, updated_at=datetime.utcnow())
            .returning(UserSessionModel)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        await self.session.commit()
        return self._to_entity(model) if model else None

    @staticmethod
    def _to_entity(model: UserSessionModel) -> UserSession:
        return UserSession(
            id=model.id,
            user_id=model.user_id,
            messages=model.messages or [],
            context=model.context or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
            expires_at=model.expires_at,
        )

    @staticmethod
    def _to_model(entity: UserSession) -> dict:
        return {
            "id": entity.id,
            "user_id": entity.user_id,
            "messages": entity.messages,
            "context": entity.context,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "expires_at": entity.expires_at,
        }
