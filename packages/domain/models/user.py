from typing import Any
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, Field, SQLModel

from packages.domain.models.base import TimestampMixin


class User(TimestampMixin, SQLModel, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    external_id: str = Field(unique=True, index=True)  # Supabase/Auth0
    email: str = Field(unique=True, index=True)


class Profile(TimestampMixin, SQLModel, table=True):
    __tablename__ = "profiles"
    user_id: UUID = Field(foreign_key="users.id", primary_key=True)
    username: str = Field(unique=True, index=True)
    avatar_url: str | None = None
    fomo_coins: int = Field(default=100)
    settings: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
