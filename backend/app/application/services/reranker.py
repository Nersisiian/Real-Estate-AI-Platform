import asyncio
from typing import List, Optional
import logging

from app.infrastructure.vector_store.pgvector_store import SearchResult

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self._initialized = False

    async def _lazy_init(self):
        if self._initialized:
            return
        try:
            from sentence_transformers import CrossEncoder

            self.model = CrossEncoder(self.model_name)
            self._initialized = True
            logger.info(f"Loaded cross-encoder model: {self.model_name}")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. Using fallback score-based reranking."
            )
            self.model = None
            self._initialized = True

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_n: int = 3,
    ) -> List[SearchResult]:
        if not results:
            return []

        await self._lazy_init()

        if self.model is None:
            sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
            return sorted_results[:top_n]

        pairs = [(query, r.content) for r in results]
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(None, self.model.predict, pairs)

        if hasattr(scores, "tolist"):
            scores = scores.tolist()

        for result, score in zip(results, scores):
            result.score = float(score)

        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
        return sorted_results[:top_n]


class LLMReranker:
    def __init__(self, llm_client):
        self.llm = llm_client

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_n: int = 3,
    ) -> List[SearchResult]:
        if not results:
            return []

        scored_results = []
        for result in results:
            prompt = f"""Rate the relevance of this property description to the search query on a scale of 0 to 10.

Search Query: {query}
Property Description: {result.content}
Relevance Score (0-10):"""

            try:
                response = await self.llm.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=10,
                )
                import re

                match = re.search(r"\b(\d+(?:\.\d+)?)\b", response)
                if match:
                    score = float(match.group(1)) / 10.0
                else:
                    score = result.score
            except Exception as e:
                logger.error(f"LLM reranking error: {e}")
                score = result.score

            result.score = score
            scored_results.append(result)

        sorted_results = sorted(scored_results, key=lambda x: x.score, reverse=True)
        return sorted_results[:top_n]
