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
# Email reconciliation — existing email / different external_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_users_me_existing_email_new_sub_returns_200(
    client: AsyncClient,
    auth_overrides: None,
    rsa_private_key: rsa.RSAPrivateKey,
    session: Session,
) -> None:
    """Staging root cause regression test.

    A user already exists with email=reconcile@example.com and
    external_id=old-dashboard-sub (from a prior login or seeded data).
    A new Keycloak token arrives with the same email but sub=new-mobile-sub.

    Expected: /users/me returns 200 for the EXISTING user, no 500, no duplicate.
    """
    existing = User(
        external_id="old-dashboard-sub",
        email="reconcile@example.com",
    )
    session.add(existing)
    session.commit()
    session.refresh(existing)
    existing_id = str(existing.id)

    token = sign_token(
        rsa_private_key,
        sub="new-mobile-sub",
        extra={"email": "reconcile@example.com"},
    )
    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    # Must resolve to the PRE-EXISTING user row, not create a duplicate.
    assert data["id"] == existing_id
    assert data["email"] == "reconcile@example.com"

    users = session.exec(
        select(User).where(User.email == "reconcile@example.com")
    ).all()
    assert len(users) == 1


@pytest.mark.asyncio
async def test_users_me_existing_email_new_sub_repeated_stable(
    client: AsyncClient,
    auth_overrides: None,
    rsa_private_key: rsa.RSAPrivateKey,
    session: Session,
) -> None:
    """Repeated calls with mismatched sub keep returning the same user."""
    existing = User(
        external_id="old-sub-for-repeat",
        email="repeat-reconcile@example.com",
    )
    session.add(existing)
    session.commit()
    session.refresh(existing)

    token = sign_token(
        rsa_private_key,
        sub="new-sub-for-repeat",
        extra={"email": "repeat-reconcile@example.com"},
    )
    headers = {"Authorization": f"Bearer {token}"}

    r1 = await client.get("/api/v1/users/me", headers=headers)
    r2 = await client.get("/api/v1/users/me", headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == str(existing.id)
    assert r2.json()["id"] == str(existing.id)


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
