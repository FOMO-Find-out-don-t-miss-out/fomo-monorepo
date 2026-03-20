import sys
from unittest.mock import MagicMock

# MOCK GEOGRAPHY BEFORE ANY IMPORTS
import sqlalchemy

class MockGeography(sqlalchemy.String):
    def __init__(self, *args, **kwargs):
        super().__init__()

import sys
from unittest.mock import MagicMock
mock_geo = MagicMock()
mock_geo.Geography = MockGeography
sys.modules["geoalchemy2"] = mock_geo

import pytest
import pytest_asyncio
import asyncio
from typing import Generator, AsyncGenerator
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
import fakeredis
from app.main import app
from app.db.session import get_db
from app.core.config import settings

# Test database URL - using sqlite with StaticPool for in-memory testing
TEST_DATABASE_URL = "sqlite://"

@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    """Provides a clean SQLModel session for each test."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest_asyncio.fixture(name="client")
async def client_fixture(session: Session) -> AsyncGenerator[AsyncClient, None]:
    """Provides an AsyncClient for testing FastAPI endpoints."""
    def get_session_override():
        return session

    app.dependency_overrides[get_db] = get_session_override
    
    # Use ASGITransport for testing the app directly without a real server
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest_asyncio.fixture(name="mock_redis")
async def mock_redis_fixture(monkeypatch):
    """Mocks Redis client using fakeredis."""
    mock_redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    
    # Monkeypatch the redis_client in health.py
    import app.api.v1.health as health_module
    monkeypatch.setattr(health_module, "redis_client", mock_redis)
    
    return mock_redis

@pytest.fixture(scope="session")
def event_loop():
    """Custom event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
