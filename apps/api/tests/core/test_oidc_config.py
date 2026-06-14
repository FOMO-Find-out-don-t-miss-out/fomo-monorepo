"""Unit tests for OIDC settings list properties (FOMO-159).

Verifies that AUTH_OIDC_ALLOWED_AZP and AUTH_OIDC_ALLOWED_AUDIENCES parse
comma-separated strings correctly, trim whitespace, and drop empty entries.
No network calls are made.
"""

from __future__ import annotations

from app.core.config import Settings

# ---------------------------------------------------------------------------
# oidc_allowed_azp_list
# ---------------------------------------------------------------------------


def test_azp_list_single_value() -> None:
    s = Settings(AUTH_OIDC_ALLOWED_AZP="fomo-dashboard")  # type: ignore[call-arg]
    assert s.oidc_allowed_azp_list == ["fomo-dashboard"]


def test_azp_list_comma_separated() -> None:
    s = Settings(AUTH_OIDC_ALLOWED_AZP="fomo-dashboard,fomo-n8n-ingestion")  # type: ignore[call-arg]
    assert s.oidc_allowed_azp_list == ["fomo-dashboard", "fomo-n8n-ingestion"]


def test_azp_list_whitespace_trimmed() -> None:
    s = Settings(AUTH_OIDC_ALLOWED_AZP=" fomo-dashboard , fomo-n8n-ingestion ")  # type: ignore[call-arg]
    assert s.oidc_allowed_azp_list == ["fomo-dashboard", "fomo-n8n-ingestion"]


def test_azp_list_empty_string_returns_empty() -> None:
    s = Settings(AUTH_OIDC_ALLOWED_AZP="")  # type: ignore[call-arg]
    assert s.oidc_allowed_azp_list == []


def test_azp_list_empty_entries_dropped() -> None:
    s = Settings(AUTH_OIDC_ALLOWED_AZP="fomo-dashboard,,fomo-n8n-ingestion,")  # type: ignore[call-arg]
    assert s.oidc_allowed_azp_list == ["fomo-dashboard", "fomo-n8n-ingestion"]


def test_azp_list_whitespace_only_entry_dropped() -> None:
    s = Settings(AUTH_OIDC_ALLOWED_AZP="fomo-dashboard,  ,fomo-n8n-ingestion")  # type: ignore[call-arg]
    assert s.oidc_allowed_azp_list == ["fomo-dashboard", "fomo-n8n-ingestion"]


# ---------------------------------------------------------------------------
# oidc_allowed_audiences_list
# ---------------------------------------------------------------------------


def test_audiences_list_single_value() -> None:
    s = Settings(AUTH_OIDC_ALLOWED_AUDIENCES="fomo-api")  # type: ignore[call-arg]
    assert s.oidc_allowed_audiences_list == ["fomo-api"]


def test_audiences_list_comma_separated() -> None:
    s = Settings(AUTH_OIDC_ALLOWED_AUDIENCES="fomo-api,account")  # type: ignore[call-arg]
    assert s.oidc_allowed_audiences_list == ["fomo-api", "account"]


def test_audiences_list_whitespace_trimmed() -> None:
    s = Settings(AUTH_OIDC_ALLOWED_AUDIENCES=" fomo-api , account ")  # type: ignore[call-arg]
    assert s.oidc_allowed_audiences_list == ["fomo-api", "account"]


def test_audiences_list_empty_string_returns_empty() -> None:
    s = Settings(AUTH_OIDC_ALLOWED_AUDIENCES="")  # type: ignore[call-arg]
    assert s.oidc_allowed_audiences_list == []


def test_audiences_list_empty_entries_dropped() -> None:
    s = Settings(AUTH_OIDC_ALLOWED_AUDIENCES="fomo-api,,account,")  # type: ignore[call-arg]
    assert s.oidc_allowed_audiences_list == ["fomo-api", "account"]


def test_audiences_list_whitespace_only_entry_dropped() -> None:
    s = Settings(AUTH_OIDC_ALLOWED_AUDIENCES="fomo-api,  ,account")  # type: ignore[call-arg]
    assert s.oidc_allowed_audiences_list == ["fomo-api", "account"]
