import logging
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security.jwt_validator import validate_access_token
from app.schemas.identity import TokenIdentity

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> TokenIdentity | None:
    """Optional authentication dependency.

    Returns a TokenIdentity when a valid Bearer token is present, None otherwise.
    Does not raise on missing tokens — use require_authenticated_identity for that.
    When AUTH_OIDC_ENABLED=False the dependency always returns None (dev mode).
    """
    if not settings.AUTH_OIDC_ENABLED:
        return None

    if credentials is None:
        return None

    return _decode_credentials(credentials)


def require_authenticated_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> TokenIdentity:
    """Required authentication dependency.

    Returns a TokenIdentity for a valid Bearer token.
    Raises HTTP 401 for missing, malformed, expired, or otherwise invalid tokens.
    Raises HTTP 503 when AUTH_OIDC_ENABLED=False (OIDC not configured on this instance).
    """
    if not settings.AUTH_OIDC_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Authentication service is not enabled on this instance.",
        )

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _decode_credentials(credentials)


def _decode_credentials(credentials: HTTPAuthorizationCredentials) -> TokenIdentity:
    """Validate JWT credentials and return a TokenIdentity.  Raises HTTP 401 on failure."""
    try:
        claims = validate_access_token(credentials.credentials)
        return TokenIdentity.from_claims(claims)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
