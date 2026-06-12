"""RBAC route protection tests (FOMO-150).

Verifies that moderation and ingestion routers enforce access control:
  - unauthenticated → 401
  - wrong role     → 403
  - correct role   → 2xx

Also verifies public discovery routes remain accessible without authentication.

All tests are offline; no live Keycloak calls are made.
Role injection reuses the _inject_role pattern from test_rbac.py via
app.dependency_overrides[require_authenticated_user].
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.core.security.rbac import require_authenticated_user
from app.main import app
from httpx import AsyncClient

from packages.domain.models.user import User, UserSystemRole


def _inject_role(role: UserSystemRole) -> User:
    """Override require_authenticated_user for the duration of the test."""
    user = User(id=uuid4(), external_id=f"{role.value}-rbac150-sub", system_role=role)
    app.dependency_overrides[require_authenticated_user] = lambda: user
    return user


# ---------------------------------------------------------------------------
# Moderation router — GET /moderation/pending-events (representative route)
# ---------------------------------------------------------------------------

MOD_URL = "/api/v1/moderation/pending-events"


@pytest.mark.asyncio
async def test_moderation_unauthenticated_returns_401(
    client: AsyncClient, auth_overrides: None
) -> None:
    """No token must produce 401 on moderation routes."""
    response = await client.get(MOD_URL)
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_moderation_normal_user_returns_403(client: AsyncClient) -> None:
    """system_role=user must be denied access to moderation routes."""
    _inject_role(UserSystemRole.user)
    response = await client.get(MOD_URL)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_moderation_service_role_returns_403(client: AsyncClient) -> None:
    """system_role=service must NOT be able to access moderation routes."""
    _inject_role(UserSystemRole.service)
    response = await client.get(MOD_URL)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_moderation_moderator_returns_200(client: AsyncClient) -> None:
    """system_role=moderator must have access to moderation routes."""
    _inject_role(UserSystemRole.moderator)
    response = await client.get(MOD_URL)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_moderation_manager_returns_200(client: AsyncClient) -> None:
    """system_role=manager must have access to moderation routes (manager > moderator)."""
    _inject_role(UserSystemRole.manager)
    response = await client.get(MOD_URL)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_moderation_admin_returns_200(client: AsyncClient) -> None:
    """system_role=admin must have access to moderation routes (admin > manager > moderator)."""
    _inject_role(UserSystemRole.admin)
    response = await client.get(MOD_URL)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Ingestion router — POST /ingestion/run-scraper (representative route)
# Returns 202 immediately; background task is not executed synchronously.
# ---------------------------------------------------------------------------

INGEST_URL = "/api/v1/ingestion/run-scraper"


@pytest.mark.asyncio
async def test_ingestion_unauthenticated_returns_401(
    client: AsyncClient, auth_overrides: None
) -> None:
    """No token must produce 401 on ingestion routes."""
    response = await client.post(INGEST_URL)
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_ingestion_normal_user_returns_403(client: AsyncClient) -> None:
    """system_role=user must be denied access to ingestion routes."""
    _inject_role(UserSystemRole.user)
    response = await client.post(INGEST_URL)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ingestion_moderator_returns_403(client: AsyncClient) -> None:
    """system_role=moderator must NOT access ingestion routes (service only)."""
    _inject_role(UserSystemRole.moderator)
    response = await client.post(INGEST_URL)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ingestion_manager_returns_403(client: AsyncClient) -> None:
    """system_role=manager must NOT access ingestion routes (service only)."""
    _inject_role(UserSystemRole.manager)
    response = await client.post(INGEST_URL)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ingestion_admin_returns_403(client: AsyncClient) -> None:
    """system_role=admin must NOT access ingestion routes.

    Admin is NOT a substitute for service credentials — use a dedicated
    service account for the harvester/n8n pipeline.
    """
    _inject_role(UserSystemRole.admin)
    response = await client.post(INGEST_URL)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ingestion_service_returns_202(client: AsyncClient) -> None:
    """system_role=service must be allowed to trigger the scraper pipeline."""
    _inject_role(UserSystemRole.service)
    response = await client.post(INGEST_URL)
    assert response.status_code == 202
    assert "Scraper started" in response.json()["message"]


# ---------------------------------------------------------------------------
# Public routes — must remain accessible without any authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_public_event_detail_not_blocked_by_auth(client: AsyncClient) -> None:
    """GET /events/{id} must not require authentication.

    404 (event not found) proves the route was reached and processed;
    401 would indicate auth is mistakenly required.
    """
    response = await client.get(f"/api/v1/events/{uuid4()}")
    assert response.status_code == 404  # not 401 — route is public


@pytest.mark.asyncio
async def test_public_health_not_blocked_by_auth(client: AsyncClient) -> None:
    """Health endpoint must remain public."""
    response = await client.get("/api/v1/health")
    assert response.status_code not in (401, 403)


@pytest.mark.asyncio
async def test_public_identity_me_still_requires_auth(
    client: AsyncClient, auth_overrides: None
) -> None:
    """/identity/me is deliberately protected — confirm it still returns 401 without a token."""
    response = await client.get("/api/v1/identity/me")
    assert response.status_code == 401
