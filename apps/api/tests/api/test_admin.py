"""Admin user management endpoint tests (FOMO-157, FOMO-161).

Covers:
  GET  /api/v1/admin/users                     — list users
  PATCH /api/v1/admin/users/{id}/system-role   — update role
  POST  /api/v1/admin/users/invite             — invite / create user

Test strategy:
  - Role-isolation: override require_authenticated_user to inject a caller
    without hitting a real Keycloak/JWT chain.
  - DB tests: create users in the session fixture, verify they appear in
    the list and that role updates persist.
  - Auth tests: use auth_overrides fixture to test 401 for missing token.
  - Keycloak Admin: override get_keycloak_admin_service with an AsyncMock.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.core.security.rbac import require_authenticated_user
from app.main import app
from app.services.keycloak_admin_service import get_keycloak_admin_service
from httpx import AsyncClient
from sqlmodel import Session

from packages.domain.models.user import Profile, User, UserSystemRole

USERS_URL = "/api/v1/admin/users"
INVITE_URL = "/api/v1/admin/users/invite"


def _inject_role(role: UserSystemRole) -> User:
    """Override require_authenticated_user for the caller in this test."""
    user = User(id=uuid4(), external_id=f"{role.value}-admin-test-sub", system_role=role)
    app.dependency_overrides[require_authenticated_user] = lambda: user
    return user


def _mock_keycloak(
    *,
    kc_user_id: str = "kc-user-uuid-abc",
    was_created: bool = True,
) -> MagicMock:
    """Override get_keycloak_admin_service with an AsyncMock."""
    svc = MagicMock()
    svc.get_or_create_user = AsyncMock(return_value=(kc_user_id, was_created))
    svc.get_all_user_external_ids = AsyncMock(return_value={kc_user_id})
    app.dependency_overrides[get_keycloak_admin_service] = lambda: svc
    return svc


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
        "identity_status",
    )
    for field in required_fields:
        assert field in item, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_list_users_identity_status_unknown_without_keycloak(
    client: AsyncClient, session: Session
) -> None:
    """When Keycloak Admin is not configured, identity_status defaults to 'unknown'."""
    user = User(id=uuid4(), external_id="sub-no-kc", system_role=UserSystemRole.user)
    session.add(user)
    session.commit()

    _inject_role(UserSystemRole.admin)
    # No Keycloak mock — service not configured in test env
    response = await client.get(USERS_URL)
    assert response.status_code == 200
    assert response.json()[0]["identity_status"] == "unknown"


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


# ---------------------------------------------------------------------------
# POST /api/v1/admin/users/invite
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invite_user_unauthenticated_returns_401(
    client: AsyncClient, auth_overrides: None
) -> None:
    response = await client.post(
        INVITE_URL, json={"email": "new@example.com", "system_role": "moderator"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [UserSystemRole.user, UserSystemRole.moderator, UserSystemRole.manager, UserSystemRole.service],
)
async def test_invite_user_non_admin_returns_403(client: AsyncClient, role: UserSystemRole) -> None:
    _inject_role(role)
    response = await client.post(
        INVITE_URL, json={"email": "new@example.com", "system_role": "moderator"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_invite_user_creates_keycloak_and_fomo_user(
    client: AsyncClient, session: Session
) -> None:
    """Admin can invite a brand-new user; both Keycloak and FOMO records are created."""
    kc_id = str(uuid4())
    _inject_role(UserSystemRole.admin)
    _mock_keycloak(kc_user_id=kc_id, was_created=True)

    response = await client.post(
        INVITE_URL,
        json={"email": "invited@example.com", "system_role": "moderator"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "invited@example.com"
    assert data["system_role"] == "moderator"
    assert data["external_id"] == kc_id
    assert data["keycloak_created"] is True
    assert data["identity_status"] == "active"
    assert data["username"] is not None

    # Verify FOMO DB record was created
    user = session.exec(
        __import__("sqlmodel").select(User).where(User.external_id == kc_id)
    ).first()
    assert user is not None
    assert user.system_role == UserSystemRole.moderator


@pytest.mark.asyncio
async def test_invite_user_existing_keycloak_user_creates_fomo_record(
    client: AsyncClient, session: Session
) -> None:
    """When Keycloak user already exists, only the FOMO record is created."""
    kc_id = str(uuid4())
    _inject_role(UserSystemRole.admin)
    _mock_keycloak(kc_user_id=kc_id, was_created=False)

    response = await client.post(
        INVITE_URL,
        json={"email": "existing-kc@example.com", "system_role": "admin"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["keycloak_created"] is False
    assert data["system_role"] == "admin"


@pytest.mark.asyncio
async def test_invite_user_existing_fomo_user_returns_409(
    client: AsyncClient, session: Session
) -> None:
    """Inviting an email already registered in FOMO returns 409."""
    kc_id = str(uuid4())
    existing = User(
        id=uuid4(), external_id=kc_id, email="taken@example.com", system_role=UserSystemRole.user
    )
    session.add(existing)
    session.commit()

    _inject_role(UserSystemRole.admin)
    _mock_keycloak(kc_user_id=kc_id, was_created=False)

    response = await client.post(
        INVITE_URL,
        json={"email": "taken@example.com", "system_role": "moderator"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_invite_user_duplicate_keycloak_id_returns_409(
    client: AsyncClient, session: Session
) -> None:
    """409 when FOMO already has a user mapped to the returned Keycloak ID."""
    kc_id = str(uuid4())
    existing = User(
        id=uuid4(), external_id=kc_id, email="other@example.com", system_role=UserSystemRole.user
    )
    session.add(existing)
    session.commit()

    _inject_role(UserSystemRole.admin)
    _mock_keycloak(kc_user_id=kc_id, was_created=False)

    response = await client.post(
        INVITE_URL,
        json={"email": "different@example.com", "system_role": "moderator"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_invite_user_service_role_rejected_422(client: AsyncClient) -> None:
    """service role must be rejected at the request validation level.

    The Keycloak service is mocked to prevent a 503 from masking the 422 —
    FastAPI may resolve endpoint dependencies concurrently with body parsing,
    so we ensure the service doesn't raise first.
    """
    _inject_role(UserSystemRole.admin)
    _mock_keycloak()  # prevent 503 so Pydantic validation 422 is returned
    response = await client.post(
        INVITE_URL,
        json={"email": "bot@example.com", "system_role": "service"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invite_user_invalid_email_rejected_422(client: AsyncClient) -> None:
    _inject_role(UserSystemRole.admin)
    _mock_keycloak()  # prevent 503 so Pydantic validation 422 is returned
    response = await client.post(
        INVITE_URL,
        json={"email": "not-an-email", "system_role": "moderator"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invite_user_keycloak_not_configured_returns_503(client: AsyncClient) -> None:
    """When KEYCLOAK_ADMIN_* env vars are absent, invite returns 503."""
    _inject_role(UserSystemRole.admin)
    # Ensure no override is in place — rely on settings not being configured in tests
    app.dependency_overrides.pop(get_keycloak_admin_service, None)

    response = await client.post(
        INVITE_URL,
        json={"email": "someone@example.com", "system_role": "moderator"},
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_invite_user_email_normalised_to_lowercase(
    client: AsyncClient, session: Session
) -> None:
    """Email is normalised to lowercase before storage and Keycloak lookup."""
    kc_id = str(uuid4())
    _inject_role(UserSystemRole.admin)
    _mock_keycloak(kc_user_id=kc_id, was_created=True)

    response = await client.post(
        INVITE_URL,
        json={"email": "Upper.Case@Example.COM", "system_role": "user"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "upper.case@example.com"


@pytest.mark.asyncio
async def test_invite_user_response_does_not_expose_secrets(
    client: AsyncClient, session: Session
) -> None:
    """Response must not contain tokens, passwords, or Keycloak admin credentials."""
    kc_id = str(uuid4())
    _inject_role(UserSystemRole.admin)
    _mock_keycloak(kc_user_id=kc_id, was_created=True)

    response = await client.post(
        INVITE_URL,
        json={"email": "safe@example.com", "system_role": "user"},
    )
    assert response.status_code == 201
    data = response.json()
    for sensitive_key in ("password", "token", "secret", "client_secret"):
        assert sensitive_key not in data
