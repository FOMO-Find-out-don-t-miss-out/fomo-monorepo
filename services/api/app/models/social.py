from uuid import UUID
from sqlmodel import SQLModel, Field, UniqueConstraint


class SocialConnection(SQLModel, table=True):
    __tablename__ = "social_connections"
    follower_id: UUID = Field(foreign_key="users.id", primary_key=True)
    following_id: UUID = Field(foreign_key="users.id", primary_key=True)

    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="unique_follow"),
    )
