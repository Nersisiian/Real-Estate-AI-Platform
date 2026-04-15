"""Initial migration with properties, embeddings, user_sessions

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector
from sqlalchemy.dialects.postgresql import UUID

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.create_table(
        'properties',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('price', sa.Numeric(12, 2), nullable=False),
        sa.Column('area', sa.Float(), nullable=False),
        sa.Column('rooms', sa.Integer(), nullable=False),
        sa.Column('bathrooms', sa.Integer(), nullable=False),
        sa.Column('location', sa.String(500), nullable=False),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('state', sa.String(50), nullable=False),
        sa.Column('zip_code', sa.String(20), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('property_type', sa.String(50), nullable=False),
        sa.Column('year_built', sa.Integer(), nullable=True),
        sa.Column('amenities', sa.ARRAY(sa.String()), server_default='{}'),
        sa.Column('images', sa.ARRAY(sa.String()), server_default='{}'),
        sa.Column('metadata', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
    )
    op.create_index('idx_properties_price', 'properties', ['price'])
    op.create_index('idx_properties_rooms', 'properties', ['rooms'])
    op.create_index('idx_properties_city', 'properties', ['city'])
    op.create_index('idx_properties_property_type', 'properties', ['property_type'])
    op.create_index('idx_properties_is_active', 'properties', ['is_active'])
    op.create_index('idx_properties_location', 'properties', ['city', 'state'])
    op.create_index('idx_properties_price_rooms', 'properties', ['price', 'rooms'])

    op.create_table(
        'embeddings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('property_id', UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', pgvector.sqlalchemy.Vector(dim=1536), nullable=False),
        sa.Column('chunk_index', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_embeddings_property_id', 'embeddings', ['property_id'])

    op.create_table(
        'user_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('messages', sa.JSON(), server_default='[]'),
        sa.Column('context', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_user_sessions_updated_at', 'user_sessions', ['updated_at'])
    op.create_index('idx_user_sessions_expires_at', 'user_sessions', ['expires_at'])


def downgrade() -> None:
    op.drop_table('user_sessions')
    op.drop_table('embeddings')
    op.drop_table('properties')
    op.execute('DROP EXTENSION IF EXISTS vector')