# isort: skip_file
import asyncio
import os
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


# ---------------------------------------------------------------------------
# AI provider safety guard
# ---------------------------------------------------------------------------
# All tests run with zero real Gemini calls by default.
# Tests that need AI output must patch ai_extractor._client with their own mock.
# Tests that need the real API must be marked @pytest.mark.integration_ai and
# the caller must set RUN_EXTERNAL_AI_TESTS=true.
# ---------------------------------------------------------------------------

_GUARD_MESSAGE = (
    "External AI call attempted during tests. "
    "Patch app.services.harvester.cleansing.ai_extractor._client with a mock, "
    "or opt in with @pytest.mark.integration_ai + RUN_EXTERNAL_AI_TESTS=true."
)


@pytest.fixture(autouse=True)
def _block_real_ai_client(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replace the live Gemini client with a sentinel that raises on any call.

    Tests that need AI output must supply their own mock via
    ``patch("app.services.harvester.cleansing.ai_extractor._client")``.
    Tests marked ``integration_ai`` are exempt from this guard.
    """
    if request.node.get_closest_marker("integration_ai"):
        return  # integration_ai tests manage their own client and credentials

    import app.services.harvester.cleansing.ai_extractor as ai_mod

    blocker = MagicMock(name="ai_client_guard")
    blocker.chat.completions.create.side_effect = RuntimeError(_GUARD_MESSAGE)
    monkeypatch.setattr(ai_mod, "_client", blocker)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip integration_ai tests unless RUN_EXTERNAL_AI_TESTS=true."""
    run_external_ai = os.getenv("RUN_EXTERNAL_AI_TESTS", "").lower() == "true"
    skip_marker = pytest.mark.skip(
        reason=(
            "integration_ai: opt-in only. "
            "Set RUN_EXTERNAL_AI_TESTS=true and supply GOOGLE_API_KEY to run."
        )
    )
    for item in items:
        if item.get_closest_marker("integration_ai") and not run_external_ai:
            item.add_marker(skip_marker, append=False)
