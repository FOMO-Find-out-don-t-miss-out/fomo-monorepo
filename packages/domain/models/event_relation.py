from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.dialects import postgresql
from sqlmodel import Column, DateTime, Field, Index, SQLModel, UniqueConstraint, func


class EventRelationType(StrEnum):
    series = "series"
    occurrence = "occurrence"
    bundle = "bundle"
    child_event = "child_event"


class EventRelation(SQLModel, table=True):
    __tablename__ = "event_relations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    parent_event_id: UUID = Field(
        sa_column=Column(
            ForeignKey("events.id", name="fk_event_relations_parent_event_id_events"),
            nullable=False,
        ),
    )
    child_event_id: UUID = Field(
        sa_column=Column(
            ForeignKey("events.id", name="fk_event_relations_child_event_id_events"),
            nullable=False,
        ),
    )
    relation_type: EventRelationType = Field(
        sa_column=Column(
            postgresql.ENUM(EventRelationType, name="event_relation_type", create_type=False),
            nullable=False,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},
    )

    __table_args__ = (
        UniqueConstraint(
            "parent_event_id",
            "child_event_id",
            "relation_type",
            name="uq_event_relations_parent_child_type",
        ),
        CheckConstraint(
            "parent_event_id <> child_event_id",
            name="ck_event_relations_no_self_relation",
        ),
        Index("ix_event_relations_parent_event_id", "parent_event_id"),
        Index("ix_event_relations_child_event_id", "child_event_id"),
        Index("ix_event_relations_relation_type", "relation_type"),
        Index(
            "ix_event_relations_parent_event_id_relation_type",
            "parent_event_id",
            "relation_type",
        ),
    )
