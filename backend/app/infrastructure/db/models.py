from sqlalchemy import (
    Column,
    String,
    Numeric,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    ARRAY,
    ForeignKey,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid

from app.infrastructure.db.database import Base


class PropertyModel(Base):
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Numeric(12, 2), nullable=False, index=True)
    area = Column(Float, nullable=False)
    rooms = Column(Integer, nullable=False, index=True)
    bathrooms = Column(Integer, nullable=False)
    location = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(50), nullable=False)
    zip_code = Column(String(20), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    property_type = Column(String(50), nullable=False, index=True)
    year_built = Column(Integer, nullable=True)
    amenities = Column(ARRAY(String), default=[])
    images = Column(ARRAY(String), default=[])
    metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    updated_at = Column(
        DateTime(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()")
    )
    is_active = Column(Boolean, default=True, index=True)

    embeddings = relationship(
        "EmbeddingModel", back_populates="property", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_properties_location", "city", "state"),
        Index("idx_properties_price_rooms", "price", "rooms"),
    )


class EmbeddingModel(Base):
    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    chunk_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))

    property = relationship("PropertyModel", back_populates="embeddings")

    __table_args__ = (Index("idx_embeddings_property_id", "property_id"),)


class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=True, index=True)
    messages = Column(JSON, default=[])
    context = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    updated_at = Column(
        DateTime(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()")
    )
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (Index("idx_user_sessions_updated_at", "updated_at"),)
