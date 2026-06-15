"""Unit tests for KeycloakAdminService (FOMO-161).

Covers:
  - Error class construction
  - from_settings() configuration guard and happy path
  - get_keycloak_admin_service() FastAPI dependency (503 guard)
  - _get_admin_token() success and failure
  - get_user_by_email() found, not-found, and API error paths
  - create_user() success (Location header parsing), non-201 error, missing Location
  - get_or_create_user() existing and new-user branches
  - get_all_user_external_ids() single page, multi-page pagination, and API error

All Keycloak Admin REST calls are intercepted by respx — no real server needed.
"""

from __future__ import annotations

import httpx
import pytest
from app.services.keycloak_admin_service import (
    KeycloakAdminError,
    KeycloakAdminNotConfiguredError,
    KeycloakAdminService,
    get_keycloak_admin_service,
)

# ---------------------------------------------------------------------------
# Fixtures / constants
# ---------------------------------------------------------------------------

_BASE = "https://auth.example.com"
_REALM = "fomo-test"
_CLIENT_ID = "fomo-admin-sa"
_CLIENT_SECRET = "super-secret"  # noqa: S105
_TOKEN_URL = f"{_BASE}/realms/{_REALM}/protocol/openid-connect/token"
_USERS_URL = f"{_BASE}/admin/realms/{_REALM}/users"
_ACCESS_TOKEN = "test-admin-access-token"  # noqa: S105


def _make_service() -> KeycloakAdminService:
    return KeycloakAdminService(
        base_url=_BASE,
        realm=_REALM,
        client_id=_CLIENT_ID,
        client_secret=_CLIENT_SECRET,
    )


def _mock_token(respx_mock: object) -> None:
    """Register a successful token response on the mock router."""
    respx_mock.post(_TOKEN_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(200, json={"access_token": _ACCESS_TOKEN})
    )


# ---------------------------------------------------------------------------
# Error class
# ---------------------------------------------------------------------------


def test_keycloak_admin_error_stores_status_code() -> None:
    err = KeycloakAdminError("something failed", status_code=503)
    assert err.status_code == 503
    assert str(err) == "something failed"


def test_keycloak_admin_error_defaults_status_code_to_none() -> None:
    err = KeycloakAdminError("generic failure")
    assert err.status_code is None


# ---------------------------------------------------------------------------
# from_settings() — configuration guard
# ---------------------------------------------------------------------------


def test_from_settings_raises_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """from_settings raises KeycloakAdminNotConfiguredError when env vars are absent."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_BASE_URL", None)
    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_CLIENT_ID", None)
    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_CLIENT_SECRET", None)

    with pytest.raises(KeycloakAdminNotConfiguredError):
        KeycloakAdminService.from_settings()


def test_from_settings_returns_service_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """from_settings builds a service with the expected URL/realm/credentials."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_BASE_URL", _BASE)
    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_REALM", _REALM)
    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_CLIENT_ID", _CLIENT_ID)
    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_CLIENT_SECRET", _CLIENT_SECRET)

    svc = KeycloakAdminService.from_settings()
    assert isinstance(svc, KeycloakAdminService)
    # trailing slash is stripped
    assert svc._base == _BASE.rstrip("/")
    assert svc._realm == _REALM
    assert svc._client_id == _CLIENT_ID
    assert svc._client_secret == _CLIENT_SECRET


def test_from_settings_strips_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_BASE_URL", f"{_BASE}/")
    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_REALM", _REALM)
    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_CLIENT_ID", _CLIENT_ID)
    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_CLIENT_SECRET", _CLIENT_SECRET)

    svc = KeycloakAdminService.from_settings()
    assert not svc._base.endswith("/")


# ---------------------------------------------------------------------------
# get_keycloak_admin_service() — FastAPI dependency
# ---------------------------------------------------------------------------


