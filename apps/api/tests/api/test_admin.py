"""Admin user management endpoint tests (FOMO-157).

Covers:
  GET  /api/v1/admin/users        — list users
  PATCH /api/v1/admin/users/{id}/system-role — update role

Test strategy:
  - Role-isolation: override require_authenticated_user to inject a caller
    without hitting a real Keycloak/JWT chain.
  - DB tests: create users in the session fixture, verify they appear in
    the list and that role updates persist.
  - Auth tests: use auth_overrides fixture to test 401 for missing token.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.core.security.rbac import require_authenticated_user
from app.main import app
from httpx import AsyncClient
from sqlmodel import Session

from packages.domain.models.user import Profile, User, UserSystemRole

USERS_URL = "/api/v1/admin/users"


def _inject_role(role: UserSystemRole) -> User:
    """Override require_authenticated_user for the caller in this test."""
    user = User(id=uuid4(), external_id=f"{role.value}-admin-test-sub", system_role=role)
    app.dependency_overrides[require_authenticated_user] = lambda: user
    return user


# ---------------------------------------------------------------------------
# GET /api/v1/admin/users
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_users_unauthenticated_returns_401(
    client: AsyncClient, auth_overrides: None
) -> None:
    response = await client.get(USERS_URL)
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [UserSystemRole.user, UserSystemRole.moderator, UserSystemRole.manager, UserSystemRole.service],
)
async def test_list_users_non_admin_returns_403(client: AsyncClient, role: UserSystemRole) -> None:
    _inject_role(role)
    response = await client.get(USERS_URL)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users_admin_returns_empty_list(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.admin)
    response = await client.get(USERS_URL)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_users_returns_db_users_with_profile_data(
    client: AsyncClient, session: Session
) -> None:
    u1 = User(
        id=uuid4(),
        external_id="sub-alpha",
        email="alpha@example.com",
        system_role=UserSystemRole.moderator,
    )
    u2 = User(
        id=uuid4(),
        external_id="sub-beta",
        email="beta@example.com",
        system_role=UserSystemRole.user,
    )
    p1 = Profile(user_id=u1.id, username="alpha_user")
    session.add(u1)
    session.add(u2)
    session.add(p1)
    session.commit()

    _inject_role(UserSystemRole.admin)
    response = await client.get(USERS_URL)
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2

    alpha = next(d for d in data if d["external_id"] == "sub-alpha")
    assert alpha["username"] == "alpha_user"
    assert alpha["system_role"] == "moderator"
    assert alpha["email"] == "alpha@example.com"

    beta = next(d for d in data if d["external_id"] == "sub-beta")
    assert beta["username"] is None
    assert beta["system_role"] == "user"


@pytest.mark.asyncio
async def test_list_users_response_includes_required_fields(
    client: AsyncClient, session: Session
) -> None:
    user = User(id=uuid4(), external_id="sub-fields-check", system_role=UserSystemRole.user)
    session.add(user)
    session.commit()

    _inject_role(UserSystemRole.admin)
    response = await client.get(USERS_URL)
    assert response.status_code == 200

    item = response.json()[0]
    required_fields = (
        "id",
        "external_id",
        "email",
        "username",
        "avatar_url",
        "system_role",
        "created_at",
        "updated_at",
    )
    for field in required_fields:
        assert field in item, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# PATCH /api/v1/admin/users/{user_id}/system-role
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_role_unauthenticated_returns_401(
    client: AsyncClient, auth_overrides: None
) -> None:
    response = await client.patch(
        f"{USERS_URL}/{uuid4()}/system-role",
        json={"system_role": "moderator"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [UserSystemRole.user, UserSystemRole.moderator, UserSystemRole.manager, UserSystemRole.service],
)
async def test_update_role_non_admin_returns_403(client: AsyncClient, role: UserSystemRole) -> None:
    _inject_role(role)
    response = await client.patch(
        f"{USERS_URL}/{uuid4()}/system-role",
        json={"system_role": "user"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_role_admin_can_update_another_user(
    client: AsyncClient, session: Session
) -> None:
    target = User(id=uuid4(), external_id="sub-target", system_role=UserSystemRole.user)
    session.add(target)
    session.commit()

    _inject_role(UserSystemRole.admin)
    response = await client.patch(
        f"{USERS_URL}/{target.id}/system-role",
        json={"system_role": "moderator"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["system_role"] == "moderator"
    assert data["id"] == str(target.id)


@pytest.mark.asyncio
async def test_update_role_admin_can_assign_service_role(
    client: AsyncClient, session: Session
) -> None:
    target = User(id=uuid4(), external_id="sub-svc-candidate", system_role=UserSystemRole.user)
    session.add(target)
    session.commit()

    _inject_role(UserSystemRole.admin)
    response = await client.patch(
        f"{USERS_URL}/{target.id}/system-role",
        json={"system_role": "service"},
    )
    assert response.status_code == 200
    assert response.json()["system_role"] == "service"


@pytest.mark.asyncio
async def test_update_role_self_demotion_returns_400(client: AsyncClient) -> None:
    caller = _inject_role(UserSystemRole.admin)
    response = await client.patch(
        f"{USERS_URL}/{caller.id}/system-role",
        json={"system_role": "user"},
    )
    assert response.status_code == 400
    assert "demote" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_role_self_to_moderator_returns_400(client: AsyncClient) -> None:
    caller = _inject_role(UserSystemRole.admin)
    response = await client.patch(
        f"{USERS_URL}/{caller.id}/system-role",
        json={"system_role": "moderator"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_role_admin_keeping_own_admin_is_allowed(
    client: AsyncClient, session: Session
) -> None:
    """Updating own role to admin is a no-op and must succeed."""
    caller = _inject_role(UserSystemRole.admin)
    session.add(
        User(id=caller.id, external_id=caller.external_id, system_role=UserSystemRole.admin)
    )
    session.commit()

    response = await client.patch(
        f"{USERS_URL}/{caller.id}/system-role",
        json={"system_role": "admin"},
    )
    assert response.status_code == 200
    assert response.json()["system_role"] == "admin"


@pytest.mark.asyncio
async def test_update_role_user_not_found_returns_404(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.admin)
    response = await client.patch(
        f"{USERS_URL}/{uuid4()}/system-role",
        json={"system_role": "moderator"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_role_invalid_role_returns_422(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.admin)
    response = await client.patch(
        f"{USERS_URL}/{uuid4()}/system-role",
        json={"system_role": "superuser"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_role_response_includes_updated_role(
    client: AsyncClient, session: Session
) -> None:
    target = User(id=uuid4(), external_id="sub-verify-response", system_role=UserSystemRole.user)
    p = Profile(user_id=target.id, username="verify_user")
    session.add(target)
    session.add(p)
    session.commit()

    _inject_role(UserSystemRole.admin)
    response = await client.patch(
        f"{USERS_URL}/{target.id}/system-role",
        json={"system_role": "manager"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["system_role"] == "manager"
    assert data["username"] == "verify_user"
    assert data["external_id"] == "sub-verify-response"
