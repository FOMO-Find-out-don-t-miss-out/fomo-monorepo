"""Tests for OIDC JWT authentication (FOMO-147).

All tests are offline — no live Keycloak calls are made.
Test JWTs are signed with a locally generated RSA key pair; JWKS fetching is
mocked at the jwt_validator module boundary so PyJWT performs real RS256
signature verification against the test key.

Fixtures (rsa_private_key, rsa_public_key, auth_overrides, sign_token) are
defined in tests/api/conftest.py and shared with other API test modules.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient

from tests.api.conftest import TEST_AZP, TEST_ISSUER, sign_token

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
    token = sign_token(rsa_private_key, expired=True)
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
    token = sign_token(rsa_private_key)
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
    token = sign_token(rsa_private_key, issuer="https://evil.example.com/realms/bad")
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
    token = sign_token(rsa_private_key, azp="some-other-client")
    response = await client.get(
        "/api/v1/identity/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Audience validation (when configured)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Multi-client AZP (FOMO-159) — comma-separated AUTH_OIDC_ALLOWED_AZP
# ---------------------------------------------------------------------------

_SECOND_AZP = "fomo-n8n-ingestion"
_MULTI_AZP = f"{TEST_AZP},{_SECOND_AZP}"


def _make_multi_azp_overrides(
    monkeypatch: pytest.MonkeyPatch,
    rsa_public_key: object,
    *,
    allowed_azp: str = _MULTI_AZP,
) -> None:
    """Apply settings + JWKS mock for multi-AZP tests."""
    import app.core.config as config_module
    import app.core.security.jwt_validator as validator_module

    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ENABLED", True)
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ISSUER", TEST_ISSUER)
    monkeypatch.setattr(
        config_module.settings,
        "AUTH_OIDC_JWKS_URL",
        "https://test.example.com/.well-known/jwks.json",
    )
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ALLOWED_AZP", allowed_azp)
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ALLOWED_AUDIENCES", "")

    mock_signing_key = MagicMock()
    mock_signing_key.key = rsa_public_key
    mock_jwks_client = MagicMock()
    mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
    monkeypatch.setattr(
        validator_module,
        "get_jwks_client_for_issuer",
        lambda _issuer: mock_jwks_client,
    )


@pytest.mark.asyncio
async def test_multi_azp_first_client_accepted(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    rsa_private_key: rsa.RSAPrivateKey,
) -> None:
    """First client in a comma-separated AZP list must be accepted."""
    _make_multi_azp_overrides(monkeypatch, rsa_private_key.public_key())
    token = sign_token(rsa_private_key, azp=TEST_AZP)
    resp = await client.get("/api/v1/identity/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["azp"] == TEST_AZP


@pytest.mark.asyncio
async def test_multi_azp_second_client_accepted(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    rsa_private_key: rsa.RSAPrivateKey,
) -> None:
    """Second client in a comma-separated AZP list must be accepted."""
    _make_multi_azp_overrides(monkeypatch, rsa_private_key.public_key())
    token = sign_token(rsa_private_key, azp=_SECOND_AZP)
    resp = await client.get("/api/v1/identity/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["azp"] == _SECOND_AZP


@pytest.mark.asyncio
async def test_multi_azp_disallowed_client_rejected(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    rsa_private_key: rsa.RSAPrivateKey,
) -> None:
    """A client not in the AZP list must be rejected with 401."""
    _make_multi_azp_overrides(monkeypatch, rsa_private_key.public_key())
    token = sign_token(rsa_private_key, azp="some-unauthorized-client")
    resp = await client.get("/api/v1/identity/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_multi_azp_whitespace_in_config_handled(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    rsa_private_key: rsa.RSAPrivateKey,
) -> None:
    """Whitespace around comma-separated AZP values must be trimmed."""
    _make_multi_azp_overrides(
        monkeypatch,
        rsa_private_key.public_key(),
        allowed_azp=f" {TEST_AZP} , {_SECOND_AZP} ",
    )
    token = sign_token(rsa_private_key, azp=_SECOND_AZP)
    resp = await client.get("/api/v1/identity/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_multi_azp_empty_entries_do_not_allow_empty_azp(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    rsa_private_key: rsa.RSAPrivateKey,
) -> None:
    """Empty entries in a comma-separated AZP config must not grant access."""
    _make_multi_azp_overrides(
        monkeypatch,
        rsa_private_key.public_key(),
        allowed_azp=f"{TEST_AZP},,{_SECOND_AZP},",
    )
    # A token whose azp happens to be an empty string must not be accepted
    token = sign_token(rsa_private_key, azp="", extra={"azp": ""})
    resp = await client.get("/api/v1/identity/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


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
    monkeypatch.setattr(
        validator_module,
        "get_jwks_client_for_issuer",
        lambda _issuer: mock_jwks_client,
    )

    # Token without required aud → 401
    token_no_aud = sign_token(rsa_private_key)
    resp = await client.get(
        "/api/v1/identity/me", headers={"Authorization": f"Bearer {token_no_aud}"}
    )
    assert resp.status_code == 401

    # Token with correct aud → 200
    token_with_aud = sign_token(rsa_private_key, aud="test-client")
    resp = await client.get(
        "/api/v1/identity/me", headers={"Authorization": f"Bearer {token_with_aud}"}
    )
    assert resp.status_code == 200
    assert resp.json()["audience"] == "test-client"
