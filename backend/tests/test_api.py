import os
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
async def test_chat_endpoint(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "Hello"}], "stream": False},
    )
    assert response.status_code == 200