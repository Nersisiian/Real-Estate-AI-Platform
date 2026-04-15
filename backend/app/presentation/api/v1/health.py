from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis

from app.infrastructure.db.database import get_db
from app.infrastructure.llm.openai_client import OpenAIClient
from app.core.config import get_settings
from app.core.dependencies import get_openai_client

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}


@router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    openai_client: OpenAIClient = Depends(get_openai_client),
):
    checks = {"database": False, "redis": False, "llm": False}

    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            checks["database"] = True
    except Exception as e:
        checks["database"] = str(e)

    try:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        await redis_client.close()
        checks["redis"] = True
    except Exception as e:
        checks["redis"] = str(e)

    try:
        test_message = "test"
        tokens = openai_client.token_counter.count_tokens(test_message)
        if tokens > 0:
            checks["llm"] = True
    except Exception as e:
        checks["llm"] = str(e)

    all_ready = all(v is True for v in checks.values())
    status_code = 200 if all_ready else 503
    return {"status": "ready" if all_ready else "not ready", "checks": checks}