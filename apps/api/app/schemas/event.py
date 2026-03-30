from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, computed_field

from packages.domain.utils.datetime_utils import DateTimeHelper


class EventBase(BaseModel):
    title: str
    lat: float | None = None
    lng: float | None = None
    start_time: datetime
    end_time: datetime | None = None
    category: str | None = "Other"
    hype_score: int = 0
    ticket_url: str | None = None
    source_url: str | None = None
    source_provider: str = "unknown"
    ingestion_method: str = "unknown"
    location_name: str | None = None
    search_term: str | None = None
    event_metadata: dict[str, Any] = {}
    confidence_score: float | None = None
    geocoding_status: str = "failed"
    geocoding_metadata: dict[str, Any] = {}

    @computed_field
    @property
    def safe_start_time(self) -> datetime:
        return DateTimeHelper.safe_parse(self.start_time)

    @computed_field
    @property
    def safe_end_time(self) -> datetime | None:
        if self.end_time is None:
            return None
        return DateTimeHelper.safe_parse(self.end_time)


class EventIngest(BaseModel):
    events: list[EventBase]
    raw_content: str | None = None


class IngestSummary(BaseModel):
    added: int
    updated: int


class PendingEventRead(BaseModel):
    id: UUID
    status: str
    title: str
    category: str
    source_provider: str = "unknown"
    ingestion_method: str = "unknown"
    start_time: datetime
    hype_score: int
