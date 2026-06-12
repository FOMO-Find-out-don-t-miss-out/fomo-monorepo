from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.dialects import postgresql
from sqlmodel import JSON, Column, Field, SQLModel

from packages.domain.models.base import TimestampMixin


class UserSystemRole(StrEnum):
    """System access roles for backend RBAC.

    These govern API access control only and are intentionally separate from
    product trust states (scout, trusted_partner, organizer tiers, etc.).

    Hierarchy (human roles):  admin > manager > moderator > user
    Service is a standalone machine role, not part of the human hierarchy.
    """

    admin = "admin"
    manager = "manager"
    moderator = "moderator"
    user = "user"
    service = "service"


class User(TimestampMixin, SQLModel, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    external_id: str = Field(unique=True, index=True)  # Keycloak sub
    email: str | None = Field(default=None, unique=True, index=True)
    # Reserved for OTP phone verification (FOMO-149+); not set by JWT sync.
    phone_number: str | None = Field(default=None)
    phone_verified: bool = Field(default=False)
    system_role: UserSystemRole = Field(
        default=UserSystemRole.user,
        sa_column=Column(
            postgresql.ENUM(UserSystemRole, name="user_system_role", create_type=False),
            nullable=False,
            server_default=UserSystemRole.user.value,
        ),
    )


class Profile(TimestampMixin, SQLModel, table=True):
    __tablename__ = "profiles"
    user_id: UUID = Field(foreign_key="users.id", primary_key=True)
    username: str = Field(unique=True, index=True)
    avatar_url: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
