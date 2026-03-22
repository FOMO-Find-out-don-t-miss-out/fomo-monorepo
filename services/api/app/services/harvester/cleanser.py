import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
import instructor
import google.generativeai as genai
from bs4 import BeautifulSoup

from app.core.config import settings
from app.utils.datetime_utils import DateTimeHelper
from app.core.geography_constants import DEFAULT_COUNTRY_CODE
from app.services.harvester.geocoder import GeocoderService

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
    street_address: Optional[str] = Field(default=None, description="The specific street address or road if available")
    search_term: Optional[str] = Field(default=None, description="Enriched search term for geocoding")
    lat: Optional[float] = Field(default=None, description="Latitude of the event")
    lng: Optional[float] = Field(default=None, description="Longitude of the event")
    category: str = Field(default="Other", description="Event category (e.g., Music, Art, Tech)")
    sub_category: Optional[str] = Field(default=None, description="Specific sub-category or local genre (e.g., Rebetiko, Techno, Jazz)")
    tags: List[str] = Field(default_factory=list, description="Standardized list of genre or vibe tags")
    hype_score: int = Field(default=0, description="Hype score of the event")
    ticket_url: Optional[str] = Field(default=None, description="URL to purchase tickets")
    description: Optional[str] = Field(default=None, description="Short summary or description of the event")
    event_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional structured data")
    confidence_score: Optional[float] = Field(default=None, description="Geocoding confidence score")
    geocoding_status: str = Field(default="failed", description="Geocoding status: verified, ambiguous, or failed")
    geocoding_metadata: Dict[str, Any] = Field(default_factory=dict, description="Geocoding metadata")
    country_code: Optional[str] = Field(default=None, description="ISO country code (e.g., GR, DE, FR)")
    source: str = Field(default="unknown", description="The source system/strategy that provided this event")

    @field_validator("start_time", mode="before")
    @classmethod
    def parse_start_time(cls, v):
        if isinstance(v, datetime):
            return v
        return DateTimeHelper.safe_parse(v)

    @field_validator("end_time", mode="before")
    @classmethod
    def parse_end_time(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        return DateTimeHelper.safe_parse(v)

    @field_validator("category", mode="before")
    @classmethod
    def ensure_category(cls, v):
        if not v or v is None:
            return "Other"
        return str(v)


class IterableExtractedEvent(BaseModel):
    tasks: List[ExtractedEvent]

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
    async def clean_json_ld(data: Dict[str, Any], country_hint: Optional[str] = None) -> Optional[ExtractedEvent]:
        """
        Maps Schema.org / JSON-LD event data directly to ExtractedEvent.
        Uses GeocoderService if coordinates are missing.
        """
        try:
            if isinstance(data, list):
                data = data[0] if data else {}

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
            city_hint = None

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
                
                address_data = location.get("address")
                address_parts = []
                street_address = None
                if isinstance(address_data, dict):
                    city_hint = address_data.get("addressLocality")
                    street_address = address_data.get("streetAddress")
                    if street_address: address_parts.append(str(street_address))
                    if city_hint: address_parts.append(str(city_hint))
                elif isinstance(address_data, str):
                    street_address = address_data
                    address_parts.append(address_data)
                
                search_term = None
                if location_name:
                    search_term = location_name
                    if address_parts:
                        search_term += f", {', '.join(address_parts)}"
            elif isinstance(location, str):
                location_name = location
                street_address = location
                search_term = location
            
            logger.info(f"[CLEANSER] JSON-LD Scraper Output: location_name='{location_name}' | address='{street_address}' | city_hint='{city_hint}'")

            confidence_score = None
            geocoding_status = "failed"
            geocoding_metadata: Dict[str, Any] = {}

            if (lat is None or lng is None) and location_name:
                geo_res = await GeocoderService.get_coordinates(
                    location_name, 
                    country_hint or DEFAULT_COUNTRY_CODE,
                    city_hint=city_hint,
                    search_term=search_term,
                    source_address=street_address
                )
                if geo_res:
                    lat, lng = geo_res.lat, geo_res.lng
                    confidence_score = geo_res.relevance
                    geocoding_status = geo_res.geocoding_status
                    geocoding_metadata = geo_res.geocoding_metadata
            elif lat is not None and lng is not None:
                geocoding_status = "verified"
                confidence_score = 1.0
                geocoding_metadata = {"source": "provided", "query": location_name}

            # Extract image from schema
            photo_url = None
            image_data = data.get("image")
            if isinstance(image_data, str):
                photo_url = image_data
            elif isinstance(image_data, list) and len(image_data) > 0:
                photo_url = image_data[0] if isinstance(image_data[0], str) else image_data[0].get("url")
            elif isinstance(image_data, dict):
                photo_url = image_data.get("url")

            return ExtractedEvent(
                title=str(title),
                start_time=data.get("startDate"), 
                end_time=data.get("endDate"),     
                location_name=location_name,
                street_address=street_address,
                lat=lat,
                lng=lng,
                category="Music" if "MusicEvent" in str(data.get("@type")) else "Other",
                ticket_url=get_val("url"),
                description=get_val("description"),
                event_metadata={**data, "image": photo_url} if photo_url else data,
                confidence_score=confidence_score,
                geocoding_status=geocoding_status,
                geocoding_metadata=geocoding_metadata
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
    async def clean_html_fallback(cls, html_text: str, country_hint: Optional[str] = None) -> List[ExtractedEvent]:
        """
        Strips noise from HTML and uses Gemini via Instructor to extract 
        a list of structured event data. Uses Geocoder for missing coords.
        """
        if not _client:
            logger.warning("Gemini client not configured. HTML fallback extraction skipped.")
            return []

        cleaned_text = cls._strip_html_noise(html_text)
        if len(cleaned_text) < 50: 
            return []

        # Taxonomy for consistent classification
        global_tags = [
            "Rock", "Techno", "House", "Jazz", "Classical", "Hip-Hop", "R&B", 
            "Electronic", "Pop", "Indie", "Metal", "Folk", "Reggae", "Blues",
            "Family-Friendly", "Festival", "Outdoor", "Clubbing", "Workshop", "Conference"
        ]

        try:
            response = _client.chat.completions.create(
                messages=[
                    {
                        "role": "user", 
                        "content": f"""Extract all event details from the following text. Return a JSON list of events. Context country: {country_hint or 'Global'}.

Strict Junk Detection: If the text is a generic offer page, a list of events, or a promotional banner, return an empty list or mark the event as category="Junk". We only want specific, single events. Exclude noise like 'cookies', 'newsletter', or 'related events'.

For each event, also provide:
- search_term: A more descriptive search term for geocoding if location_name is short (under 10 chars) or ambiguous (e.g., 'Floyd Live Music Venue' for 'Floyd')
- city_hint: The city/neighborhood from event_metadata if available
- street_address: The specific street name and number (e.g., 'Iera Odos 345')
- sub_category: Identify the specific genre or vibe (e.g., Rebetiko, Psytrance, Tech-House). Be extra specific with local sub-genres.
- tags: Select 2-5 applicable tags/genres (e.g., ["Indie-Pop", "Synth", "Live", "Tour"]). Baseline tags: {', '.join(global_tags)}.

Text: {cleaned_text}"""
                    }
                ],
                response_model=IterableExtractedEvent,
                max_retries=3
            )
            
            events = response.tasks
            
            # Post-process with Geocoder if needed
            for ev in events:
                city_hint = ev.event_metadata.get("city") if ev.event_metadata else None
                logger.info(f"[CLEANSER] AI Extraction: location_name='{ev.location_name}' | address='{ev.street_address}' | city_hint='{city_hint}'")
                if (ev.lat is None or ev.lng is None) and ev.location_name:
                    try:
                        geo_res = await GeocoderService.get_coordinates(
                            ev.location_name, 
                            country_hint or DEFAULT_COUNTRY_CODE,
                            city_hint=city_hint,
                            search_term=ev.search_term,
                            source_address=ev.street_address
                        )
                        if geo_res:
                            ev.lat, ev.lng = geo_res.lat, geo_res.lng
                            ev.confidence_score = geo_res.relevance
                            ev.geocoding_status = geo_res.geocoding_status
                            ev.geocoding_metadata = geo_res.geocoding_metadata
                    except Exception as geo_err:
                        logger.error(f"[CLEANSER] Geocoding failed for '{ev.location_name}': {geo_err}")
                        ev.geocoding_status = "failed"
                elif ev.lat is not None and ev.lng is not None:
                    ev.geocoding_status = "verified"
                    ev.confidence_score = 1.0
                    ev.geocoding_metadata = {"source": "provided", "query": ev.location_name}
                        
            return events
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return []
