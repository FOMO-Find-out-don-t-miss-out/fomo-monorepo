"""Shared auth fixtures for API-level tests (FOMO-147 / FOMO-148 / FOMO-150).

All JWT signing is done offline with a locally generated RSA key pair.
No live Keycloak calls are made.

Role-injection fixtures (moderator_auth, service_auth) override
require_authenticated_user so existing tests pass without carrying JWTs.
The client fixture clears dependency_overrides on teardown.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import jwt
import pytest
from app.core.security.rbac import require_authenticated_user
from app.main import app
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from packages.domain.models.user import User, UserSystemRole

TEST_ISSUER = "https://test.example.com/realms/test-realm"
TEST_AZP = "test-client"


# ---------------------------------------------------------------------------
# RSA key pair — session-scoped, generated once per test run
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


def sign_token(
    private_key: rsa.RSAPrivateKey,
    *,
    sub: str = "user-abc123",
    issuer: str = TEST_ISSUER,
    azp: str = TEST_AZP,
    aud: str | list[str] | None = None,
    expired: bool = False,
    extra: dict | None = None,
) -> str:
    """Sign a test JWT with the supplied RSA private key."""
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
# Settings + JWKS mock fixture
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
    import app.core.security.jwks as jwks_module

    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ENABLED", True)
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ISSUER", TEST_ISSUER)
    monkeypatch.setattr(
        config_module.settings,
        "AUTH_OIDC_JWKS_URL",
        "https://test.example.com/.well-known/jwks.json",
    )
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ALLOWED_AZP", TEST_AZP)
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_ALLOWED_AUDIENCES", "")
    monkeypatch.setattr(config_module.settings, "AUTH_OIDC_EXTRA_ISSUERS", "")

    mock_signing_key = MagicMock()
    mock_signing_key.key = rsa_public_key

    mock_jwks_client = MagicMock()
    mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

    # Patch the per-issuer JWKS lookup in the validator's own namespace
    # (jwt_validator imports it directly, so we must patch where it's bound).
    monkeypatch.setattr(validator_module, "get_jwks_client_for_issuer", lambda _issuer: mock_jwks_client)
    jwks_module.reset_jwks_client()


# ---------------------------------------------------------------------------
# Role-injection fixtures for protected route tests (FOMO-150)
# ---------------------------------------------------------------------------
# These fixtures override require_authenticated_user at the FastAPI DI level so
# that existing functional tests keep working after RBAC was applied to routers.
# The client fixture's dependency_overrides.clear() cleans up on teardown.
# ---------------------------------------------------------------------------


def _make_user(role: UserSystemRole) -> User:
    return User(id=uuid4(), external_id=f"{role.value}-test-sub", system_role=role)


@pytest.fixture
def moderator_auth() -> Generator[None, None, None]:
    """Inject a moderator user into the dependency graph.

    Use via pytestmark or as a direct fixture argument.
    Satisfies require_moderator, require_authenticated_user, and any dependency
    that chains from require_authenticated_user.
    """
    app.dependency_overrides[require_authenticated_user] = lambda: _make_user(
        UserSystemRole.moderator
    )
    yield
    app.dependency_overrides.pop(require_authenticated_user, None)


@pytest.fixture
def service_auth() -> Generator[None, None, None]:
    """Inject a service user into the dependency graph.

    Use via pytestmark or as a direct fixture argument.
    Satisfies require_service and require_authenticated_user.
    """
    app.dependency_overrides[require_authenticated_user] = lambda: _make_user(
        UserSystemRole.service
    )
    yield
    app.dependency_overrides.pop(require_authenticated_user, None)
