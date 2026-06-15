"""Admin-only user management endpoints (FOMO-157, FOMO-161)."""

from __future__ import annotations

import re
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.security.rbac import require_admin
from app.db.session import get_db
from app.schemas.admin import (
    InviteUserRequest,
    InviteUserResponse,
    UpdateSystemRoleRequest,
    UserAdminResponse,
)
from app.services.keycloak_admin_service import (
    KeycloakAdminError,
    KeycloakAdminNotConfiguredError,
    KeycloakAdminService,
    get_keycloak_admin_service,
)
from packages.domain.models.user import Profile, User, UserSystemRole

router = APIRouter(dependencies=[Depends(require_admin)])

_EMAIL_PREFIX_RE = re.compile(r"[^a-zA-Z0-9_]")


def _to_admin_response(
    user: User,
    profile: Profile | None,
    identity_status: str = "unknown",
) -> UserAdminResponse:
    return UserAdminResponse(
        id=user.id,
        external_id=user.external_id,
        email=user.email,
        username=profile.username if profile else None,
        avatar_url=profile.avatar_url if profile else None,
        system_role=user.system_role,
        created_at=user.created_at,
        updated_at=user.updated_at,
        identity_status=identity_status,
    )


def _derive_username(session: Session, email: str, user_id: UUID) -> str:
    """Derive a unique username from the email prefix.

    Falls back to a UUID stub if no unique candidate can be found in 10 tries.
    """
    base = _EMAIL_PREFIX_RE.sub("_", email.split("@")[0])[:32].strip("_") or "user"
    candidate = base
    for _ in range(10):
        if not session.exec(select(Profile).where(Profile.username == candidate)).first():
            return candidate
        candidate = f"{base}_{str(uuid4())[:6]}"
    return f"user_{str(user_id)[:8]}"


@router.get("/users", response_model=list[UserAdminResponse])
async def list_users(
    session: Annotated[Session, Depends(get_db)],
) -> list[UserAdminResponse]:
    """List all FOMO users for admin management, ordered newest first.

    Attempts a single Keycloak batch call to populate identity_status for each
    user.  Returns "unknown" for all users when KEYCLOAK_ADMIN_* is not
    configured or the Keycloak call fails — this is graceful degradation, not
    an error.

    Orphaned users (FOMO DB row exists, Keycloak identity missing) are marked
    identity_status="missing_in_keycloak".  They cannot log in because Keycloak
    will not issue tokens for them, but they remain in the DB until an admin
    explicitly cleans them up.  See FOMO-161 for the full orphan-handling policy.
    """
    users = session.exec(select(User).order_by(User.created_at.desc())).all()

    # Attempt a single Keycloak call to get all user IDs for status enrichment.
    # Gracefully degrades to "unknown" if admin API is not configured or fails.
    kc_ids: set[str] | None = None
    try:
        kc_service = KeycloakAdminService.from_settings()
        kc_ids = await kc_service.get_all_user_external_ids()
    except (KeycloakAdminNotConfiguredError, KeycloakAdminError, Exception):  # noqa: S110
        pass  # graceful degradation — identity_status stays "unknown"

    def _identity_status(external_id: str) -> str:
        if kc_ids is None:
            return "unknown"
        return "active" if external_id in kc_ids else "missing_in_keycloak"

    return [
        _to_admin_response(
            user,
            session.get(Profile, user.id),
            _identity_status(user.external_id),
        )
        for user in users
    ]


@router.patch("/users/{user_id}/system-role", response_model=UserAdminResponse)
async def update_user_system_role(
    user_id: UUID,
    body: UpdateSystemRoleRequest,
    caller: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> UserAdminResponse:
    """Update a user's system_role.

    Prevents self-demotion: an admin cannot change their own role away from admin.
    Assigning admin role to another user and then updating your own role is the
    supported workflow for role transfers.
    """
    if caller.id == user_id and body.system_role != UserSystemRole.admin:
        raise HTTPException(
            status_code=400,
            detail="Cannot demote yourself. Assign admin to another user first.",
        )

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.system_role = body.system_role
    session.add(user)
    session.commit()
    session.refresh(user)

    return _to_admin_response(user, session.get(Profile, user_id))


@router.post("/users/invite", response_model=InviteUserResponse, status_code=201)
async def invite_user(
    body: InviteUserRequest,
    caller: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    kc_service: Annotated[KeycloakAdminService, Depends(get_keycloak_admin_service)],
) -> InviteUserResponse:
    """Create or prepare a dashboard user in Keycloak and the FOMO database.

    Behaviour by case:
      A. Keycloak user absent + FOMO user absent
         → Create both; return keycloak_created=True.
      B. Keycloak user exists + FOMO user absent
         → Create FOMO user mapped to existing Keycloak identity;
           return keycloak_created=False.
      C. FOMO user exists (by external_id) → 409 Conflict.
      D. FOMO user exists (by email, different external_id) → 409 Conflict.

    The created Keycloak user has UPDATE_PASSWORD as a required action, meaning
    the user must set a password on first login.  If SMTP is configured in
    Keycloak, trigger an execute-actions-email from the Keycloak Admin UI to
    send the user an invite link; otherwise, share the Keycloak realm login URL
    and instruct the user to use "Forgot password".
    """
    # Resolve Keycloak identity — create if absent
    try:
        kc_user_id, kc_created = await kc_service.get_or_create_user(body.email)
    except KeycloakAdminError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Keycloak Admin API error while creating user: {exc}",
        ) from exc

    # Guard: FOMO user already mapped to this Keycloak identity
    existing_by_ext_id = session.exec(
        select(User).where(User.external_id == kc_user_id)
    ).first()
    if existing_by_ext_id is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A FOMO user is already linked to Keycloak ID {kc_user_id}. "
                "Use the role-update endpoint to change their role."
            ),
        )

    # Guard: FOMO user exists with same email but a different Keycloak identity
    existing_by_email = session.exec(
        select(User).where(User.email == body.email)
    ).first()
    if existing_by_email is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Email {body.email!r} is already registered in FOMO "
                "under a different identity. "
                "Resolve the duplicate before inviting this address again."
            ),
        )

    # Create FOMO user record
    user = User(
        external_id=kc_user_id,
        email=body.email,
        system_role=body.system_role,
    )
    session.add(user)
    session.flush()

    username = _derive_username(session, body.email, user.id)
    profile = Profile(user_id=user.id, username=username)
    session.add(profile)
    session.commit()
    session.refresh(user)
    session.refresh(profile)

    return InviteUserResponse(
        id=user.id,
        external_id=user.external_id,
        email=user.email,
        username=profile.username,
        avatar_url=profile.avatar_url,
        system_role=user.system_role,
        created_at=user.created_at,
        updated_at=user.updated_at,
        identity_status="active",
        keycloak_created=kc_created,
    )
