from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EventDiscoveryResponse(BaseModel):
    """
    Schema for atomic event facts returned by the discovery endpoint.
    """
    id: UUID
    title: str
    start_time: datetime = Field(..., serialization_alias="startTime")
    end_time: datetime | None = Field(None, serialization_alias="endTime")
    location_name: str | None = Field(None, serialization_alias="locationName")
    lat: float
    lng: float
    source_url: str | None = Field(None, serialization_alias="sourceUrl")
    provenance: str
    trust_level: str
    place_id: UUID | None = None
    organizer_id: UUID | None = None

    class Config:
        from_attributes = True
        populate_by_name = True
