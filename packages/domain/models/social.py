from uuid import UUID

from sqlmodel import Field, SQLModel

from packages.domain.models.base import TimestampMixin


class SocialConnection(TimestampMixin, SQLModel, table=True):
    __tablename__ = "social_connections"
    follower_id: UUID = Field(foreign_key="users.id", primary_key=True)
    following_id: UUID = Field(foreign_key="users.id", primary_key=True)
