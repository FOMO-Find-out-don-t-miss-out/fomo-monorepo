from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventDiscoveryResponse(BaseModel):
    """
    Schema for atomic event facts returned by the discovery endpoint.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    title: str
    start_time: datetime = Field(..., serialization_alias="startTime")
    end_time: datetime | None = Field(None, serialization_alias="endTime")
    location_name: str | None = Field(None, serialization_alias="locationName")
    lat: float
    lng: float
    category: str = Field(default="Other")
    hype_score: int = Field(default=0, serialization_alias="hypeScore")
    photo_url: str | None = Field(None, serialization_alias="photoUrl")
    ticket_url: str | None = Field(None, serialization_alias="ticketUrl")
    source_url: str | None = Field(None, serialization_alias="sourceUrl")
    provenance: str
    trust_level: str
    place_id: UUID | None = None
    organizer_id: UUID | None = None


class EventSearchResponse(BaseModel):
    """
    Paginated response wrapper for the Explore v1 event-search endpoint.

    Each item reuses EventDiscoveryResponse unchanged — no result-specific
    schema, no distance field, no relevance score is exposed publicly.
    """

    model_config = ConfigDict(populate_by_name=True)

    results: list[EventDiscoveryResponse]
    limit: int
    offset: int
    has_more: bool
