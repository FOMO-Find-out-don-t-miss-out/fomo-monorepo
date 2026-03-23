from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_serializer
from geoalchemy2.shape import to_shape

class PendingEventUpdate(BaseModel):
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location_name: Optional[str] = None
    category: Optional[str] = None
    hype_score: Optional[int] = None
    ticket_url: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None

class VenueUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    full_address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_manually_verified: Optional[bool] = None

class BatchApproveRequest(BaseModel):
    event_ids: List[UUID]

class BatchRejectRequest(BaseModel):
    event_ids: List[UUID]

class VenueMergeRequest(BaseModel):
    source_venue_id: UUID
    target_venue_id: UUID

class LocationBatchUpdate(BaseModel):
    target_name: str
    lat: float
    lng: float
    status: str
    confidence: float
    metadata: Dict[str, Any]

class OccurrenceCreate(BaseModel):
    start_time: datetime

class GeocodeSuggestion(BaseModel):
    lat: float
    lng: float
    relevance: float
    full_address: str
    country_code: str
    city: Optional[str] = None
    geocoding_status: str
    geocoding_metadata: Dict[str, Any]


class EventBaseResponse(BaseModel):
    id: UUID
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    hype_score: int
    category: str
    sub_category: Optional[str] = None
    ticket_url: Optional[str] = None
    source_url: Optional[str] = None
    location_name: Optional[str] = None
    country_code: Optional[str] = None
    parent_id: Optional[UUID] = None
    location: Optional[Any] = None
    photo_url: Optional[str] = None
    event_metadata: Dict[str, Any] = {}
    tags: List[str] = []

    @field_serializer("location")
    def serialize_location(self, v: Any):
        if v is None:
            return None
        try:
            shape = to_shape(v)
            return {"type": "Point", "coordinates": [shape.x, shape.y]}
        except Exception:
            # Already a dict or something else
            return v
    
    class Config:
        from_attributes = True


class EventResponse(EventBaseResponse):
    pass


class PendingEventResponse(EventBaseResponse):
    status: str
    raw_content: Optional[str] = None
    rejection_reason: Optional[str] = None
    confidence_score: Optional[float] = None
    geocoding_status: str
    geocoding_metadata: Dict[str, Any] = {}
