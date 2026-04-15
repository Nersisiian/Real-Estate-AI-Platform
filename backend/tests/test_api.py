import os
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("CI") == "true" or not os.getenv("OPENAI_API_KEY"),
    reason="Skipping API tests in CI or missing API key"
)
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("CI") == "true" or not os.getenv("OPENAI_API_KEY"),
    reason="Skipping API tests in CI or missing API key"
)
async def test_chat_endpoint(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "Hello"}], "stream": False},
    )
    assert response.status_code == 200