def test_dependency_raises_http_503_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FastAPI dependency must surface HTTP 503 when config is absent."""
    from app.core.config import settings
    from fastapi import HTTPException

    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_BASE_URL", None)
    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_CLIENT_ID", None)
    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_CLIENT_SECRET", None)

    with pytest.raises(HTTPException) as exc_info:
        get_keycloak_admin_service()
    assert exc_info.value.status_code == 503
    # Must not expose secret values in the error detail
    assert _CLIENT_SECRET not in str(exc_info.value.detail)


def test_dependency_returns_service_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_BASE_URL", _BASE)
    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_REALM", _REALM)
    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_CLIENT_ID", _CLIENT_ID)
    monkeypatch.setattr(settings, "KEYCLOAK_ADMIN_CLIENT_SECRET", _CLIENT_SECRET)

    svc = get_keycloak_admin_service()
    assert isinstance(svc, KeycloakAdminService)


# ---------------------------------------------------------------------------
# _get_admin_token()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_admin_token_success(respx_mock: object) -> None:
    """Successful client-credentials exchange returns the access token."""
    respx_mock.post(_TOKEN_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(200, json={"access_token": _ACCESS_TOKEN})
    )
    svc = _make_service()
    token = await svc._get_admin_token()
    assert token == _ACCESS_TOKEN


@pytest.mark.asyncio
async def test_get_admin_token_sends_client_credentials(respx_mock: object) -> None:
    """Token request must include grant_type, client_id, and client_secret."""
    route = respx_mock.post(_TOKEN_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(200, json={"access_token": _ACCESS_TOKEN})
    )
    svc = _make_service()
    await svc._get_admin_token()

    assert route.called
    sent_request = route.calls.last.request
    body = sent_request.content.decode()
    assert "grant_type=client_credentials" in body
    assert f"client_id={_CLIENT_ID}" in body
    assert f"client_secret={_CLIENT_SECRET}" in body


@pytest.mark.asyncio
async def test_get_admin_token_raises_on_non_200(respx_mock: object) -> None:
    """Non-200 token response raises KeycloakAdminError."""
    respx_mock.post(_TOKEN_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(401, json={"error": "unauthorized_client"})
    )
    svc = _make_service()
    with pytest.raises(KeycloakAdminError) as exc_info:
        await svc._get_admin_token()
    assert exc_info.value.status_code == 401
    # Error message must not expose the client secret
    assert _CLIENT_SECRET not in str(exc_info.value)


# ---------------------------------------------------------------------------
# get_user_by_email()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_by_email_returns_user_when_found(respx_mock: object) -> None:
    kc_user = {"id": "kc-uuid-abc", "email": "user@example.com", "enabled": True}
    _mock_token(respx_mock)
    respx_mock.get(_USERS_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(200, json=[kc_user])
    )

    svc = _make_service()
    result = await svc.get_user_by_email("user@example.com")
    assert result == kc_user


@pytest.mark.asyncio
async def test_get_user_by_email_returns_none_when_not_found(respx_mock: object) -> None:
    _mock_token(respx_mock)
    respx_mock.get(_USERS_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(200, json=[])
    )

    svc = _make_service()
    result = await svc.get_user_by_email("nobody@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_email_raises_on_error_status(respx_mock: object) -> None:
    _mock_token(respx_mock)
    respx_mock.get(_USERS_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(403, json={"error": "forbidden"})
    )

    svc = _make_service()
    with pytest.raises(KeycloakAdminError) as exc_info:
        await svc.get_user_by_email("user@example.com")
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# create_user()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_user_success_extracts_id_from_location(respx_mock: object) -> None:
    """Successful creation returns the user ID extracted from the Location header."""
    new_kc_id = "new-kc-user-uuid"
    _mock_token(respx_mock)
    respx_mock.post(_USERS_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(
            201,
            headers={"Location": f"{_BASE}/admin/realms/{_REALM}/users/{new_kc_id}"},
        )
    )

    svc = _make_service()
    result = await svc.create_user("new@example.com")
    assert result == new_kc_id


@pytest.mark.asyncio
async def test_create_user_sends_expected_payload(respx_mock: object) -> None:
    """create_user must send username, email, enabled, emailVerified, UPDATE_PASSWORD."""
    import json

    new_kc_id = "payload-check-uuid"
    _mock_token(respx_mock)
    route = respx_mock.post(_USERS_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(
            201,
            headers={"Location": f"{_BASE}/admin/realms/{_REALM}/users/{new_kc_id}"},
        )
    )

    svc = _make_service()
    await svc.create_user("payload@example.com")

    sent = json.loads(route.calls.last.request.content)
    assert sent["username"] == "payload@example.com"
    assert sent["email"] == "payload@example.com"
    assert sent["enabled"] is True
    assert sent["emailVerified"] is True
    assert "UPDATE_PASSWORD" in sent["requiredActions"]


@pytest.mark.asyncio
async def test_create_user_username_normalised_to_lowercase(respx_mock: object) -> None:
    """username and email are both normalised before being sent to Keycloak."""
    import json

    new_kc_id = "norm-uuid"
    _mock_token(respx_mock)
    route = respx_mock.post(_USERS_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(
            201,
            headers={"Location": f"{_BASE}/admin/realms/{_REALM}/users/{new_kc_id}"},
        )
    )

    svc = _make_service()
    await svc.create_user("  User@Example.COM  ")

    sent = json.loads(route.calls.last.request.content)
    assert sent["username"] == "user@example.com"
    assert sent["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_create_user_raises_on_non_201(respx_mock: object) -> None:
    _mock_token(respx_mock)
    respx_mock.post(_USERS_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(409, text="User exists with same email")
    )

    svc = _make_service()
    with pytest.raises(KeycloakAdminError) as exc_info:
        await svc.create_user("dup@example.com")
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_create_user_raises_when_location_header_missing(respx_mock: object) -> None:
    """If Keycloak omits the Location header, raise KeycloakAdminError."""
    _mock_token(respx_mock)
    respx_mock.post(_USERS_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(201)  # no Location header
    )

    svc = _make_service()
    with pytest.raises(KeycloakAdminError, match="Location header"):
        await svc.create_user("noloc@example.com")


# ---------------------------------------------------------------------------
# get_or_create_user()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_create_user_returns_existing_user(respx_mock: object) -> None:
    """When email matches an existing Keycloak user, was_created is False."""
    existing_id = "existing-kc-uuid"
    _mock_token(respx_mock)
    respx_mock.get(_USERS_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(200, json=[{"id": existing_id, "email": "old@example.com"}])
    )

    svc = _make_service()
    kc_id, was_created = await svc.get_or_create_user("old@example.com")
    assert kc_id == existing_id
    assert was_created is False


@pytest.mark.asyncio
async def test_get_or_create_user_creates_when_not_found(respx_mock: object) -> None:
    """When no Keycloak user exists for the email, one is created and was_created is True."""
    new_id = "brand-new-kc-uuid"
    # Token is fetched twice: once for get_user_by_email, once for create_user
    respx_mock.post(_TOKEN_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(200, json={"access_token": _ACCESS_TOKEN})
    )
    respx_mock.get(_USERS_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(200, json=[])  # not found
    )
    respx_mock.post(_USERS_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(
            201,
            headers={"Location": f"{_BASE}/admin/realms/{_REALM}/users/{new_id}"},
        )
    )

    svc = _make_service()
    kc_id, was_created = await svc.get_or_create_user("new@example.com")
    assert kc_id == new_id
    assert was_created is True


# ---------------------------------------------------------------------------
# get_all_user_external_ids()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_all_user_external_ids_single_page(respx_mock: object) -> None:
    """Returns IDs from a single page when the response has fewer than 100 entries."""
    ids = [f"kc-id-{i}" for i in range(5)]
    page = [{"id": uid} for uid in ids]
    _mock_token(respx_mock)
    respx_mock.get(_USERS_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(200, json=page)
    )

    svc = _make_service()
    result = await svc.get_all_user_external_ids()
    assert result == set(ids)


@pytest.mark.asyncio
async def test_get_all_user_external_ids_paginates(respx_mock: object) -> None:
    """Paginates until a page smaller than 100 is returned."""
    page1 = [{"id": f"kc-{i}"} for i in range(100)]  # full page → fetch next
    page2 = [{"id": f"kc-{i}"} for i in range(100, 115)]  # partial → stop

    # Token is obtained once per _auth_headers() call; get_all_user_external_ids
    # reuses the same AsyncClient across pages so the token is fetched only once.
    _mock_token(respx_mock)
    respx_mock.get(_USERS_URL).mock(  # type: ignore[union-attr]
        side_effect=[
            httpx.Response(200, json=page1),
            httpx.Response(200, json=page2),
        ]
    )

    svc = _make_service()
    result = await svc.get_all_user_external_ids()
    assert len(result) == 115
    assert "kc-0" in result
    assert "kc-114" in result


@pytest.mark.asyncio
async def test_get_all_user_external_ids_raises_on_error(respx_mock: object) -> None:
    _mock_token(respx_mock)
    respx_mock.get(_USERS_URL).mock(  # type: ignore[union-attr]
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    svc = _make_service()
    with pytest.raises(KeycloakAdminError) as exc_info:
        await svc.get_all_user_external_ids()
    assert exc_info.value.status_code == 500
