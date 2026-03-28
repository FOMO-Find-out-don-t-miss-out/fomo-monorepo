from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from geoalchemy2.shape import to_shape
from pydantic import computed_field, field_serializer
from sqlmodel import JSON, Column, Field, SQLModel, UniqueConstraint


class EventBase(SQLModel):
    title: str
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    hype_score: int = Field(default=0, index=True)
    category: str = Field(default="Other", index=True)
    sub_category: str | None = Field(default=None, index=True)
    ticket_url: str | None = None
    source_url: str | None = None
    source_provider: str = Field(default="unknown", index=True)
    ingestion_method: str = Field(default="unknown", index=True)
    location_name: str | None = Field(default=None, index=True)
    country_code: str | None = Field(default=None, index=True)
    parent_id: UUID | None = Field(default=None, index=True)

    @computed_field
    @property
    def photo_url(self) -> str | None:
        """Returns the photo URL from metadata, normalized to be absolute."""
        if not hasattr(self, "event_metadata") or not self.event_metadata:
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


class Event(EventBase, table=True):
    __tablename__ = "events"
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    location: Any = Field(sa_column=Column(Geography(geometry_type="POINT", srid=4326)))
    event_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    __table_args__ = (UniqueConstraint("title", "start_time", name="unique_event_occurrence"),)

    @field_serializer("location")
    def serialize_location(self, v: object | None) -> dict[str, Any] | None:
        if v is None:
            return None
        try:
            shape = to_shape(v)
            return {"type": "Point", "coordinates": [shape.x, shape.y]}
        except Exception:
            return v


class PendingEvent(EventBase, table=True):
    __tablename__ = "pending_events"
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    location: Any = Field(sa_column=Column(Geography(geometry_type="POINT", srid=4326)))
    event_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    status: str = Field(default="pending", index=True)
    raw_content: str | None = None
    rejection_reason: str | None = None

    confidence_score: float | None = Field(default=None)
    geocoding_status: str = Field(default="failed", index=True)
    geocoding_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    __table_args__ = (UniqueConstraint("title", "start_time", name="unique_pending_event"),)

    @field_serializer("location")
    def serialize_location(self, v: object | None) -> dict[str, Any] | None:
        if v is None:
            return None
        try:
            shape = to_shape(v)
            return {"type": "Point", "coordinates": [shape.x, shape.y]}
        except Exception:
            return v
