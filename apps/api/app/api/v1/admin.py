"""Admin-only user management endpoints (FOMO-157)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.security.rbac import require_admin
from app.db.session import get_db
from app.schemas.admin import UpdateSystemRoleRequest, UserAdminResponse
from packages.domain.models.user import Profile, User, UserSystemRole

router = APIRouter(dependencies=[Depends(require_admin)])


def _to_admin_response(user: User, profile: Profile | None) -> UserAdminResponse:
    return UserAdminResponse(
        id=user.id,
        external_id=user.external_id,
        email=user.email,
        username=profile.username if profile else None,
        avatar_url=profile.avatar_url if profile else None,
        system_role=user.system_role,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/users", response_model=list[UserAdminResponse])
async def list_users(
    session: Annotated[Session, Depends(get_db)],
) -> list[UserAdminResponse]:
    """List all FOMO users for admin management, ordered newest first."""
    users = session.exec(select(User).order_by(User.created_at.desc())).all()
    return [_to_admin_response(user, session.get(Profile, user.id)) for user in users]


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
