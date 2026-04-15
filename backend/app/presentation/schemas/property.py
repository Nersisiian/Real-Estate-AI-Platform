from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class PropertyBase(BaseModel):
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
    amenities: List[str] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PropertyCreate(PropertyBase):
    pass


class PropertyResponse(PropertyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class PropertySearchFilters(BaseModel):
    city: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rooms: Optional[int] = None
    max_rooms: Optional[int] = None
    property_type: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class SearchRequest(BaseModel):
    query: str
    filters: Optional[PropertySearchFilters] = None
    top_k: int = Field(5, ge=1, le=20)


class SearchResponse(BaseModel):
    results: List[PropertyResponse]
    total: int
    query: str
