"""
JWT validation for Keycloak-issued access tokens.

Validation strategy
-------------------
1. Issuer      — iss extracted without verification, then checked against
                 oidc_allowed_issuers_list (AUTH_OIDC_ISSUER + AUTH_OIDC_EXTRA_ISSUERS).
2. Signature   — RS256, verified against the issuer's JWKS endpoint.
3. Expiry      — enforced by PyJWT (exp claim).
4. Audience    — if AUTH_OIDC_ALLOWED_AUDIENCES is configured, aud must contain
                 at least one of those values.  Keycloak public clients often
                 omit the client_id from aud, so audience validation is optional.
5. AZP         — if AUTH_OIDC_ALLOWED_AZP is configured, azp must be in that
                 list.  Keycloak sets azp to the client that requested the token;
                 this is more reliable than aud for public clients.

Multi-issuer support: both fomo-admin (dashboard) and fomo-users (mobile) realm
tokens are accepted when both issuers are listed in the allowed issuers config.
"""

import jwt

from app.core.config import settings
from app.core.security.jwks import get_jwks_client_for_issuer


def validate_access_token(token: str) -> dict:
    """Validate a Keycloak Bearer access token and return its decoded claims.

    Raises:
        RuntimeError: no issuers configured (server misconfiguration).
        jwt.ExpiredSignatureError: token has expired.
        jwt.InvalidTokenError: signature invalid, issuer not allowed, malformed,
                               or azp/audience policy violation.
    """
    allowed_issuers = settings.oidc_allowed_issuers_list
    if not allowed_issuers:
        raise RuntimeError(
            "No OIDC issuers configured. Set AUTH_OIDC_ISSUER (and optionally "
            "AUTH_OIDC_EXTRA_ISSUERS) when AUTH_OIDC_ENABLED=true."
        )

    # Decode issuer without signature verification to route to the right JWKS client.
    # The iss claim is re-validated with full verification below.
    try:
        unverified: dict = jwt.decode(token, options={"verify_signature": False})
        token_issuer: str = unverified.get("iss", "")
    except jwt.InvalidTokenError as exc:
        raise jwt.InvalidTokenError(f"Cannot decode token: {exc}") from exc

    if token_issuer not in allowed_issuers:
        raise jwt.InvalidTokenError(
            f"Token issuer {token_issuer!r} is not in the list of allowed issuers"
        )

    client = get_jwks_client_for_issuer(token_issuer)

    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except jwt.exceptions.PyJWKClientError as exc:
        raise jwt.InvalidTokenError(f"Cannot resolve signing key: {exc}") from exc

    audiences = settings.oidc_allowed_audiences_list

    decoded: dict = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=token_issuer,
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
