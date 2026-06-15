"""Keycloak Admin REST API client for backend-driven user management (FOMO-161).

All Keycloak Admin API calls are made server-side using client credentials.
Never expose admin credentials or responses containing sensitive data to the
browser.

Required platform configuration (KEYCLOAK_ADMIN_*):
    KEYCLOAK_ADMIN_BASE_URL     — Base URL of the Keycloak server (no trailing slash)
    KEYCLOAK_ADMIN_REALM        — Target realm (default: fomo-admin)
    KEYCLOAK_ADMIN_CLIENT_ID    — Service account client_id with manage-users role
    KEYCLOAK_ADMIN_CLIENT_SECRET — Corresponding client_secret

If any of the above vars are absent, KeycloakAdminNotConfiguredError is raised
and callers should surface HTTP 503 to indicate misconfiguration.
"""

from __future__ import annotations

import httpx
from fastapi import HTTPException

from app.core.config import settings


class KeycloakAdminNotConfiguredError(Exception):
    """Raised when KEYCLOAK_ADMIN_* env vars are missing."""


class KeycloakAdminError(Exception):
    """Raised when the Keycloak Admin API returns an unexpected error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class KeycloakAdminService:
    """Thin async client over the Keycloak Admin REST API.

    Obtains a short-lived admin token via client credentials on each operation.
    Re-using a cached token is intentionally left as a future optimisation to
    keep this implementation simple and correct.
    """

    def __init__(
        self,
        base_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._realm = realm
        self._client_id = client_id
        self._client_secret = client_secret

    @classmethod
    def from_settings(cls) -> KeycloakAdminService:
        """Build a service from the current application settings.

        Raises:
            KeycloakAdminNotConfiguredError: if any required setting is missing.
        """
        if not settings.keycloak_admin_configured:
            raise KeycloakAdminNotConfiguredError(
                "KEYCLOAK_ADMIN_BASE_URL, KEYCLOAK_ADMIN_CLIENT_ID, and "
                "KEYCLOAK_ADMIN_CLIENT_SECRET must all be set to use Keycloak admin features."
            )
        return cls(
            base_url=settings.KEYCLOAK_ADMIN_BASE_URL,  # type: ignore[arg-type]
            realm=settings.KEYCLOAK_ADMIN_REALM,
            client_id=settings.KEYCLOAK_ADMIN_CLIENT_ID,  # type: ignore[arg-type]
            client_secret=settings.KEYCLOAK_ADMIN_CLIENT_SECRET,  # type: ignore[arg-type]
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_admin_token(self) -> str:
        """Obtain a short-lived admin access token via client credentials."""
        token_url = (
            f"{self._base}/realms/{self._realm}/protocol/openid-connect/token"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
        if resp.status_code != 200:
            raise KeycloakAdminError(
                "Failed to obtain Keycloak admin token", status_code=resp.status_code
            )
        return resp.json()["access_token"]

    async def _auth_headers(self) -> dict[str, str]:
        token = await self._get_admin_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_user_by_email(self, email: str) -> dict | None:
        """Find a Keycloak user by exact email match.

        Returns the first matching Keycloak user dict, or None if not found.
        """
        headers = await self._auth_headers()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self._base}/admin/realms/{self._realm}/users",
                params={"email": email, "exact": "true"},
                headers=headers,
            )
        if resp.status_code != 200:
            raise KeycloakAdminError(
                f"Keycloak user lookup failed ({resp.status_code})",
                status_code=resp.status_code,
            )
        users: list[dict] = resp.json()
        return users[0] if users else None

    async def create_user(self, email: str) -> str:
        """Create a new Keycloak user and return their Keycloak user ID.

        The created user:
        - is enabled immediately
        - has emailVerified=true (admin-provisioned accounts are trusted)
        - has UPDATE_PASSWORD required action so the user must set a password
          on first login (typically via a password-reset / invite email)

        Returns:
            The new Keycloak user ID (UUID string).

        Raises:
            KeycloakAdminError: on non-201 response from Keycloak.
        """
        headers = await self._auth_headers()
        normalized = email.strip().lower()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self._base}/admin/realms/{self._realm}/users",
                json={
                    "username": normalized,
                    "email": normalized,
                    "enabled": True,
                    "emailVerified": True,
                    "requiredActions": ["UPDATE_PASSWORD"],
                },
                headers=headers,
            )
        if resp.status_code != 201:
            raise KeycloakAdminError(
                f"Failed to create Keycloak user ({resp.status_code}): "
                + resp.text[:200],
                status_code=resp.status_code,
            )
        # Keycloak returns the new user URI in the Location header.
        location = resp.headers.get("Location", "")
        user_id = location.rstrip("/").split("/")[-1]
        if not user_id:
            raise KeycloakAdminError("Keycloak did not return a user ID in Location header")
        return user_id

    async def get_or_create_user(self, email: str) -> tuple[str, bool]:
        """Find or create a Keycloak user by email.

        Returns:
            (keycloak_user_id, was_created): True if a new Keycloak user was
            created; False if an existing user was found.
        """
        existing = await self.get_user_by_email(email)
        if existing:
            return existing["id"], False
        user_id = await self.create_user(email)
        return user_id, True

    async def get_all_user_external_ids(self) -> set[str]:
        """Return the set of all user IDs in the Keycloak realm.

        Used for batch identity-status checks in the admin user list.
        Paginates automatically; safe for realms with up to a few thousand users.
        """
        headers = await self._auth_headers()
        all_ids: set[str] = set()
        first = 0
        page_size = 100
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                resp = await client.get(
                    f"{self._base}/admin/realms/{self._realm}/users",
                    params={"first": first, "max": page_size},
                    headers=headers,
                )
                if resp.status_code != 200:
                    raise KeycloakAdminError(
                        f"Keycloak user list failed ({resp.status_code})",
                        status_code=resp.status_code,
                    )
                page: list[dict] = resp.json()
                for u in page:
                    all_ids.add(u["id"])
                if len(page) < page_size:
                    break
                first += page_size
        return all_ids


# ------------------------------------------------------------------
# FastAPI dependency
# ------------------------------------------------------------------


def get_keycloak_admin_service() -> KeycloakAdminService:
    """FastAPI dependency: return a configured KeycloakAdminService.

    Raises HTTP 503 when KEYCLOAK_ADMIN_* env vars are not configured.
    Override in tests via app.dependency_overrides[get_keycloak_admin_service].
    """
    try:
        return KeycloakAdminService.from_settings()
    except KeycloakAdminNotConfiguredError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Keycloak Admin API is not configured on this instance. "
                "Platform must set KEYCLOAK_ADMIN_BASE_URL, "
                "KEYCLOAK_ADMIN_CLIENT_ID, and KEYCLOAK_ADMIN_CLIENT_SECRET."
            ),
        ) from exc
