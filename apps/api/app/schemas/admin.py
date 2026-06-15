from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

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
    # Identity status relative to Keycloak.  "unknown" when KEYCLOAK_ADMIN_* is
    # not configured or the lookup failed — see FOMO-161 for enrichment details.
    identity_status: str = "unknown"


class UpdateSystemRoleRequest(BaseModel):
    """Request body for PATCH /admin/users/{user_id}/system-role."""

    system_role: UserSystemRole


_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Roles that cannot be assigned through the dashboard invite flow.
# service is a machine-to-machine role created out-of-band.
_INVITE_FORBIDDEN_ROLES = frozenset({UserSystemRole.service})


class InviteUserRequest(BaseModel):
    """Request body for POST /admin/users/invite."""

    email: str
    system_role: UserSystemRole

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("system_role")
    @classmethod
    def service_role_not_allowed(cls, v: UserSystemRole) -> UserSystemRole:
        if v in _INVITE_FORBIDDEN_ROLES:
            raise ValueError(
                f"{v.value!r} role cannot be assigned through the invite flow. "
                "Service accounts must be created out-of-band."
            )
        return v


class InviteUserResponse(UserAdminResponse):
    """Response for POST /admin/users/invite.

    Extends UserAdminResponse with information about the Keycloak side of the
    operation so the caller knows whether a new Keycloak identity was created.
    """

    keycloak_created: bool
