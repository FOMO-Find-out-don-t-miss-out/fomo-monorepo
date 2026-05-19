from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from geoalchemy2.shape import to_shape
from pydantic import computed_field, field_serializer
from sqlalchemy.dialects import postgresql
from sqlmodel import JSON, Column, DateTime, Field, Index, SQLModel, UniqueConstraint

from packages.domain.models.base import TimestampMixin


class EventCategory(StrEnum):
    Music = "Music"
    Art = "Art"
    Tech = "Tech"
    Food = "Food"
    Nightlife = "Nightlife"
    Sports = "Sports"
    Business = "Business"
    Community = "Community"
    Other = "Other"


class GeocodingStatus(StrEnum):
    verified = "verified"
    ambiguous = "ambiguous"
    failed = "failed"


class EventStatus(StrEnum):
    approved = "approved"
    live = "live"
    expired = "expired"
    archived = "archived"
    under_investigation = "under_investigation"
    removed = "removed"


class EventProvenance(StrEnum):
    aggregated = "aggregated"
    community_submitted = "community_submitted"
    claimed_official = "claimed_official"
    verified_organizer = "verified_organizer"


class EventTrustLevel(StrEnum):
    unverified = "unverified"
    community_validated = "community_validated"
    trusted_source = "trusted_source"
    official = "official"


class EventVisibility(StrEnum):
    public = "public"
    hidden = "hidden"
    shadow_hidden = "shadow_hidden"
    restricted = "restricted"


class EventBase(TimestampMixin, SQLModel):
    title: str = Field(index=True)
    description: str | None = Field(default=None, nullable=True)
    photo_url: str | None = Field(
        default=None,
        nullable=True,
        serialization_alias="photoUrl",
    )
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        index=True,
    )
    end_time: datetime | None = Field(
        default=None,
        index=True,
    )
    category: str = Field(
        default="Other",
        index=True,
    )
    sub_category: str | None = Field(
        default=None,
        index=True,
    )
    hype_score: int = Field(
        default=0,
        index=True,
    )
    ticket_url: str | None = Field(
        default=None,
    )
    source_url: str | None = Field(
        default=None,
    )
    source_provider: str = Field(
        default="unknown",
        index=True,
    )
    ingestion_method: str = Field(
        default="unknown",
        index=True,
    )
    location_name: str | None = Field(
        default=None,
        index=True,
    )
    country_code: str | None = Field(
        default=None,
        index=True,
    )
    # Infrastructure fields
    location: Any = Field(default=None)
    event_metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    geocoding_status: str = Field(
        default="failed",
        index=True,
    )
    geocoding_metadata: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def lat(self) -> float:
        try:
            return to_shape(self.location).y
        except Exception:
            return 0.0

    @computed_field
    @property
    def lng(self) -> float:
        try:
            return to_shape(self.location).x
        except Exception:
            return 0.0

    @field_serializer("location")
    def serialize_location(self, v: Any) -> Any:  # noqa: ANN401
        if v is None:
            return None
        try:
            shape = to_shape(v)
            return {"type": "Point", "coordinates": [shape.x, shape.y]}
        except Exception:
            return v

    def __init__(self, **data: Any):
        # Normalize/extract photo_url if missing but event_metadata exists
        photo_url = data.get("photo_url")
        event_metadata = data.get("event_metadata")

        if not photo_url and event_metadata:
            url = event_metadata.get("photo_url") or event_metadata.get("image")
            if url:
                if isinstance(url, list):
                    url = url[0] if url else None

                if isinstance(url, str):
                    url = url.strip()
                    if url.startswith("//"):
                        url = f"https:{url}"
                    elif url.startswith("www."):
                        url = f"https://{url}"
                    photo_url = url

        if photo_url:
            if isinstance(photo_url, str):
                photo_url = photo_url.strip()
                if photo_url.startswith("//"):
                    photo_url = f"https:{photo_url}"
                elif photo_url.startswith("www."):
                    photo_url = f"https://{photo_url}"
            data["photo_url"] = photo_url

        super().__init__(**data)


class Event(EventBase, table=True):
    __tablename__ = "events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    place_id: UUID | None = Field(default=None, foreign_key="places.id", index=True)
    organizer_id: UUID | None = Field(default=None, foreign_key="organizers.id", index=True)
    status: EventStatus = Field(
        sa_column=Column(
            postgresql.ENUM(EventStatus, name="event_status", create_type=False),
            nullable=False,
        ),
    )
    provenance: EventProvenance = Field(
        sa_column=Column(
            postgresql.ENUM(EventProvenance, name="event_provenance", create_type=False),
            nullable=False,
        ),
    )
    trust_level: EventTrustLevel = Field(
        default=EventTrustLevel.unverified,
        sa_column=Column(
            postgresql.ENUM(EventTrustLevel, name="event_trust_level", create_type=False),
            nullable=False,
            server_default=EventTrustLevel.unverified.value,
        ),
    )
    visibility: EventVisibility = Field(
        default=EventVisibility.public,
        sa_column=Column(
            postgresql.ENUM(EventVisibility, name="event_visibility", create_type=False),
            nullable=False,
            server_default=EventVisibility.public.value,
        ),
    )
    approved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    published_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    expired_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    removed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

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

    __table_args__ = (
        UniqueConstraint("title", "start_time", "location_name", name="unique_event_occurrence"),
        Index("ix_events_status", "status"),
        Index("ix_events_provenance", "provenance"),
        Index("ix_events_trust_level", "trust_level"),
        Index("ix_events_visibility", "visibility"),
        Index("ix_events_status_visibility_start_time", "status", "visibility", "start_time"),
    )
