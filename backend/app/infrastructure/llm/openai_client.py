import time
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI, AsyncTimeout, RateLimitError, APIError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.core.config import get_settings
from app.infrastructure.llm.token_counter import TokenCounter
from app.infrastructure.cache.redis_cache import RedisCache

settings = get_settings()
logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


class TokenLimitExceededError(LLMError):
    pass


class OpenAIClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        cache: Optional[RedisCache] = None,
    ):
        self.client = AsyncOpenAI(
            api_key=api_key or settings.OPENAI_API_KEY,
            timeout=AsyncTimeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
            max_retries=0,
        )
        self.model = model or settings.OPENAI_MODEL
        self.fallback_model = settings.FALLBACK_MODEL
        self.token_counter = TokenCounter(model=self.model)
        self.cache = cache if settings.ENABLE_CACHE else None
        self.max_context_tokens = settings.MAX_CONTEXT_TOKENS

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((RateLimitError, APIError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _call_openai(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        stream: bool = False,
    ):
        start_time = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            if not stream:
                usage = response.usage
                logger.info(
                    f"LLM call completed",
                    extra={
                        "model": self.model,
                        "duration_ms": round(duration_ms, 2),
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens,
                    }
                )
            return response
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"LLM call failed",
                extra={
                    "model": self.model,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                }
            )
            raise

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
    ) -> str:
        temperature = temperature or settings.OPENAI_TEMPERATURE

        cache_key = None
        if self.cache and use_cache:
            cache_key = self._generate_cache_key(messages, temperature, max_tokens)
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug("LLM cache hit", extra={"cache_key": cache_key[:8]})
                return cached

        truncated_messages = self._truncate_messages(messages, max_tokens)

        try:
            response = await self._call_openai(truncated_messages, temperature, max_tokens, stream=False)
            content = response.choices[0].message.content

            if self.cache and use_cache and cache_key:
                await self.cache.set(cache_key, content, ttl=settings.CACHE_TTL_SECONDS)

            return content
        except RateLimitError:
            logger.warning("Rate limit hit, falling back to fallback model")
            return await self._fallback_chat(truncated_messages, temperature, max_tokens)
        except APIError as e:
            if "context_length_exceeded" in str(e):
                raise TokenLimitExceededError("Context length exceeded even after truncation")
            raise LLMError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            raise LLMError(f"Unexpected error: {str(e)}")

    async def _fallback_chat(self, messages: List[Dict], temperature: float, max_tokens: Optional[int]) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.fallback_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise LLMError(f"Fallback model also failed: {str(e)}")

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        temperature = temperature or settings.OPENAI_TEMPERATURE
        truncated_messages = self._truncate_messages(messages, max_tokens)

        try:
            stream = await self._call_openai(truncated_messages, temperature, max_tokens, stream=True)
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise LLMError(f"Streaming failed: {str(e)}")

    def _truncate_messages(self, messages: List[Dict], max_completion_tokens: Optional[int] = None) -> List[Dict]:
        total_tokens = self.token_counter.count_messages_tokens(messages)
        reserved_for_completion = max_completion_tokens or 0
        available_tokens = self.max_context_tokens - reserved_for_completion

        if total_tokens <= available_tokens:
            return messages

        system_messages = [m for m in messages if m["role"] == "system"]
        other_messages = [m for m in messages if m["role"] != "system"]

        system_tokens = self.token_counter.count_messages_tokens(system_messages)
        available_for_other = available_tokens - system_tokens

        truncated_other = []
        current_tokens = 0
        for msg in reversed(other_messages):
            msg_tokens = self.token_counter.count_message_tokens(msg)
            if current_tokens + msg_tokens > available_for_other:
                break
            truncated_other.insert(0, msg)
            current_tokens += msg_tokens

        return system_messages + truncated_other

    def _generate_cache_key(self, messages: List[Dict], temperature: float, max_tokens: Optional[int]) -> str:
        import hashlib
        import json
        key_data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return f"llm:{hashlib.sha256(key_str.encode()).hexdigest()}"