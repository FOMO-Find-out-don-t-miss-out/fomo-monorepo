"""Tests for OIDC JWT authentication (FOMO-147).

All tests are offline — no live Keycloak calls are made.
Test JWTs are signed with a locally generated RSA key pair; JWKS fetching is
mocked at the jwt_validator module boundary so PyJWT performs real RS256
signature verification against the test key.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient

TEST_ISSUER = "https://test.example.com/realms/test-realm"
TEST_AZP = "test-client"


# ---------------------------------------------------------------------------
# RSA key fixtures (session-scoped — generated once per test run)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def rsa_private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def rsa_public_key(rsa_private_key: rsa.RSAPrivateKey) -> rsa.RSAPublicKey:
    return rsa_private_key.public_key()


# ---------------------------------------------------------------------------
# Token factory helper
# ---------------------------------------------------------------------------


def _sign_token(
    private_key: rsa.RSAPrivateKey,
    *,
    sub: str = "user-abc123",
    issuer: str = TEST_ISSUER,
    azp: str = TEST_AZP,
    aud: str | list[str] | None = None,
    expired: bool = False,
    extra: dict | None = None,
) -> str:
    now = datetime.now(UTC)
    exp = now - timedelta(seconds=60) if expired else now + timedelta(hours=1)
    payload: dict = {
        "sub": sub,
        "iss": issuer,
        "azp": azp,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "email": "test@example.com",
        "preferred_username": "testuser",
        "name": "Test User",
        "realm_access": {"roles": ["user"]},
    }
    if aud is not None:
        payload["aud"] = aud
    if extra:
        payload.update(extra)

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(payload, pem, algorithm="RS256")


# ---------------------------------------------------------------------------
# Auth settings + JWKS mock fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_overrides(rsa_public_key: rsa.RSAPublicKey, monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch settings and JWKS client for auth tests.

    - AUTH_OIDC_ENABLED=True
    - Issuer and AZP set to test constants
    - JWKS client returns the session-scoped test public key for every token
    """
    import app.core.config as config_module
    import app.core.security.jwt_validator as validator_module

    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ENABLED", True)
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ISSUER", TEST_ISSUER)
    monkeypatch.setattr(
        config_module.settings,
        "AUTH_OIDC_JWKS_URL",
        "https://test.example.com/.well-known/jwks.json",
    )
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ALLOWED_AZP", TEST_AZP)
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ALLOWED_AUDIENCES", "")

    mock_signing_key = MagicMock()
    mock_signing_key.key = rsa_public_key

    mock_jwks_client = MagicMock()
    mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

    monkeypatch.setattr(validator_module, "get_jwks_client", lambda: mock_jwks_client)


# ---------------------------------------------------------------------------
# Public endpoint tests — must remain unauthenticated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_public_health_endpoint_no_token(client: AsyncClient) -> None:
    """Health check must be reachable without a token."""
    response = await client.get("/api/v1/health")
    # Redis will be unhealthy in tests (no mock_redis here) but status is 200
    assert response.status_code == 200
    assert response.status_code != 401


# ---------------------------------------------------------------------------
# Protected endpoint — missing / malformed / expired tokens
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_protected_no_token_returns_401(client: AsyncClient, auth_overrides: None) -> None:
    """Protected endpoint must return 401 when no token is supplied."""
    response = await client.get("/api/v1/identity/me")
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_protected_non_bearer_scheme_returns_401(
    client: AsyncClient, auth_overrides: None
) -> None:
    """Non-Bearer authorization scheme must be rejected with 401."""
    response = await client.get(
        "/api/v1/identity/me",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_malformed_token_returns_401(
    client: AsyncClient, auth_overrides: None
) -> None:
    """A string that is not a valid JWT must be rejected with 401."""
    response = await client.get(
        "/api/v1/identity/me",
        headers={"Authorization": "Bearer notavalidjwtatall"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_expired_token_returns_401(
    client: AsyncClient, auth_overrides: None, rsa_private_key: rsa.RSAPrivateKey
) -> None:
    """Expired token must be rejected with 401."""
    token = _sign_token(rsa_private_key, expired=True)
    response = await client.get(
        "/api/v1/identity/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Protected endpoint — valid token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_protected_valid_token_returns_identity(
    client: AsyncClient, auth_overrides: None, rsa_private_key: rsa.RSAPrivateKey
) -> None:
    """Valid Keycloak-like token must grant access and return identity claims."""
    token = _sign_token(rsa_private_key)
    response = await client.get(
        "/api/v1/identity/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sub"] == "user-abc123"
    assert data["email"] == "test@example.com"
    assert data["preferred_username"] == "testuser"
    assert data["name"] == "Test User"
    assert data["issuer"] == TEST_ISSUER
    assert data["azp"] == TEST_AZP
    assert "user" in data["realm_roles"]


# ---------------------------------------------------------------------------
# Issuer and AZP validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wrong_issuer_returns_401(
    client: AsyncClient, auth_overrides: None, rsa_private_key: rsa.RSAPrivateKey
) -> None:
    """Token issued by a different realm must be rejected with 401."""
    token = _sign_token(rsa_private_key, issuer="https://evil.example.com/realms/bad")
    response = await client.get(
        "/api/v1/identity/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_wrong_azp_returns_401(
    client: AsyncClient, auth_overrides: None, rsa_private_key: rsa.RSAPrivateKey
) -> None:
    """Token with an unauthorized azp (client) must be rejected with 401."""
    token = _sign_token(rsa_private_key, azp="some-other-client")
    response = await client.get(
        "/api/v1/identity/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Audience validation (when configured)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audience_validated_when_configured(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, rsa_private_key: rsa.RSAPrivateKey
) -> None:
    """When allowed audiences are configured, token aud must match."""
    import app.core.config as config_module
    import app.core.security.jwt_validator as validator_module

    rsa_public_key = rsa_private_key.public_key()
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ENABLED", True)
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ISSUER", TEST_ISSUER)
    monkeypatch.setattr(
        config_module.settings,
        "AUTH_OIDC_JWKS_URL",
        "https://test.example.com/.well-known/jwks.json",
    )
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ALLOWED_AZP", TEST_AZP)
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ALLOWED_AUDIENCES", "test-client")

    mock_signing_key = MagicMock()
    mock_signing_key.key = rsa_public_key
    mock_jwks_client = MagicMock()
    mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
    monkeypatch.setattr(validator_module, "get_jwks_client", lambda: mock_jwks_client)

    # Token without required aud → 401
    token_no_aud = _sign_token(rsa_private_key)
    resp = await client.get(
        "/api/v1/identity/me", headers={"Authorization": f"Bearer {token_no_aud}"}
    )
    assert resp.status_code == 401

    # Token with correct aud → 200
    token_with_aud = _sign_token(rsa_private_key, aud="test-client")
    resp = await client.get(
        "/api/v1/identity/me", headers={"Authorization": f"Bearer {token_with_aud}"}
    )
    assert resp.status_code == 200
    assert resp.json()["audience"] == "test-client"
