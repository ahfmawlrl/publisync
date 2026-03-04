import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/health")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "status" in data["data"]
