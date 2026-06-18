from jwt import PyJWKClient

from app.core.config import settings

# One PyJWKClient per issuer — keyed by issuer URL.
# PyJWKClient caches signing keys in memory and refreshes on unknown kid.
_jwks_clients: dict[str, PyJWKClient] = {}


def get_jwks_client_for_issuer(issuer: str) -> PyJWKClient:
    """Return (and lazily init) a cached JWKS client for the given issuer.

    For the primary AUTH_OIDC_ISSUER the explicit AUTH_OIDC_JWKS_URL is used
    when set (backwards compatibility).  All other issuers use the Keycloak
    convention: {issuer}/protocol/openid-connect/certs.
    """
    global _jwks_clients
    if issuer not in _jwks_clients:
        if issuer == settings.AUTH_OIDC_ISSUER and settings.AUTH_OIDC_JWKS_URL:
            jwks_url = settings.AUTH_OIDC_JWKS_URL
        else:
            jwks_url = f"{issuer}/protocol/openid-connect/certs"
        _jwks_clients[issuer] = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_clients[issuer]


def get_jwks_client() -> PyJWKClient:
    """Single-issuer convenience accessor.  Kept for backwards compatibility."""
    if not settings.AUTH_OIDC_ISSUER:
        raise RuntimeError("AUTH_OIDC_ISSUER is required when AUTH_OIDC_ENABLED=true")
    return get_jwks_client_for_issuer(settings.AUTH_OIDC_ISSUER)


def reset_jwks_client() -> None:
    """Reset all JWKS clients.  Used in tests to inject settings changes."""
    global _jwks_clients
    _jwks_clients = {}
