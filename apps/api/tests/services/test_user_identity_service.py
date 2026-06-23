"""Service-level tests for UserIdentityService (FOMO-148).

Uses the SQLite in-memory session fixture from conftest — no HTTP, no JWT
signing, no live Keycloak.  TokenIdentity objects are constructed directly.
"""

from uuid import uuid4

from app.schemas.identity import TokenIdentity
from app.services.user_identity_service import UserIdentityService
from sqlmodel import Session, select

from packages.domain.models.user import User

TEST_ISSUER = "https://test.example.com/realms/test-realm"


def _make_identity(
    sub: str = "kc-sub-1",
    email: str | None = "user@example.com",
    preferred_username: str | None = "testuser",
    name: str | None = "Test User",
) -> TokenIdentity:
    return TokenIdentity(
        sub=sub,
        issuer=TEST_ISSUER,
        email=email,
        preferred_username=preferred_username,
        name=name,
    )


# ---------------------------------------------------------------------------
# User creation
# ---------------------------------------------------------------------------


def test_creates_user_on_first_access(session: Session) -> None:
    identity = _make_identity(sub="kc-sub-create")
    service = UserIdentityService(session)

    user, profile = service.get_or_create_from_identity(identity)

    assert user.external_id == "kc-sub-create"
    assert user.email == "user@example.com"
    assert profile.user_id == user.id


def test_external_id_equals_token_sub(session: Session) -> None:
    sub = f"kc-{uuid4()}"
    identity = _make_identity(sub=sub)
    service = UserIdentityService(session)

    user, _ = service.get_or_create_from_identity(identity)

    assert user.external_id == sub


def test_email_populated_from_token_claim(session: Session) -> None:
    identity = _make_identity(sub="kc-email-test", email="alice@example.com")
    service = UserIdentityService(session)

    user, _ = service.get_or_create_from_identity(identity)

    assert user.email == "alice@example.com"


def test_creates_user_without_email_when_claim_absent(session: Session) -> None:
    identity = _make_identity(sub="kc-no-email", email=None)
    service = UserIdentityService(session)

    user, _ = service.get_or_create_from_identity(identity)

    assert user.email is None


# ---------------------------------------------------------------------------
# Idempotency — no duplicate users
# ---------------------------------------------------------------------------


def test_repeated_access_does_not_create_duplicate_user(session: Session) -> None:
    identity = _make_identity(sub="kc-idempotent")
    service = UserIdentityService(session)

    user_first, _ = service.get_or_create_from_identity(identity)
    user_second, _ = service.get_or_create_from_identity(identity)

    assert user_first.id == user_second.id
    all_users = session.exec(select(User).where(User.external_id == "kc-idempotent")).all()
    assert len(all_users) == 1


# ---------------------------------------------------------------------------
# Email reconciliation — existing email / different external_id
# ---------------------------------------------------------------------------


def test_existing_email_different_sub_returns_existing_user(session: Session) -> None:
    """Core staging fix: existing user with same email but different external_id
    must be returned instead of triggering a duplicate-email IntegrityError 500.

    Scenario: user signed up via the dashboard (old-sub), then authenticates
    via the mobile app under a different Keycloak client that maps to a new sub.
    """
    existing = User(external_id="old-sub-dashboard", email="shared@example.com")
    session.add(existing)
    session.commit()
    session.refresh(existing)

    identity = _make_identity(sub="new-sub-mobile", email="shared@example.com")
    service = UserIdentityService(session)

    returned, _ = service.get_or_create_from_identity(identity)

    assert returned.id == existing.id
    assert returned.email == "shared@example.com"
    # Existing sub must NOT be overwritten (MVP: preserve stable identity)
    assert returned.external_id == "old-sub-dashboard"
    # No duplicate rows created
    all_users = session.exec(
        select(User).where(User.email == "shared@example.com")
    ).all()
    assert len(all_users) == 1


def test_existing_email_different_sub_repeated_calls_stable(session: Session) -> None:
    """Repeated calls with the mismatched sub keep returning the same user row."""
    existing = User(external_id="old-sub-stable", email="stable@example.com")
    session.add(existing)
    session.commit()
    session.refresh(existing)

    identity = _make_identity(sub="new-sub-stable", email="stable@example.com")
    service = UserIdentityService(session)

    u1, _ = service.get_or_create_from_identity(identity)
    u2, _ = service.get_or_create_from_identity(identity)

    assert u1.id == existing.id
    assert u2.id == existing.id
    all_users = session.exec(
        select(User).where(User.email == "stable@example.com")
    ).all()
    assert len(all_users) == 1


