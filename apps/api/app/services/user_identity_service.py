"""
User / profile sync service for FOMO-148.

Keycloak owns authentication.  This service owns the internal FOMO projection:
on every authenticated request it ensures a User row and a Profile row exist,
mapping the Keycloak `sub` claim to `users.external_id`.

Intentionally out of scope:
- wallet state (kept in wallet_accounts / wallet_transactions)
- phone OTP verification (reserved for FOMO-149+)
- RBAC / trust tiers
- multi-issuer identity alias table (deferred; see note in _resolve_by_email)
"""

import logging
import re
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.schemas.identity import TokenIdentity
from packages.domain.models.user import Profile, User

logger = logging.getLogger(__name__)


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
        # Fast path: exact sub match
        user = self.session.exec(
            select(User).where(User.external_id == identity.sub)
        ).first()
        if user is not None:
            # Keep email in sync when the token provides one and it changed.
            # phone_number / phone_verified are NOT sourced from JWT — they
            # belong to the OTP flow and must never be overwritten here.
            if identity.email and user.email != identity.email:
                user = self._update_user_email(user, identity.email)
            return user

        # Email fallback: handles realm migration, IdP change, or staging data
        # where a user record exists with the same verified email but a different
        # stored external_id.  MVP policy: return the existing user unchanged
        # rather than creating a duplicate or silently overwriting the sub.
        # Full multi-issuer linking (user_identity_aliases table) is deferred.
        if identity.email:
            user = self._resolve_by_email(identity)
            if user is not None:
                return user

        # No match by sub or email: insert a new user row.
        return self._insert_user(identity)

    def _resolve_by_email(self, identity: TokenIdentity) -> User | None:
        """Look up an existing user whose verified email matches the token claim.

        When found and the stored external_id differs from the token sub, the
        existing sub is preserved (not overwritten).  This is the safe MVP
        behaviour for single-realm setups: the email uniqueness constraint
        already ensures one user per address, so returning the existing row is
        always correct.  Overwriting external_id would require an explicit
        identity migration table to be safe across multiple issuers.
        """
        user = self.session.exec(
            select(User).where(User.email == identity.email)
        ).first()
        if user is None:
            return None

        if user.external_id != identity.sub:
            logger.warning(
                "Email match for sub=%r: found user_id=%r with external_id=%r. "
                "Returning existing user without overwriting external_id.",
                identity.sub,
                user.id,
                user.external_id,
            )
        return user

    def _insert_user(self, identity: TokenIdentity) -> User:
        """INSERT a new user row, recovering from unique constraint races.

        Two concurrent first-time requests for the same Keycloak sub can both
        pass the SELECT-then-INSERT check and race to INSERT.  A savepoint
        lets the loser roll back its write without aborting the outer session,
        then re-fetch the winner's row.

        If the IntegrityError is on the email column (a concurrent request
        resolved the same email via _resolve_by_email and itself INSERTed a
        new row just before us), we fall back to an email lookup after the
        savepoint rollback.
        """
        try:
            with self.session.begin_nested():
                user = User(external_id=identity.sub, email=identity.email)
                self.session.add(user)
                self.session.flush()
            return user
        except IntegrityError:
            logger.warning(
                "User INSERT conflict for sub=%r — re-fetching after savepoint rollback",
                identity.sub,
            )
            # Race on external_id (concurrent first login with same sub)
            refetched = self.session.exec(
                select(User).where(User.external_id == identity.sub)
            ).first()
            if refetched is not None:
                return refetched
            # Race on email (another path resolved the same email just before us)
            if identity.email:
                refetched = self.session.exec(
                    select(User).where(User.email == identity.email)
                ).first()
                if refetched is not None:
                    return refetched
            raise

    def _update_user_email(self, user: User, new_email: str) -> User:
        """Update user email, ignoring unique constraint violations.

        If the new email already belongs to a different user (a Keycloak
        misconfiguration), keep the existing email and log a warning rather
        than raising a 500.
        """
        try:
            with self.session.begin_nested():
                user.email = new_email
                self.session.flush()
        except IntegrityError:
            logger.warning(
                "Email update conflict for user_id=%r new_email=%r — keeping existing email",
                user.id,
                new_email,
            )
            self.session.expire(user)
        return user

    def _get_or_create_profile(self, user: User, identity: TokenIdentity) -> Profile:
        profile = self.session.get(Profile, user.id)

        if profile is None:
            username = self._derive_username(user, identity)
            try:
                with self.session.begin_nested():
                    profile = Profile(user_id=user.id, username=username)
                    self.session.add(profile)
                    self.session.flush()
            except IntegrityError:
                # Concurrent creation race: re-fetch the profile committed by the winner.
                self.session.expire_all()
                profile = self.session.get(Profile, user.id)
                if profile is None:
                    raise

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
