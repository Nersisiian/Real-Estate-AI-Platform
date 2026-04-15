import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_chat_endpoint(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat",
        json={
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "session_id" in data