def test_no_email_in_token_and_no_existing_user_creates_new(session: Session) -> None:
    """When token has no email and no user exists for the sub, create fresh."""
    identity = _make_identity(sub="no-email-new-sub", email=None)
    service = UserIdentityService(session)

    user, _ = service.get_or_create_from_identity(identity)

    assert user.external_id == "no-email-new-sub"
    assert user.email is None


def test_no_email_in_token_existing_sub_still_returns_user(session: Session) -> None:
    """Existing user whose token stops including email must not be re-created."""
    existing = User(external_id="sub-no-email-existing", email="had-email@example.com")
    session.add(existing)
    session.commit()
    session.refresh(existing)

    # Token now has no email claim (e.g., consent removed)
    identity = _make_identity(sub="sub-no-email-existing", email=None)
    service = UserIdentityService(session)

    returned, _ = service.get_or_create_from_identity(identity)

    assert returned.id == existing.id
    # Email on record is preserved (not cleared) when token omits the claim
    assert returned.email == "had-email@example.com"


# ---------------------------------------------------------------------------
# Profile creation
# ---------------------------------------------------------------------------


def test_creates_profile_on_first_access(session: Session) -> None:
    identity = _make_identity(sub="kc-profile-new")
    service = UserIdentityService(session)

    user, profile = service.get_or_create_from_identity(identity)

    assert profile.user_id == user.id
    assert profile.username is not None and len(profile.username) > 0


def test_creates_profile_for_existing_user_without_profile(session: Session) -> None:
    """An existing user whose profile was never created gets one on sync."""
    existing = User(external_id="kc-no-profile", email="noprofile@example.com")
    session.add(existing)
    session.commit()
    session.refresh(existing)

    identity = _make_identity(sub="kc-no-profile", email="noprofile@example.com")
    service = UserIdentityService(session)
    user, profile = service.get_or_create_from_identity(identity)

    assert user.id == existing.id
    assert profile.user_id == user.id


def test_email_fallback_user_gets_profile_created(session: Session) -> None:
    """User resolved via email fallback (different sub) also gets a profile."""
    existing = User(external_id="old-sub-profile", email="profiled@example.com")
    session.add(existing)
    session.commit()
    session.refresh(existing)

    identity = _make_identity(sub="new-sub-profile", email="profiled@example.com")
    service = UserIdentityService(session)

    user, profile = service.get_or_create_from_identity(identity)

    assert user.id == existing.id
    assert profile.user_id == user.id
    assert profile.username is not None


def test_username_derived_from_preferred_username(session: Session) -> None:
    identity = _make_identity(sub="kc-uname", preferred_username="johndoe")
    service = UserIdentityService(session)

    _, profile = service.get_or_create_from_identity(identity)

    assert profile.username.startswith("johndoe")


def test_username_fallback_to_email_prefix(session: Session) -> None:
    identity = _make_identity(
        sub="kc-email-prefix",
        email="bob@example.com",
        preferred_username=None,
        name=None,
    )
    service = UserIdentityService(session)

    _, profile = service.get_or_create_from_identity(identity)

    assert profile.username.startswith("bob")


# ---------------------------------------------------------------------------
# Phone fields preserved / not overwritten by JWT sync
# ---------------------------------------------------------------------------


def test_phone_fields_not_overwritten_by_jwt_sync(session: Session) -> None:
    user = User(
        external_id="kc-phone-user",
        email="phone@example.com",
        phone_number="+30210000000",
        phone_verified=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    identity = _make_identity(sub="kc-phone-user", email="phone@example.com")
    service = UserIdentityService(session)
    returned_user, _ = service.get_or_create_from_identity(identity)

    assert returned_user.phone_number == "+30210000000"
    assert returned_user.phone_verified is True


def test_phone_fields_default_to_null_and_false_on_new_user(session: Session) -> None:
    identity = _make_identity(sub="kc-phone-default")
    service = UserIdentityService(session)

    user, _ = service.get_or_create_from_identity(identity)

    assert user.phone_number is None
    assert user.phone_verified is False


# ---------------------------------------------------------------------------
# Wallet state not stored in profile
# ---------------------------------------------------------------------------


def test_response_does_not_include_wallet_fields(session: Session) -> None:
    from app.schemas.user import UserMeResponse

    identity = _make_identity(sub="kc-wallet-check")
    service = UserIdentityService(session)
    user, profile = service.get_or_create_from_identity(identity)
    response = UserMeResponse.from_models(user, profile)

    response_dict = response.model_dump()
    assert "balance" not in response_dict
    assert "wallet" not in response_dict
    assert "fomo_coins" not in response_dict
