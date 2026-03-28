from datetime import datetime
from typing import Any
from uuid import UUID

from geoalchemy2.shape import to_shape
from pydantic import BaseModel, ConfigDict, field_serializer


class PendingEventUpdate(BaseModel):
    title: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    location_name: str | None = None
    category: str | None = None
    hype_score: int | None = None
    ticket_url: str | None = None
    event_metadata: dict[str, Any] | None = None


class VenueUpdate(BaseModel):
    name: str | None = None
    city: str | None = None
    full_address: str | None = None
    lat: float | None = None
    lng: float | None = None
    is_manually_verified: bool | None = None


class BatchApproveRequest(BaseModel):
    event_ids: list[UUID]


class BatchRejectRequest(BaseModel):
    event_ids: list[UUID]


class VenueMergeRequest(BaseModel):
    source_venue_id: UUID
    target_venue_id: UUID


class LocationBatchUpdate(BaseModel):
    target_name: str
    lat: float
    lng: float
    status: str
    confidence: float
    metadata: dict[str, Any]


class OccurrenceCreate(BaseModel):
    start_time: datetime


class GeocodeSuggestion(BaseModel):
    lat: float
    lng: float
    relevance: float
    full_address: str
    country_code: str
    city: str | None = None
    geocoding_status: str
    geocoding_metadata: dict[str, Any]


class EventBaseResponse(BaseModel):
    id: UUID
    title: str
    start_time: datetime
    end_time: datetime | None = None
    hype_score: int
    category: str
    sub_category: str | None = None
    ticket_url: str | None = None
    source_url: str | None = None
    source_provider: str = "unknown"
    ingestion_method: str = "unknown"
    location_name: str | None = None
    country_code: str | None = None
    parent_id: UUID | None = None
    location: Any | None = None
    photo_url: str | None = None
    event_metadata: dict[str, Any] = {}
    tags: list[str] = []

    @field_serializer("location")
    def serialize_location(self, v: object | None) -> dict[str, Any] | None:
        if v is None:
            return None
        try:
            shape = to_shape(v)
            return {"type": "Point", "coordinates": [shape.x, shape.y]}
        except Exception:
            return v

    model_config = ConfigDict(from_attributes=True)


class EventResponse(EventBaseResponse):
    pass


class PendingEventResponse(EventBaseResponse):
    status: str
    raw_content: str | None = None
    rejection_reason: str | None = None
    confidence_score: float | None = None
    geocoding_status: str
    geocoding_metadata: dict[str, Any] = {}
