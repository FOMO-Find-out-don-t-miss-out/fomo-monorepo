"""
User / profile sync service for FOMO-148.

Keycloak owns authentication.  This service owns the internal FOMO projection:
on every authenticated request it ensures a User row and a Profile row exist,
mapping the Keycloak `sub` claim to `users.external_id`.

Intentionally out of scope:
- wallet state (kept in wallet_accounts / wallet_transactions)
- phone OTP verification (reserved for FOMO-149+)
- RBAC / trust tiers
"""

import re
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.schemas.identity import TokenIdentity
from packages.domain.models.user import Profile, User


class UserIdentityService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create_from_identity(self, identity: TokenIdentity) -> tuple[User, Profile]:
        """Find or create a User + Profile from a validated Keycloak identity.

        Idempotent: repeated calls with the same identity.sub always return
        the same User, never creating duplicates.
        """
        user = self._get_or_create_user(identity)
        profile = self._get_or_create_profile(user, identity)
        self.session.commit()
        self.session.refresh(user)
        self.session.refresh(profile)
        return user, profile

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_or_create_user(self, identity: TokenIdentity) -> User:
        user = self.session.exec(
            select(User).where(User.external_id == identity.sub)
        ).first()

        if user is None:
            user = User(external_id=identity.sub, email=identity.email)
            self.session.add(user)
            self.session.flush()
        elif identity.email and user.email != identity.email:
            # Keep email in sync when the token provides one and it changed.
            # phone_number / phone_verified are NOT sourced from JWT — they
            # belong to the OTP flow and must never be overwritten here.
            user.email = identity.email
            self.session.flush()

        return user

    def _get_or_create_profile(self, user: User, identity: TokenIdentity) -> Profile:
        profile = self.session.get(Profile, user.id)

        if profile is None:
            username = self._derive_username(user, identity)
            profile = Profile(user_id=user.id, username=username)
            self.session.add(profile)
            self.session.flush()

        return profile

    def _derive_username(self, user: User, identity: TokenIdentity) -> str:
        """Produce a unique, sanitized username from available token claims.

        Preference order: preferred_username → name → email prefix → UUID stub.
        A random hex suffix is appended on collision (up to 10 retries).
        """
        raw: str = (
            identity.preferred_username
            or identity.name
            or (user.email.split("@")[0] if user.email else None)
            or str(user.id)[:8]
        )
        base = re.sub(r"[^a-zA-Z0-9_]", "_", raw)[:32].strip("_") or "user"

        candidate = base
        for _ in range(10):
            if not self.session.exec(
                select(Profile).where(Profile.username == candidate)
            ).first():
                return candidate
            candidate = f"{base}_{str(uuid4())[:6]}"

        # Deterministic fallback using the user primary key.
        return f"user_{str(user.id)[:8]}"

    def get_user_and_profile(self, user_id: UUID) -> tuple[User, Profile] | None:
        """Load an existing User and Profile by internal user ID."""
        user = self.session.get(User, user_id)
        if user is None:
            return None
        profile = self.session.get(Profile, user_id)
        if profile is None:
            return None
        return user, profile
