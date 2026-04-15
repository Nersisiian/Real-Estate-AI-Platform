import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient
from uuid import uuid4

from app.main import app
from app.core.dependencies import get_openai_client


@pytest.mark.asyncio
async def test_chat_endpoint_mocked_llm(db_session):
    mock_openai = AsyncMock()
    mock_openai.chat_completion.return_value = (
        "I found several properties matching your criteria."
    )
    mock_openai.token_counter.count_tokens.return_value = 10
    mock_openai.token_counter.count_messages_tokens.return_value = 50
    mock_openai.token_counter.count_message_tokens.return_value = 20

    app.dependency_overrides[get_openai_client] = lambda: mock_openai

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            json={
                "messages": [{"role": "user", "content": "Find me a 3-bedroom house"}],
                "stream": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["response"] == "I found several properties matching your criteria."
        mock_openai.chat_completion.assert_called_once()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_agent_pipeline_execution(db_session):
    from app.infrastructure.agents.graph import MultiAgentGraph
    from app.infrastructure.llm.openai_client import OpenAIClient
    from app.infrastructure.vector_store.pgvector_store import PGVectorStore
    from app.infrastructure.llm.embeddings import EmbeddingGenerator
    from app.domain.repositories import PropertyRepository, UserSessionRepository

    mock_llm = AsyncMock(spec=OpenAIClient)
    mock_property_repo = AsyncMock(spec=PropertyRepository)
    mock_vector_store = AsyncMock(spec=PGVectorStore)
    mock_embed_gen = AsyncMock(spec=EmbeddingGenerator)
    mock_session_repo = AsyncMock(spec=UserSessionRepository)

    mock_llm.chat_completion.side_effect = [
        '{"search_query": "3 bedroom house", "filters": {"min_rooms": 3}, "tools": []}',
        "I found a nice 3-bedroom home for you.",
    ]
    mock_vector_store.similarity_search_with_filters.return_value = []
    mock_embed_gen.generate.return_value = [0.1] * 1536

    graph = MultiAgentGraph(
        openai_client=mock_llm,
        property_repo=mock_property_repo,
        vector_store=mock_vector_store,
        embedding_generator=mock_embed_gen,
        session_repo=mock_session_repo,
    )

    result = await graph.invoke(
        messages=[{"role": "user", "content": "Find me a 3-bedroom house"}],
        session_id=str(uuid4()),
    )

    assert result["final_response"] == "I found a nice 3-bedroom home for you."
    assert result["plan"]["search_query"] == "3 bedroom house"
    assert mock_llm.chat_completion.call_count == 2
