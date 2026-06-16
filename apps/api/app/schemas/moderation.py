from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer, model_validator

from packages.domain.models.pending_event import DedupeStatus
from packages.domain.models.place import PlaceVerificationStatus
from packages.domain.utils.geo_utils import parse_wkb_to_geojson


class PendingEventUpdate(BaseModel):
    title: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    location_name: str | None = None
    category: str | None = None
    hype_score: int | None = None
    ticket_url: str | None = None
    event_metadata: dict[str, Any] | None = None


class PlaceUpdate(BaseModel):
    name: str | None = None
    city: str | None = None
    full_address: str | None = None
    lat: float | None = None
    lng: float | None = None
    verification_status: PlaceVerificationStatus | None = None


class PlaceResponse(BaseModel):
    created_at: datetime = None
    updated_at: datetime = None
    id: UUID = None
    name: str
    country_code: str
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    full_address: str | None = None
    relevance: float
    verification_status: PlaceVerificationStatus = PlaceVerificationStatus.unverified

    model_config = ConfigDict(from_attributes=True)


class PlaceMergeRequest(BaseModel):
    source_place_id: UUID
    target_place_id: UUID


class BatchApproveRequest(BaseModel):
    event_ids: list[UUID]


class BatchRejectRequest(BaseModel):
    event_ids: list[UUID]


# Kept for deprecated /venues routes — field names are HTTP API contract for existing clients
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
    location: Any | None = None
    photo_url: str | None = None
    event_metadata: dict[str, Any] = {}
    tags: list[str] = []

    @field_serializer("location")
    def serialize_location(self, v: object | None) -> dict[str, Any] | None:
        return parse_wkb_to_geojson(v)

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
    dedupe_status: DedupeStatus = DedupeStatus.not_checked
    candidate_event_id: UUID | None = None
    place_candidate_id: UUID | None = None
    place_id: UUID | None = None

    @model_validator(mode="before")
    @classmethod
    def map_from_orm(cls, data: Any) -> Any:  # noqa: ANN401
        if hasattr(data, "id") and not isinstance(data, dict):
            payload = data.model_dump()
            payload["location"] = parse_wkb_to_geojson(data.location)
            return {
                **payload,
                "status": getattr(data, "status", "published"),
                "raw_content": getattr(data, "raw_content", None),
                "rejection_reason": getattr(data, "rejection_reason", None),
                "confidence_score": getattr(data, "confidence_score", None),
                "geocoding_status": getattr(data, "geocoding_status", "verified"),
                "geocoding_metadata": {
                    **getattr(data, "geocoding_metadata", {}),
                    "full_address": getattr(data, "geocoding_metadata", {}).get("full_address")
                    or data.location_name,
                },
                "dedupe_status": getattr(data, "dedupe_status", DedupeStatus.not_checked),
                "candidate_event_id": getattr(data, "candidate_event_id", None),
                "place_candidate_id": getattr(data, "place_candidate_id", None),
                "place_id": getattr(data, "place_id", None),
            }
        return data


# Backward-compat aliases — use canonical names for new code
VenueUpdate = PlaceUpdate
Venue = PlaceResponse
