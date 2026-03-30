from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from packages.domain.utils.datetime_utils import DateTimeHelper


class ExtractedEvent(BaseModel):
    """Schema for a single extracted event from any source."""

    title: str = Field(description="The name or title of the event")
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="The start date and time of the event",
    )
    end_time: datetime | None = Field(
        default=None, description="The end date and time of the event"
    )
    location_name: str | None = Field(default=None, description="The name of the venue or location")
    street_address: str | None = Field(
        default=None, description="The specific street address or road if available"
    )
    search_term: str | None = Field(default=None, description="Enriched search term for geocoding")
    lat: float | None = Field(default=None, description="Latitude of the event")
    lng: float | None = Field(default=None, description="Longitude of the event")
    category: str = Field(default="Other", description="Event category (e.g., Music, Art, Tech)")
    sub_category: str | None = Field(
        default=None,
        description="Specific sub-category or local genre (e.g., Rebetiko, Techno, Jazz)",
    )
    tags: list[str] = Field(
        default_factory=list, description="Standardized list of genre or vibe tags"
    )
    hype_score: int = Field(default=0, description="Hype score of the event")
    ticket_url: str | None = Field(default=None, description="URL to purchase tickets")
    description: str | None = Field(
        default=None, description="Short summary or description of the event"
    )
    event_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional structured data"
    )
    confidence_score: float | None = Field(default=None, description="Geocoding confidence score")
    geocoding_status: str = Field(
        default="failed", description="Geocoding status: verified, ambiguous, or failed"
    )
    geocoding_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Geocoding metadata"
    )
    country_code: str | None = Field(
        default=None, description="ISO country code (e.g., GR, DE, FR)"
    )
    source_provider: str = Field(
        default="unknown", description="The source provider (e.g., more.com)"
    )
    ingestion_method: str = Field(
        default="unknown", description="The method used to ingest (e.g., json_ld, html_fallback)"
    )

    @field_validator("start_time", mode="before")
    @classmethod
    def parse_start_time(cls, v: datetime | str | list[str]) -> datetime:
        if isinstance(v, datetime):
            return v
        return DateTimeHelper.safe_parse(v)

    @field_validator("end_time", mode="before")
    @classmethod
    def parse_end_time(cls, v: datetime | str | list[str] | None) -> datetime | None:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        return DateTimeHelper.safe_parse(v)

    @field_validator("category", mode="before")
    @classmethod
    def ensure_category(cls, v: str | None) -> str:
        if not v:
            return "Other"
        return str(v)


class IterableExtractedEvent(BaseModel):
    tasks: list[ExtractedEvent]
