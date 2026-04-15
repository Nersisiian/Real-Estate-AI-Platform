from functools import lru_cache
from typing import AsyncGenerator, Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.database import get_db
from app.infrastructure.db.repositories_impl import (
    PropertyRepositoryImpl,
    EmbeddingRepositoryImpl,
    UserSessionRepositoryImpl,
)
from app.infrastructure.vector_store.pgvector_store import PGVectorStore
from app.infrastructure.llm.embeddings import EmbeddingGenerator
from app.infrastructure.llm.openai_client import OpenAIClient
from app.infrastructure.cache.redis_cache import RedisCache
from app.infrastructure.agents.graph import MultiAgentGraph
from app.application.services.rag_service import RAGIngestionService, RAGRetrievalService, ChunkingStrategy
from app.application.services.agent_service import AgentService
from app.application.services.recommend_use_case import RecommendUseCase
from app.domain.repositories import PropertyRepository, EmbeddingRepository, UserSessionRepository
from app.core.config import get_settings

settings = get_settings()


async def get_property_repository(session: AsyncSession = Depends(get_db)) -> PropertyRepository:
    return PropertyRepositoryImpl(session)


async def get_embedding_repository(session: AsyncSession = Depends(get_db)) -> EmbeddingRepository:
    return EmbeddingRepositoryImpl(session)


async def get_user_session_repository(session: AsyncSession = Depends(get_db)) -> UserSessionRepository:
    return UserSessionRepositoryImpl(session)


async def get_vector_store(session: AsyncSession = Depends(get_db)) -> PGVectorStore:
    return PGVectorStore(session)


@lru_cache()
def get_redis_cache() -> RedisCache:
    return RedisCache() if settings.ENABLE_CACHE else None


@lru_cache()
def get_embedding_generator(cache: Optional[RedisCache] = Depends(get_redis_cache)) -> EmbeddingGenerator:
    return EmbeddingGenerator(cache=cache)


@lru_cache()
def get_openai_client(cache: Optional[RedisCache] = Depends(get_redis_cache)) -> OpenAIClient:
    return OpenAIClient(cache=cache)


async def get_chunking_strategy() -> ChunkingStrategy:
    return ChunkingStrategy(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )


async def get_rag_ingestion_service(
    property_repo: PropertyRepository = Depends(get_property_repository),
    embedding_repo: EmbeddingRepository = Depends(get_embedding_repository),
    embedding_gen: EmbeddingGenerator = Depends(get_embedding_generator),
    chunking: ChunkingStrategy = Depends(get_chunking_strategy),
) -> RAGIngestionService:
    return RAGIngestionService(
        property_repo=property_repo,
        embedding_repo=embedding_repo,
        embedding_generator=embedding_gen,
        chunking_strategy=chunking,
    )


async def get_rag_retrieval_service(
    vector_store: PGVectorStore = Depends(get_vector_store),
    embedding_gen: EmbeddingGenerator = Depends(get_embedding_generator),
    property_repo: PropertyRepository = Depends(get_property_repository),
) -> RAGRetrievalService:
    return RAGRetrievalService(
        vector_store=vector_store,
        embedding_generator=embedding_gen,
        property_repo=property_repo,
    )


async def get_agent_graph(
    openai_client: OpenAIClient = Depends(get_openai_client),
    property_repo: PropertyRepository = Depends(get_property_repository),
    vector_store: PGVectorStore = Depends(get_vector_store),
    embedding_gen: EmbeddingGenerator = Depends(get_embedding_generator),
    session_repo: UserSessionRepository = Depends(get_user_session_repository),
    cache: Optional[RedisCache] = Depends(get_redis_cache),
) -> MultiAgentGraph:
    return MultiAgentGraph(
        openai_client=openai_client,
        property_repo=property_repo,
        vector_store=vector_store,
        embedding_generator=embedding_gen,
        session_repo=session_repo,
        cache=cache,
    )


async def get_agent_service(
    agent_graph: MultiAgentGraph = Depends(get_agent_graph),
) -> AgentService:
    return AgentService(agent_graph)


async def get_recommend_use_case(
    property_repo: PropertyRepository = Depends(get_property_repository),
    embedding_repo: EmbeddingRepository = Depends(get_embedding_repository),
    embedding_gen: EmbeddingGenerator = Depends(get_embedding_generator),
    vector_store: PGVectorStore = Depends(get_vector_store),
) -> RecommendUseCase:
    return RecommendUseCase(
        property_repo=property_repo,
        embedding_repo=embedding_repo,
        embedding_generator=embedding_gen,
        vector_store=vector_store,
    )