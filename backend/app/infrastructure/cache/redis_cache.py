import json
from typing import Optional, Any
import logging
from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self, redis_client: Optional[Redis] = None):
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = Redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        try:
            serialized = json.dumps(value)
            ttl = ttl or settings.CACHE_TTL_SECONDS
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        try:
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += await self.redis.delete(*keys)
                if cursor == 0:
                    break
            return deleted
        except Exception as e:
            logger.error(f"Redis clear pattern error: {e}")
            return 0
