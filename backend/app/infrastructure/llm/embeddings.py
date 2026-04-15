import hashlib
import logging
from typing import List, Optional
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.infrastructure.cache.redis_cache import RedisCache

settings = get_settings()
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, cache: Optional[RedisCache] = None):
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.model = model or settings.OPENAI_EMBEDDING_MODEL
        self.cache = cache if settings.ENABLE_CACHE else None

    def _cache_key(self, text: str) -> str:
        return f"emb:{hashlib.sha256(text.encode()).hexdigest()}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def generate(self, text: str) -> List[float]:
        if self.cache:
            cached = await self.cache.get(self._cache_key(text))
            if cached:
                logger.debug("Embedding cache hit")
                return cached

        try:
            response = await self.client.embeddings.create(model=self.model, input=text)
            embedding = response.data[0].embedding
            if self.cache:
                await self.cache.set(self._cache_key(text), embedding, ttl=86400)
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        if self.cache:
            for i, text in enumerate(texts):
                cached = await self.cache.get(self._cache_key(text))
                if cached:
                    embeddings.append(cached)
                else:
                    embeddings.append(None)
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            embeddings = [None] * len(texts)

        if uncached_texts:
            try:
                response = await self.client.embeddings.create(model=self.model, input=uncached_texts)
                for idx, data in zip(uncached_indices, response.data):
                    emb = data.embedding
                    embeddings[idx] = emb
                    if self.cache:
                        await self.cache.set(self._cache_key(texts[idx]), emb, ttl=86400)
            except Exception as e:
                logger.error(f"Batch embedding error: {e}")
                raise

        return embeddings