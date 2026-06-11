from jwt import PyJWKClient

from app.core.config import settings

_jwks_client: PyJWKClient | None = None


def get_jwks_client() -> PyJWKClient:
    """Return (and lazily initialize) the module-level JWKS client.

    PyJWKClient caches signing keys in memory and refreshes on unknown kid.
    The same instance is reused across requests to avoid repeated JWKS fetches.
    """
    global _jwks_client
    if _jwks_client is None:
        if not settings.AUTH_OIDC_JWKS_URL:
            raise RuntimeError("AUTH_OIDC_JWKS_URL is required when AUTH_OIDC_ENABLED=true")
        _jwks_client = PyJWKClient(settings.AUTH_OIDC_JWKS_URL, cache_keys=True)
    return _jwks_client


def reset_jwks_client() -> None:
    """Reset the JWKS singleton.  Used in tests to inject settings changes."""
    global _jwks_client
    _jwks_client = None
