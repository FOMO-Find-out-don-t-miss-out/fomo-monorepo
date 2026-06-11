"""
JWT validation for Keycloak-issued access tokens.

Validation strategy
-------------------
1. Signature   — RS256, verified against Keycloak JWKS endpoint.
2. Expiry      — enforced by PyJWT (exp claim).
3. Issuer      — iss must equal AUTH_OIDC_ISSUER.
4. Audience    — if AUTH_OIDC_ALLOWED_AUDIENCES is configured, aud must contain
                 at least one of those values.  Keycloak public clients often
                 omit the client_id from aud, so audience validation is optional.
5. AZP         — if AUTH_OIDC_ALLOWED_AZP is configured, azp must be in that
                 list.  Keycloak sets azp to the client that requested the token;
                 this is more reliable than aud for public clients.

FOMO-148 will handle user / profile sync; this module only validates the token.
RBAC (role enforcement) is intentionally out of scope for FOMO-147.
"""

import jwt

from app.core.config import settings
from app.core.security.jwks import get_jwks_client


def validate_access_token(token: str) -> dict:
    """Validate a Keycloak Bearer access token and return its decoded claims.

    Raises:
        RuntimeError: AUTH_OIDC_ISSUER not configured (server misconfiguration).
        jwt.ExpiredSignatureError: token has expired.
        jwt.InvalidTokenError: signature invalid, issuer wrong, malformed, or
                               azp/audience policy violation.
    """
    if not settings.AUTH_OIDC_ISSUER:
        raise RuntimeError("AUTH_OIDC_ISSUER is required when AUTH_OIDC_ENABLED=true")

    client = get_jwks_client()

    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except jwt.exceptions.PyJWKClientError as exc:
        raise jwt.InvalidTokenError(f"Cannot resolve signing key: {exc}") from exc

    audiences = settings.oidc_allowed_audiences_list

    decoded: dict = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=settings.AUTH_OIDC_ISSUER,
        audience=audiences if audiences else None,
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_iss": True,
            "verify_aud": bool(audiences),
        },
    )

    allowed_azp = settings.oidc_allowed_azp_list
    if allowed_azp:
        azp = decoded.get("azp")
        if azp not in allowed_azp:
            raise jwt.InvalidTokenError(
                f"Token azp {azp!r} is not in the list of allowed authorized parties"
            )

    return decoded
