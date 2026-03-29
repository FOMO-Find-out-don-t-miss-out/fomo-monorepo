from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlmodel import JSON, Column, Field, UniqueConstraint

from packages.domain.models.event import EventBase


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
    )
