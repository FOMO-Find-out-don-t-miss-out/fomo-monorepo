import pytest
from app.core.config import Settings
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Settings validator unit tests
# ---------------------------------------------------------------------------


def test_cors_origins_default() -> None:
    s = Settings()
    assert "http://localhost:3000" in s.CORS_ALLOWED_ORIGINS


def test_cors_origins_comma_separated() -> None:
    s = Settings(CORS_ALLOWED_ORIGINS="http://localhost:3000,https://dashboard.staging.fomo-lab.org")  # type: ignore[call-arg]
    assert s.CORS_ALLOWED_ORIGINS == [
        "http://localhost:3000",
        "https://dashboard.staging.fomo-lab.org",
    ]


def test_cors_origins_json_array() -> None:
    s = Settings(CORS_ALLOWED_ORIGINS='["http://localhost:3000","https://dashboard.staging.fomo-lab.org"]')  # type: ignore[call-arg]
    assert "https://dashboard.staging.fomo-lab.org" in s.CORS_ALLOWED_ORIGINS


def test_cors_origins_list_passthrough() -> None:
    s = Settings(CORS_ALLOWED_ORIGINS=["http://localhost:3000"])  # type: ignore[call-arg]
    assert s.CORS_ALLOWED_ORIGINS == ["http://localhost:3000"]


# ---------------------------------------------------------------------------
# Middleware integration tests (via ASGI transport)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cors_allowed_origin_get(client: AsyncClient) -> None:
    """GET from an allowed origin includes Access-Control-Allow-Origin."""
    response = await client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_cors_preflight_allowed_origin(client: AsyncClient) -> None:
    """OPTIONS preflight from an allowed origin returns 200 with CORS headers."""
    response = await client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_cors_disallowed_origin_excluded(client: AsyncClient) -> None:
    """Response for an unlisted origin does not include Access-Control-Allow-Origin."""
    response = await client.get(
        "/api/v1/health",
        headers={"Origin": "https://evil.example.com"},
    )
    assert "access-control-allow-origin" not in response.headers
