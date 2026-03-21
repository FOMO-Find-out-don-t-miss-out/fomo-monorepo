from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class EventBase(BaseModel):
    title: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    category: Optional[str] = "Other"
    hype_score: int = 0
    ticket_url: Optional[str] = None
    source_url: Optional[str] = None
    location_name: Optional[str] = None
    search_term: Optional[str] = None
    event_metadata: Dict[str, Any] = {}
    confidence_score: Optional[float] = None
    geocoding_status: str = "failed"
    geocoding_metadata: Dict[str, Any] = {}


class EventIngest(BaseModel):
    events: List[EventBase]
    raw_content: Optional[str] = None


class IngestSummary(BaseModel):
    added: int
    updated: int


class PendingEventRead(BaseModel):
    id: UUID
    status: str
    title: str
    category: str
    start_time: datetime
    hype_score: int
    # Add other fields as needed for the UI
