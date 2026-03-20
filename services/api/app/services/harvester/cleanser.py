import logging
import re
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
import instructor
import google.generativeai as genai
from bs4 import BeautifulSoup

from app.core.config import settings
from app.utils.datetime_utils import DateTimeHelper

logger = logging.getLogger(__name__)

# --- Schemas ---

class ExtractedEvent(BaseModel):
    """Schema for a single extracted event from any source."""
    title: str = Field(description="The name or title of the event")
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The start date and time of the event"
    )
    end_time: Optional[datetime] = Field(
        default=None, 
        description="The end date and time of the event"
    )
    location_name: Optional[str] = Field(default=None, description="The name of the venue or location")
    lat: Optional[float] = Field(default=None, description="Latitude of the event")
    lng: Optional[float] = Field(default=None, description="Longitude of the event")
    category: str = Field(default="Other", description="Event category (e.g., Music, Art, Tech)")
    hype_score: int = Field(default=0, description="Hype score of the event")
    ticket_url: Optional[str] = Field(default=None, description="URL to purchase tickets")
    description: Optional[str] = Field(default=None, description="Short summary or description of the event")
    event_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional structured data")

    @field_validator("start_time", mode="before")
    @classmethod
    def parse_start_time(cls, v):
        return DateTimeHelper.safe_parse(v)

    @field_validator("end_time", mode="before")
    @classmethod
    def parse_end_time(cls, v):
        if v is None:
            return None
        return DateTimeHelper.safe_parse(v)

    @field_validator("category", mode="before")
    @classmethod
    def ensure_category(cls, v):
        if not v or v is None:
            return "Other"
        return str(v)

# --- Instructor Setup ---

# Configure Gemini if API key is present
_client = None
if hasattr(settings, "GOOGLE_API_KEY") and settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    _client = instructor.from_gemini(
        client=genai.GenerativeModel(
            model_name="models/gemini-2.5-flash-lite",
        ),
        mode=instructor.Mode.GEMINI_JSON,
    )

# --- Cleansing Logic ---

class CleansingService:
    @staticmethod
    def clean_json_ld(data: Dict[str, Any]) -> Optional[ExtractedEvent]:
        """
        Maps Schema.org / JSON-LD event data directly to ExtractedEvent.
        No AI involved, purely deterministic mapping.
        """
        try:
            # Handle list of events or single event
            if isinstance(data, list):
                data = data[0] if data else {}

            # Basic field extraction with fallback to first list element if needed
            def get_val(key: str):
                val = data.get(key)
                return val[0] if isinstance(val, list) else val

            title = get_val("name") or get_val("headline")
            if not title:
                return None

            location = data.get("location", {})
            location_name = None
            lat = None
            lng = None

            if isinstance(location, dict):
                location_name = location.get("name")
                geo = location.get("geo", {})
                if isinstance(geo, dict):
                    lat_raw = geo.get("latitude")
                    lng_raw = geo.get("longitude")
                    try:
                        lat = float(lat_raw[0] if isinstance(lat_raw, list) else lat_raw) if lat_raw is not None else None
                        lng = float(lng_raw[0] if isinstance(lng_raw, list) else lng_raw) if lng_raw is not None else None
                    except (ValueError, TypeError):
                        lat = None
                        lng = None

            return ExtractedEvent(
                title=str(title),
                start_time=data.get("startDate"), 
                end_time=data.get("endDate"),     
                location_name=location_name,
                lat=lat,
                lng=lng,
                category="Music" if "MusicEvent" in str(data.get("@type")) else "Other",
                ticket_url=get_val("url"),
                description=get_val("description"),
                event_metadata=data
            )
        except Exception as e:
            logger.error(f"Error cleansing JSON-LD: {e}")
            return None

    @staticmethod
    def _strip_html_noise(html_text: str) -> str:
        """Strips scripts, styles, and excessive whitespace from HTML."""
        if not html_text:
            return ""
        
        soup = BeautifulSoup(html_text, "html.parser")
        
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
            
        text = soup.get_text(separator=' ')
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @classmethod
    async def clean_html_fallback(cls, html_text: str) -> List[ExtractedEvent]:
        """
        Strips noise from HTML and uses Gemini via Instructor to extract 
        a list of structured event data matching the Pydantic schema.
        """
        if not _client:
            logger.warning("Gemini client not configured. HTML fallback extraction skipped.")
            return []

        cleaned_text = cls._strip_html_noise(html_text)
        if len(cleaned_text) < 50: 
            return []

        try:
            # Request a LIST of events to handle Gemini's behavior and avoid parsing errors
            events = _client.chat.completions.create(
                messages=[
                    {
                        "role": "user", 
                        "content": f"Extract all event details from the following text. Return a JSON list of events.\n\nText: {cleaned_text}"
                    }
                ],
                response_model=List[ExtractedEvent],
                max_retries=3
            )
            return events
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return []
