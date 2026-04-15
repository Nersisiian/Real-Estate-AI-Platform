from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from decimal import Decimal


@dataclass
class Property:
    id: UUID
    title: str
    description: str
    price: Decimal
    area: float
    rooms: int
    bathrooms: int
    location: str
    city: str
    state: str
    zip_code: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    property_type: str = "house"
    year_built: Optional[int] = None
    amenities: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True

    @classmethod
    def create(
        cls,
        title: str,
        description: str,
        price: Decimal,
        area: float,
        rooms: int,
        bathrooms: int,
        location: str,
        city: str,
        state: str,
        zip_code: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        property_type: str = "house",
        year_built: Optional[int] = None,
        amenities: List[str] = None,
        images: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> "Property":
        return cls(
            id=uuid4(),
            title=title,
            description=description,
            price=price,
            area=area,
            rooms=rooms,
            bathrooms=bathrooms,
            location=location,
            city=city,
            state=state,
            zip_code=zip_code,
            latitude=latitude,
            longitude=longitude,
            property_type=property_type,
            year_built=year_built,
            amenities=amenities or [],
            images=images or [],
            metadata=metadata or {},
        )


@dataclass
class Embedding:
    id: UUID
    property_id: UUID
    content: str
    embedding: List[float]
    chunk_index: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, property_id: UUID, content: str, embedding: List[float], chunk_index: int = 0) -> "Embedding":
        return cls(
            id=uuid4(),
            property_id=property_id,
            content=content,
            embedding=embedding,
            chunk_index=chunk_index,
        )


@dataclass
class UserSession:
    id: UUID
    user_id: Optional[str] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    @classmethod
    def create(cls, user_id: Optional[str] = None) -> "UserSession":
        return cls(
            id=uuid4(),
            user_id=user_id,
        )