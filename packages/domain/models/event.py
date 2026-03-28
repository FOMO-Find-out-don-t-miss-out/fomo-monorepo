from datetime import datetime
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
    description: str | None = Field(default=None)
    start_time: datetime = Field(
        default_factory=datetime.utcnow,
        index=True,
        serialization_alias="startTime",
    )
    end_time: datetime | None = Field(
        default=None,
        index=True,
        serialization_alias="endTime",
    )
    category: EventCategory = Field(
        default=EventCategory.Other,
        index=True,
    )
    sub_category: str | None = Field(
        default=None,
        index=True,
        serialization_alias="subCategory",
    )
    hype_score: int = Field(
        default=0,
        index=True,
        serialization_alias="hypeScore",
    )
    ticket_url: str | None = Field(
        default=None,
        serialization_alias="ticketUrl",
    )
    source_url: str | None = Field(
        default=None,
        serialization_alias="sourceUrl",
    )
    location_name: str | None = Field(
        default=None,
        index=True,
        serialization_alias="locationName",
    )
    country_code: str | None = Field(
        default=None,
        index=True,
        serialization_alias="countryCode",
    )
    parent_id: UUID | None = Field(
        default=None,
        index=True,
        serialization_alias="parentId",
    )

    # Infrastructure fields
    location: Any = Field(sa_column=Column(Geography(geometry_type="POINT", srid=4326)))
    event_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        serialization_alias="eventMetadata",
    )
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
    )
    geocoding_status: GeocodingStatus = Field(
        default=GeocodingStatus.failed,
        index=True,
        serialization_alias="geocodingStatus",
    )
    geocoding_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        serialization_alias="geocodingMetadata",
    )

    @computed_field(alias="photoUrl")
    @property
    def photo_url(self) -> str | None:
        """Returns the photo URL from metadata, normalized to be absolute."""
        if not self.event_metadata:
            return None

        url = self.event_metadata.get("photo_url") or self.event_metadata.get("image")
        if not url:
            return None

        if isinstance(url, list):
            url = url[0] if url else None

        if not isinstance(url, str):
            return None

        url = url.strip()
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("www."):
            return f"https://{url}"

        return url

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
    def serialize_location(self, v: object) -> dict[str, Any] | None:
        if v is None:
            return None
        try:
            shape = to_shape(v)
            return {"type": "Point", "coordinates": [shape.x, shape.y]}
        except Exception:
            return None


class Event(EventBase, table=True):
    __tablename__ = "events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    __table_args__ = (UniqueConstraint("title", "start_time", name="unique_event_occurrence"),)
