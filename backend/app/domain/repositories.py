from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID
from decimal import Decimal

from app.domain.entities import Property, Embedding, UserSession


class PropertyRepository(ABC):
    @abstractmethod
    async def get(self, id: UUID) -> Optional[Property]:
        pass

    @abstractmethod
    async def save(self, property: Property) -> Property:
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def find_by_ids(self, ids: List[UUID]) -> List[Property]:
        pass


class EmbeddingRepository(ABC):
    @abstractmethod
    async def save(self, embedding: Embedding) -> Embedding:
        pass

    @abstractmethod
    async def save_batch(self, embeddings: List[Embedding]) -> List[Embedding]:
        pass

    @abstractmethod
    async def find_by_property_id(self, property_id: UUID) -> List[Embedding]:
        pass

    @abstractmethod
    async def delete_by_property_id(self, property_id: UUID) -> int:
        pass

    @abstractmethod
    async def similarity_search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        min_score: float = 0.7,
        property_ids_filter: Optional[List[UUID]] = None,
    ) -> List[Tuple[Embedding, float]]:
        pass


class UserSessionRepository(ABC):
    @abstractmethod
    async def get(self, id: UUID) -> Optional[UserSession]:
        pass

    @abstractmethod
    async def save(self, session: UserSession) -> UserSession:
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        pass

    @abstractmethod
    async def update_messages(
        self, id: UUID, messages: List[Dict[str, Any]]
    ) -> Optional[UserSession]:
        pass
