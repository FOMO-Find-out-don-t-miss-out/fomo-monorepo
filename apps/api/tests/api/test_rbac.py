"""API-level tests for RBAC role dependencies (FOMO-149).

Two test strategies:
1. Role-isolation: override require_authenticated_user to inject a User with
   a specific system_role — tests role hierarchy without a JWT or live DB user.
2. Full-chain: create a DB user with a known role, use auth_overrides + JWT —
   tests that system_role is preserved across identity sync.

No live Keycloak calls are made.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.core.security.rbac import require_authenticated_user
from app.main import app
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient
from sqlmodel import Session

from packages.domain.models.user import User, UserSystemRole
from tests.api.conftest import sign_token

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _inject_role(role: UserSystemRole) -> User:
    """Override require_authenticated_user to return a user with the given role.

    The override is cleared by the client fixture teardown (dependency_overrides.clear()).
    """
    user = User(id=uuid4(), external_id="rbac-test-sub", email="rbac@example.com", system_role=role)
    app.dependency_overrides[require_authenticated_user] = lambda: user
    return user


# ---------------------------------------------------------------------------
# 401 — unauthenticated (no token, OIDC enabled)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_check_no_token_returns_401(client: AsyncClient, auth_overrides: None) -> None:
    """Missing token must return 401 from the underlying auth dependency."""
    response = await client.get("/api/v1/identity/admin-check")
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


# ---------------------------------------------------------------------------
# require_authenticated_user — any role is accepted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_default_user_can_access_authenticated_user_endpoint(
    client: AsyncClient,
) -> None:
    """A user with the default 'user' role must pass require_authenticated_user."""
    _inject_role(UserSystemRole.user)
    response = await client.get("/api/v1/identity/moderator-check")
    # moderator-check accepts moderator+ but not plain user → 403 proves auth passed
    # (401 would mean not authenticated; 403 proves authenticated but wrong role)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# require_admin
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_role_can_access_admin_check(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.admin)
    response = await client.get("/api/v1/identity/admin-check")
    assert response.status_code == 200
    assert response.json()["system_role"] == "admin"


@pytest.mark.asyncio
async def test_manager_role_cannot_access_admin_check(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.manager)
    response = await client.get("/api/v1/identity/admin-check")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_user_role_cannot_access_admin_check(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.user)
    response = await client.get("/api/v1/identity/admin-check")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# require_manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_access_manager_check(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.admin)
    response = await client.get("/api/v1/identity/manager-check")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_manager_can_access_manager_check(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.manager)
    response = await client.get("/api/v1/identity/manager-check")
    assert response.status_code == 200
    assert response.json()["system_role"] == "manager"


@pytest.mark.asyncio
async def test_moderator_cannot_access_manager_check(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.moderator)
    response = await client.get("/api/v1/identity/manager-check")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_user_role_cannot_access_manager_check(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.user)
    response = await client.get("/api/v1/identity/manager-check")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# require_moderator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_access_moderator_check(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.admin)
    response = await client.get("/api/v1/identity/moderator-check")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_manager_can_access_moderator_check(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.manager)
    response = await client.get("/api/v1/identity/moderator-check")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_moderator_can_access_moderator_check(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.moderator)
    response = await client.get("/api/v1/identity/moderator-check")
    assert response.status_code == 200
    assert response.json()["system_role"] == "moderator"


@pytest.mark.asyncio
async def test_user_role_cannot_access_moderator_check(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.user)
    response = await client.get("/api/v1/identity/moderator-check")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# require_service — standalone, non-hierarchical
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_role_can_access_service_check(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.service)
    response = await client.get("/api/v1/identity/service-check")
    assert response.status_code == 200
    assert response.json()["system_role"] == "service"


@pytest.mark.asyncio
async def test_admin_cannot_access_service_check(client: AsyncClient) -> None:
    """Admin is NOT a substitute for service — separate machine credentials required."""
    _inject_role(UserSystemRole.admin)
    response = await client.get("/api/v1/identity/service-check")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_user_role_cannot_access_service_check(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.user)
    response = await client.get("/api/v1/identity/service-check")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Full-chain: system_role preserved across identity sync
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_system_role_preserved_after_repeated_sync(
    client: AsyncClient,
    auth_overrides: None,
    rsa_private_key: rsa.RSAPrivateKey,
    session: Session,
) -> None:
    """Calling /users/me multiple times must not overwrite an assigned system_role."""
    admin_user = User(
        external_id="rbac-sync-sub",
        email="admin-sync@example.com",
        system_role=UserSystemRole.admin,
    )
    session.add(admin_user)
    session.commit()

    token = sign_token(rsa_private_key, sub="rbac-sync-sub")
    headers = {"Authorization": f"Bearer {token}"}

    r1 = await client.get("/api/v1/users/me", headers=headers)
    r2 = await client.get("/api/v1/users/me", headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["system_role"] == "admin"
    assert r2.json()["system_role"] == "admin"


@pytest.mark.asyncio
async def test_users_me_returns_system_role_for_new_user(
    client: AsyncClient,
    auth_overrides: None,
    rsa_private_key: rsa.RSAPrivateKey,
) -> None:
    """Newly created users must have system_role='user' (the default)."""
    token = sign_token(rsa_private_key, sub="rbac-new-user-sub")
    response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["system_role"] == "user"
