"""
JWT validation for Keycloak-issued access tokens.

Validation strategy
-------------------
1. Signature   — RS256 verified against each configured issuer's JWKS endpoint in
                 order.  The issuer whose signing key resolves the token's kid AND
                 whose iss claim verifies inside jwt.decode is accepted.
2. Expiry      — enforced by PyJWT (exp claim).
3. Issuer      — iss is authenticated cryptographically inside jwt.decode, never
                 via an unverified pre-decode.
4. Audience    — if AUTH_OIDC_ALLOWED_AUDIENCES is configured, aud must contain
                 at least one of those values.  Keycloak public clients often
                 omit the client_id from aud, so audience validation is optional.
5. AZP         — if AUTH_OIDC_ALLOWED_AZP is configured, azp must be in that
                 list.  Keycloak sets azp to the client that requested the token;
                 this is more reliable than aud for public clients.

Multi-issuer support: the validator iterates over oidc_allowed_issuers_list
(AUTH_OIDC_ISSUER + AUTH_OIDC_EXTRA_ISSUERS) and attempts full RS256 verification
with each issuer's JWKS client.  The loop stops on the first accepted issuer.
An unknown issuer is rejected because no JWKS client will have its signing key.
"""

import jwt

from app.core.config import settings
from app.core.security.jwks import get_jwks_client_for_issuer


def validate_access_token(token: str) -> dict:
    """Validate a Keycloak Bearer access token and return its decoded claims.

    Raises:
        RuntimeError: no issuers configured (server misconfiguration).
        jwt.ExpiredSignatureError: token has expired.
        jwt.InvalidTokenError: no configured issuer accepted the token (unknown
                               issuer, invalid signature, bad audience, or azp
                               policy violation).
    """
    allowed_issuers = settings.oidc_allowed_issuers_list
    if not allowed_issuers:
        raise RuntimeError(
            "No OIDC issuers configured. Set AUTH_OIDC_ISSUER (and optionally "
            "AUTH_OIDC_EXTRA_ISSUERS) when AUTH_OIDC_ENABLED=true."
        )

    audiences = settings.oidc_allowed_audiences_list

    # Try each configured issuer in order.  The correct issuer is the one whose
    # JWKS contains the token's signing key AND whose iss claim verifies.
    # iss is never read from an unverified decode — it is verified inside
    # jwt.decode via issuer= together with full RS256 signature verification.
    last_exc: Exception = jwt.InvalidTokenError(
        "Token does not match any configured issuer"
    )
    decoded: dict = {}

    for issuer in allowed_issuers:
        client = get_jwks_client_for_issuer(issuer)
        try:
            signing_key = client.get_signing_key_from_jwt(token)
        except jwt.exceptions.PyJWKClientError:
            continue  # this issuer's JWKS does not have the token's kid

        try:
            decoded = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=issuer,
                audience=audiences if audiences else None,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": bool(audiences),
                },
            )
        except jwt.ExpiredSignatureError:
            raise  # token is genuinely expired; no point trying other issuers
        except (jwt.InvalidTokenError, jwt.DecodeError) as exc:
            last_exc = exc
            continue  # iss mismatch, bad signature for this issuer, etc.
        else:
            break  # full verification passed
    else:
        raise last_exc

    allowed_azp = settings.oidc_allowed_azp_list
    if allowed_azp:
        azp = decoded.get("azp")
        if azp not in allowed_azp:
            raise jwt.InvalidTokenError(
                f"Token azp {azp!r} is not in the list of allowed authorized parties"
            )

    return decoded
