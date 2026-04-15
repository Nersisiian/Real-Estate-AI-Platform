@"
import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.main import app
from app.infrastructure.db.models import Base
from app.core.config import get_settings
from app.core.dependencies import get_db, get_redis_cache, get_embedding_generator

settings = get_settings()
TEST_DATABASE_URL = settings.async_database_url.replace(
    settings.POSTGRES_DB, f"{settings.POSTGRES_DB}_test"
)

engine_for_creation = create_async_engine(
    settings.async_database_url.replace(settings.POSTGRES_DB, "postgres"),
    echo=False,
    isolation_level="AUTOCOMMIT",
)


async def create_test_db():
    async with engine_for_creation.connect() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS {settings.POSTGRES_DB}_test"))
        await conn.execute(text(f"CREATE DATABASE {settings.POSTGRES_DB}_test"))
    await engine_for_creation.dispose()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    asyncio.run(create_test_db())
    yield


engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    async def override_get_cache():
        return None

    async def override_get_embedding_generator():
        from unittest.mock import AsyncMock
        mock = AsyncMock()
        mock.generate.return_value = [0.1] * 1536
        return mock

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_cache] = override_get_cache
    app.dependency_overrides[get_embedding_generator] = override_get_embedding_generator

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
"@ | Set-Content backend/tests/conftest.py
