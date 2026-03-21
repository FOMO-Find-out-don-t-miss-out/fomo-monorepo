import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock
from app.db.session import get_db

@pytest.mark.asyncio
async def test_health_check_healthy(client: AsyncClient, mock_redis):
    """Test health check when all components are healthy."""
    # Mocking redis.ping() is done via fakeredis
    # Postgres health check runs SELECT 1 in the session
    
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["components"]["database"] == "healthy"
    assert data["components"]["redis"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_db_unhealthy(client: AsyncClient, mock_redis, monkeypatch):
    """Test health check when database is unhealthy."""
    from sqlmodel import Session, text
    
    # Override the database execute method to raise an exception
    def mock_execute(*args, **kwargs):
        raise Exception("Database Connection Refused")
    
    monkeypatch.setattr(Session, "execute", mock_execute)
    
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "unhealthy: Database Connection Refused" in data["components"]["database"]
    assert data["components"]["redis"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_redis_unhealthy(client: AsyncClient, monkeypatch):
    """Test health check when Redis is unhealthy."""
    import app.api.v1.health as health_module
    
    # Mock redis client that raises an exception on ping
    mock_bad_redis = MagicMock()
    mock_bad_redis.ping.side_effect = Exception("Redis connection lost")
    monkeypatch.setattr(health_module, "redis_client", mock_bad_redis)
    
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["components"]["database"] == "healthy"
    assert "unhealthy: Redis connection lost" in data["components"]["redis"]
