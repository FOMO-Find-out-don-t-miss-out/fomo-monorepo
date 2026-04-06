from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from geoalchemy2.shape import to_shape
from pydantic import computed_field, field_serializer
from sqlmodel import JSON, Column, Field, SQLModel, UniqueConstraint


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


class EventBase(SQLModel):
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
    parent_id: UUID | None = Field(
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
    )
