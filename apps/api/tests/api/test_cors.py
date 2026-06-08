import json

import pytest
from app.core.config import Settings
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# cors_allowed_origins_list property unit tests
# ---------------------------------------------------------------------------


def test_cors_origins_default() -> None:
    s = Settings()
    assert s.cors_allowed_origins_list == ["http://localhost:3000"]


def test_cors_origins_comma_separated() -> None:
    s = Settings(CORS_ALLOWED_ORIGINS="https://dashboard.staging.fomo-lab.org,http://localhost:3000")  # type: ignore[call-arg]
    assert s.cors_allowed_origins_list == [
        "https://dashboard.staging.fomo-lab.org",
        "http://localhost:3000",
    ]


def test_cors_origins_comma_separated_with_whitespace() -> None:
    raw = "  https://dashboard.staging.fomo-lab.org , http://localhost:3000  "
    s = Settings(CORS_ALLOWED_ORIGINS=raw)  # type: ignore[call-arg]
    assert s.cors_allowed_origins_list == [
        "https://dashboard.staging.fomo-lab.org",
        "http://localhost:3000",
    ]


def test_cors_origins_json_array() -> None:
    val = json.dumps(["https://dashboard.staging.fomo-lab.org", "http://localhost:3000"])
    s = Settings(CORS_ALLOWED_ORIGINS=val)  # type: ignore[call-arg]
    assert s.cors_allowed_origins_list == [
        "https://dashboard.staging.fomo-lab.org",
        "http://localhost:3000",
    ]


def test_cors_origins_single_value() -> None:
    s = Settings(CORS_ALLOWED_ORIGINS="http://localhost:3000")  # type: ignore[call-arg]
    assert s.cors_allowed_origins_list == ["http://localhost:3000"]


def test_cors_origins_empty_string_returns_empty() -> None:
    s = Settings(CORS_ALLOWED_ORIGINS="")  # type: ignore[call-arg]
    assert s.cors_allowed_origins_list == []


def test_cors_origins_empty_entries_dropped() -> None:
    s = Settings(CORS_ALLOWED_ORIGINS="http://localhost:3000,,  ,")  # type: ignore[call-arg]
    assert s.cors_allowed_origins_list == ["http://localhost:3000"]


def test_cors_origins_invalid_json_raises() -> None:
    s = Settings(CORS_ALLOWED_ORIGINS="[not-valid-json")  # type: ignore[call-arg]
    with pytest.raises(json.JSONDecodeError):
        _ = s.cors_allowed_origins_list


def test_cors_origins_json_object_not_array_treated_as_literal() -> None:
    # A JSON object doesn't start with "[", so it is not JSON-parsed.
    # It is treated as a single literal origin string (safe: no crash, no wildcard).
    s = Settings(CORS_ALLOWED_ORIGINS='{"key": "value"}')  # type: ignore[call-arg]
    assert s.cors_allowed_origins_list == ['{"key": "value"}']


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
