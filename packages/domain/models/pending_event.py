from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql
from sqlmodel import JSON, Column, DateTime, Field, Index, Text, UniqueConstraint

from packages.domain.models.event import EventBase


class SubmissionType(StrEnum):
    harvested = "harvested"
    community_submission = "community_submission"
    organizer_submission = "organizer_submission"
    claim_conversion = "claim_conversion"


class DedupeStatus(StrEnum):
    not_checked = "not_checked"
    no_match = "no_match"
    possible_match = "possible_match"
    merged = "merged"
    duplicate_confirmed = "duplicate_confirmed"


class PendingEvent(EventBase, table=True):
    __tablename__ = "pending_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    location: Any = Field(sa_column=Column(Geography(geometry_type="POINT", srid=4326)))
    event_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
    )
    geocoding_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )

    status: str = Field(default="pending", index=True)
    submission_type: SubmissionType = Field(
        default=SubmissionType.harvested,
        sa_column=Column(
            postgresql.ENUM(SubmissionType, name="submission_type", create_type=False),
            nullable=False,
            server_default=SubmissionType.harvested.value,
        ),
    )
    dedupe_status: DedupeStatus = Field(
        default=DedupeStatus.not_checked,
        sa_column=Column(
            postgresql.ENUM(DedupeStatus, name="dedupe_status", create_type=False),
            nullable=False,
            server_default=DedupeStatus.not_checked.value,
        ),
    )
    candidate_event_id: UUID | None = Field(default=None, foreign_key="events.id", index=True)
    place_candidate_id: UUID | None = Field(default=None, foreign_key="places.id", index=True)
    reviewed_by: UUID | None = Field(default=None, foreign_key="users.id", index=True)
    reviewed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    review_notes: str | None = Field(default=None, sa_column=Column(Text))

    raw_content: str | None = Field(
        default=None,
        serialization_alias="rawContent",
    )
    rejection_reason: str | None = Field(
        default=None,
        serialization_alias="rejectionReason",
    )

    confidence_score: float | None = Field(
        default=None,
        serialization_alias="confidenceScore",
    )

    __table_args__ = (
        UniqueConstraint("title", "start_time", "location_name", name="unique_pending_event"),
        Index("ix_pending_events_submission_type", "submission_type"),
        Index("ix_pending_events_dedupe_status", "dedupe_status"),
        Index("ix_pending_events_status_dedupe_status", "status", "dedupe_status"),
    )
