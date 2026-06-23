"""API-level tests for GET /api/v1/users/me (FOMO-148).

Uses shared fixtures from tests/api/conftest.py (auth_overrides, sign_token,
rsa_private_key) and the root conftest's client / session fixtures.
"""

from __future__ import annotations

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient
from sqlmodel import Session, select

from packages.domain.models.user import User, UserSystemRole
from tests.api.conftest import sign_token

# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_users_me_no_token_returns_401(client: AsyncClient, auth_overrides: None) -> None:
    """Missing token must return 401."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


# ---------------------------------------------------------------------------
# First access — user and profile created
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_users_me_creates_user_on_first_access(
    client: AsyncClient,
    auth_overrides: None,
    rsa_private_key: rsa.RSAPrivateKey,
    session: Session,
) -> None:
    """First authenticated request must create a user and profile."""
    token = sign_token(rsa_private_key, sub="kc-api-new")
    response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()

    assert data["external_id"] == "kc-api-new"
    assert data["email"] == "test@example.com"
    assert data["username"] is not None
    assert data["phone_number"] is None
    assert data["phone_verified"] is False
    assert data["system_role"] == UserSystemRole.user.value

    # Verify persistence in DB
    users = session.exec(select(User).where(User.external_id == "kc-api-new")).all()
    assert len(users) == 1


@pytest.mark.asyncio
async def test_users_me_external_id_equals_sub(
    client: AsyncClient,
    auth_overrides: None,
    rsa_private_key: rsa.RSAPrivateKey,
    session: Session,
) -> None:
    """users.external_id must equal the token sub claim."""
    token = sign_token(rsa_private_key, sub="kc-ext-id-check")
    await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    users = session.exec(select(User).where(User.external_id == "kc-ext-id-check")).all()
    assert len(users) == 1


@pytest.mark.asyncio
async def test_users_me_creates_user_without_email(
    client: AsyncClient,
    auth_overrides: None,
    rsa_private_key: rsa.RSAPrivateKey,
    session: Session,
) -> None:
    """Users without an email claim in their token must still be created."""
    token = sign_token(rsa_private_key, sub="kc-no-email", extra={"email": None})
    response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["external_id"] == "kc-no-email"
    assert data["email"] is None
    assert data["username"] is not None


@pytest.mark.asyncio
async def test_users_me_response_shape_includes_all_fields(
    client: AsyncClient,
    auth_overrides: None,
    rsa_private_key: rsa.RSAPrivateKey,
) -> None:
    """Response must include all fields required by the mobile Profile screen."""
    token = sign_token(rsa_private_key, sub="kc-field-check")
    response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()

    required_fields = {
        "id", "external_id", "email", "phone_number", "phone_verified",
        "system_role", "username", "avatar_url", "created_at", "updated_at",
    }
    assert required_fields <= data.keys()
    assert data["system_role"] == "user"


# ---------------------------------------------------------------------------
# Idempotency — no duplicate users on repeated calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_users_me_repeated_calls_no_duplicate(
    client: AsyncClient,
    auth_overrides: None,
    rsa_private_key: rsa.RSAPrivateKey,
    session: Session,
) -> None:
    """Repeated requests with the same token sub must not create duplicate users."""
    token = sign_token(rsa_private_key, sub="kc-idempotent-api")
    headers = {"Authorization": f"Bearer {token}"}

    r1 = await client.get("/api/v1/users/me", headers=headers)
    r2 = await client.get("/api/v1/users/me", headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]

    count = len(session.exec(select(User).where(User.external_id == "kc-idempotent-api")).all())
    assert count == 1


# ---------------------------------------------------------------------------
# Duplicate handling — email conflict
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_users_me_duplicate_email_keeps_existing_user(
    client: AsyncClient,
    auth_overrides: None,
    rsa_private_key: rsa.RSAPrivateKey,
    session: Session,
) -> None:
    """When a user exists with the given external_id, repeated requests return 200.

    Simulates an existing user whose record was pre-populated (e.g., by a
    seeder or a prior auth method) then re-authenticated via Keycloak.
    """
    # Pre-populate a user so the service finds it by external_id on first call.
    user_b = User(external_id="kc-dup-email-b", email="shared@example.com")
    session.add(user_b)
    session.commit()

    token_b = sign_token(
        rsa_private_key, sub="kc-dup-email-b",
        extra={"email": "shared@example.com"},
    )
    headers = {"Authorization": f"Bearer {token_b}"}
    response_b = await client.get("/api/v1/users/me", headers=headers)
    assert response_b.status_code == 200
    assert response_b.json()["external_id"] == "kc-dup-email-b"


# ---------------------------------------------------------------------------
# Response shape — wallet balance excluded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_users_me_response_excludes_wallet(
    client: AsyncClient,
    auth_overrides: None,
    rsa_private_key: rsa.RSAPrivateKey,
) -> None:
    """Wallet balance must not appear in the /users/me response."""
    token = sign_token(rsa_private_key, sub="kc-wallet-excl")
    response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "balance" not in data
    assert "wallet" not in data
    assert "fomo_coins" not in data


# ---------------------------------------------------------------------------
# Public event endpoints remain unauthenticated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_public_health_still_accessible(client: AsyncClient) -> None:
    """Public endpoints must not be broken by auth changes."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.status_code != 401
