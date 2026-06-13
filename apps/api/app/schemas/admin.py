from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from packages.domain.models.user import UserSystemRole


class UserAdminResponse(BaseModel):
    """User record returned by admin management endpoints."""

    id: UUID
    external_id: str
    email: str | None
    username: str | None
    avatar_url: str | None
    system_role: UserSystemRole
    created_at: datetime
    updated_at: datetime


class UpdateSystemRoleRequest(BaseModel):
    """Request body for PATCH /admin/users/{user_id}/system-role."""

    system_role: UserSystemRole
