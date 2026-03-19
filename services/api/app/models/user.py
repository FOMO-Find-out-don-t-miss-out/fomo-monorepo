from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, JSON


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    external_id: str = Field(unique=True, index=True)  # Supabase/Auth0
    email: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Profile(SQLModel, table=True):
    __tablename__ = "profiles"
    user_id: UUID = Field(foreign_key="users.id", primary_key=True)
    username: str = Field(unique=True, index=True)
    avatar_url: Optional[str] = None
    fomo_coins: int = Field(default=100)
    settings: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
