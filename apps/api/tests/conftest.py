# isort: skip_file
import asyncio
import sys
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import MagicMock

import fakeredis
import pytest
import pytest_asyncio
import sqlalchemy
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# --- Pre-import Mocking ---
# We MUST mock geoalchemy2 before app models are imported


class MockGeography(sqlalchemy.String):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Ignore all PostGIS specific arguments like geometry_type, srid etc.
        super().__init__()


mock_geo = MagicMock()
mock_geo.Geography = MockGeography
mock_geo.WKTElement = lambda x, srid: x

mock_elements = MagicMock()
mock_elements.WKTElement = mock_geo.WKTElement

mock_shape = MagicMock()
mock_shape.to_shape = lambda x: MagicMock(x=0, y=0)

sys.modules["geoalchemy2"] = mock_geo
sys.modules["geoalchemy2.elements"] = mock_elements
sys.modules["geoalchemy2.shape"] = mock_shape

# Now imports that might use these
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

# Test database URL - using sqlite with StaticPool for in-memory testing
TEST_DATABASE_URL = "sqlite://"


@pytest.fixture(name="engine", scope="session")
def engine_fixture() -> Generator[sqlalchemy.Engine, None, None]:
    """Provides a session-scoped SQLModel engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine: sqlalchemy.Engine) -> Generator[Session, None, None]:
    """Provides a clean SQLModel session for each test."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest_asyncio.fixture(name="client")
async def client_fixture(session: Session) -> AsyncGenerator[AsyncClient, None]:
    """Provides an AsyncClient for testing FastAPI endpoints."""

    def get_session_override() -> Session:
        return session

    app.dependency_overrides[get_db] = get_session_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(name="mock_redis")
async def mock_redis_fixture(monkeypatch: pytest.MonkeyPatch) -> fakeredis.FakeAsyncRedis:
    """Mocks Redis client using fakeredis."""
    mock_redis = fakeredis.FakeAsyncRedis(decode_responses=True)

    import app.api.v1.health as health_module

    monkeypatch.setattr(health_module, "redis_client", mock_redis)

    return mock_redis


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Custom event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
