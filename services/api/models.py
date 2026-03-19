from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, JSON, String, Integer, DateTime, UniqueConstraint
from geoalchemy2 import Geography


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


class Event(SQLModel, table=True):
    __tablename__ = "events"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str
    location: Any = Field(sa_column=Column(Geography(geometry_type='POINT', srid=4326)))
    start_time: datetime
    end_time: datetime
    hype_score: int = Field(default=0, index=True)
    event_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class SocialConnection(SQLModel, table=True):
    __tablename__ = "social_connections"
    follower_id: UUID = Field(foreign_key="users.id", primary_key=True)
    following_id: UUID = Field(foreign_key="users.id", primary_key=True)

    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="unique_follow"),
    )


class HypeLedger(SQLModel, table=True):
    __tablename__ = "hype_ledger"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    event_id: UUID = Field(foreign_key="events.id")
    amount: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
