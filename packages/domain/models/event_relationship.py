from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.dialects import postgresql
from sqlmodel import Column, Field, Index, SQLModel, UniqueConstraint

from packages.domain.models.base import TimestampMixin


class RelationshipType(StrEnum):
    interested = "interested"
    saved = "saved"
    going = "going"


class EventRelationship(TimestampMixin, SQLModel, table=True):
    __tablename__ = "event_relationships"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", name="fk_event_relationships_user_id_users"),
            nullable=False,
        ),
    )
    event_id: UUID = Field(
        sa_column=Column(
            ForeignKey("events.id", name="fk_event_relationships_event_id_events"),
            nullable=False,
        ),
    )
    relationship_type: RelationshipType = Field(
        sa_column=Column(
            postgresql.ENUM(RelationshipType, name="relationship_type", create_type=False),
            nullable=False,
        ),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "event_id",
            "relationship_type",
            name="uq_event_relationships_user_event_type",
        ),
        Index("ix_event_relationships_user_id", "user_id"),
        Index("ix_event_relationships_event_id", "event_id"),
        Index("ix_event_relationships_relationship_type", "relationship_type"),
        Index("ix_event_relationships_user_id_relationship_type", "user_id", "relationship_type"),
        Index(
            "ix_event_relationships_event_id_relationship_type",
            "event_id",
            "relationship_type",
        ),
    )
