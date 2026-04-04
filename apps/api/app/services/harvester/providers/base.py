from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ScrapedEvent(BaseModel):
    title: str | None = None
    description: str | None = None
    location_name: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    photo_url: str | None = None
    original_link: str
    country_code: str
    source: str  # Kept for backward compatibility if needed, but we'll use ingestion_method
    source_provider: str | None = None
    ingestion_method: str | None = None
    raw_text: str | None = None
    structured_data: dict[str, Any] | None = None


class BaseProvider(ABC):
    @abstractmethod
    async def discover_links(self, target_url: str) -> list[str]:
        """Discover individual event links from a listing page URL."""
        pass

    @abstractmethod
    async def fetch_event(self, url: str) -> ScrapedEvent | None:
        """Fetch and parse event from URL."""
        pass
