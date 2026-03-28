from typing import Any

import pytest
from httpx import AsyncClient
from sqlmodel import Session


@pytest.mark.asyncio
async def test_health_check_healthy(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test health check when both components are healthy."""
    import app.api.v1.health as health_module

    class MockRedisHealthy:
        async def ping(self) -> str:
            return "PONG"

    monkeypatch.setattr(health_module, "redis_client", MockRedisHealthy())

    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    # If the environment is not fully set up, it might be unhealthy but should return 200
    # In tests, we expect healthy if we mock correctly
    assert data["status"] == "ok"
    assert data["components"]["database"] == "healthy"
    assert data["components"]["redis"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_db_unhealthy(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test health check when Database is unhealthy."""

    def mock_execute(*args: Any, **kwargs: Any) -> None:
        raise Exception("Database Connection Refused")

    monkeypatch.setattr(Session, "execute", mock_execute)

    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "unhealthy" in data["components"]["database"]


@pytest.mark.asyncio
async def test_health_check_redis_unhealthy(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test health check when Redis is unhealthy."""
    import app.api.v1.health as health_module

    class MockRedisUnhealthy:
        async def ping(self) -> None:
            raise Exception("Redis Connection Refused")

    monkeypatch.setattr(health_module, "redis_client", MockRedisUnhealthy())

    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "unhealthy" in data["components"]["redis"]
