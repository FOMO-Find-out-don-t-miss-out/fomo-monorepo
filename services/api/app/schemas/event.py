from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class EventBase(BaseModel):
    title: str
    lat: float
    lng: float
    start_time: datetime
    end_time: datetime
    category: str
    hype_score: int = 0
    ticket_url: Optional[str] = None
    source_url: Optional[str] = None
    event_metadata: Dict[str, Any] = {}


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
    # Add other fields as needed for the UI
