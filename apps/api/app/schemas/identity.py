from pydantic import BaseModel


class TokenIdentity(BaseModel):
    """Validated identity extracted from a Keycloak JWT access token.

    Created by FOMO-147; user/profile DB sync is deferred to FOMO-148.
    """

    sub: str
    issuer: str
    email: str | None = None
    preferred_username: str | None = None
    name: str | None = None
    audience: list[str] | str | None = None
    azp: str | None = None
    realm_roles: list[str] = []

    @classmethod
    def from_claims(cls, claims: dict) -> "TokenIdentity":
        realm_access = claims.get("realm_access") or {}
        roles: list[str] = realm_access.get("roles", []) if isinstance(realm_access, dict) else []
        return cls(
            sub=claims["sub"],
            issuer=claims["iss"],
            email=claims.get("email"),
            preferred_username=claims.get("preferred_username"),
            name=claims.get("name"),
            audience=claims.get("aud"),
            azp=claims.get("azp"),
            realm_roles=roles,
        )
