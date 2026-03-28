import logging
import re
from datetime import UTC, datetime
from typing import Any

import instructor
from bs4 import BeautifulSoup
from google import genai
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.core.geography_constants import DEFAULT_COUNTRY_CODE
from app.services.harvester.geocoder import GeocoderService
from app.utils.datetime_utils import DateTimeHelper

logger = logging.getLogger(__name__)

# --- Schemas ---


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


# --- Instructor Setup ---

# Configure Gemini if API key is present
_client: Any = None
if hasattr(settings, "GOOGLE_API_KEY") and settings.GOOGLE_API_KEY:
    client = genai.Client(api_key=settings.GOOGLE_API_KEY, http_options={"api_version": "v1alpha"})
    # Corrected method name for this SDK/instructor version
    _client = instructor.from_genai(client=client)

# --- Cleansing Logic ---


class CleansingService:
    @staticmethod
    async def clean_json_ld(
        data: dict[str, Any] | list[dict[str, Any]],
        country_hint: str | None = None,
        source_domain: str | None = None,
    ) -> ExtractedEvent | None:
        """
        Maps Schema.org / JSON-LD event data directly to ExtractedEvent.
        Uses GeocoderService if coordinates are missing.
        """
        try:
            if isinstance(data, list):
                item_data = data[0] if data else {}
            else:
                item_data = data

            # Basic validation that this is an Event
            item_type_raw = item_data.get("@type", "")
            item_types = item_type_raw if isinstance(item_type_raw, list) else [str(item_type_raw)]
            if not any(
                "Event" in t or t in ["Event", "MusicEvent", "Festival"] for t in item_types
            ):
                return None

            def get_val(key: str) -> object | None:
                val = item_data.get(key)
                return val[0] if isinstance(val, list) else val

            title = get_val("name") or get_val("headline")
            if not title:
                return None

            location = item_data.get("location", {})
            location_name = None
            lat = None
            lng = None
            city_hint = None

            if isinstance(location, list) and location:
                location = location[0]

            if isinstance(location, dict):
                location_name = location.get("name")
                geo = location.get("geo", {})
                if isinstance(geo, dict):
                    lat_raw = geo.get("latitude")
                    lng_raw = geo.get("longitude")
                    try:
                        lat_val = lat_raw[0] if isinstance(lat_raw, list) else lat_raw
                        lng_val = lng_raw[0] if isinstance(lng_raw, list) else lng_raw
                        lat = float(lat_val) if lat_val is not None else None
                        lng = float(lng_val) if lng_val is not None else None
                    except (ValueError, TypeError):
                        lat = None
                        lng = None

                address_data = location.get("address")
                address_parts = []
                street_address = None
                if isinstance(address_data, dict):
                    city_hint = address_data.get("addressLocality")
                    street_address = address_data.get("streetAddress")
                    if street_address:
                        address_parts.append(str(street_address))
                    if city_hint:
                        address_parts.append(str(city_hint))
                elif isinstance(address_data, str):
                    street_address = address_data
                    address_parts.append(address_data)

                search_term = None
                if location_name:
                    search_term = str(location_name)
                    if address_parts:
                        search_term += f", {', '.join(address_parts)}"
            elif isinstance(location, str):
                location_name = location
                street_address = location
                search_term = location

            logger.info(
                f"[CLEANSER] JSON-LD Output: loc='{location_name}' | addr='{street_address}'"
            )

            confidence_score = None
            geocoding_status = "failed"
            geocoding_metadata: dict[str, Any] = {}

            if (lat is None or lng is None) and location_name:
                geo_res = await GeocoderService.get_coordinates(
                    str(location_name),
                    country_hint or DEFAULT_COUNTRY_CODE,
                    city_hint=city_hint,
                    search_term=search_term,
                    source_address=street_address,
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
            image_data = item_data.get("image")
            if isinstance(image_data, str):
                photo_url = image_data
            elif isinstance(image_data, list) and len(image_data) > 0:
                first_img = image_data[0]
                photo_url = first_img if isinstance(first_img, str) else first_img.get("url")
            elif isinstance(image_data, dict):
                photo_url = image_data.get("url")

            return ExtractedEvent(
                title=str(title),
                start_time=item_data.get("startDate"),  # type: ignore
                end_time=item_data.get("endDate"),  # type: ignore
                location_name=location_name,
                street_address=street_address,
                lat=lat,
                lng=lng,
                category="Music" if "MusicEvent" in str(item_data.get("@type")) else "Other",
                ticket_url=get_val("url"),
                description=get_val("description"),
                event_metadata={**item_data, "image": photo_url} if photo_url else item_data,
                confidence_score=confidence_score,
                geocoding_status=geocoding_status,
                geocoding_metadata=geocoding_metadata,
                source_provider=source_domain or "unknown",
                ingestion_method="json_ld",
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

        text = soup.get_text(separator=" ")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    async def clean_html_fallback(
        cls, html_text: str, country_hint: str | None = None, source_domain: str | None = None
    ) -> list[ExtractedEvent]:
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
            "Concert",
            "Festival",
            "Clubbing",
            "DJ Set",
            "Live Music",
            "Pop",
            "Electronic",
            "Hip-Hop",
            "Rock",
            "Jazz",
            "Classical",
            "Art",
            "Workshop",
            "Conference",
            "Outdoor",
        ]

        try:
            response = _client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional event data extractor.
Return ONLY valid JSON. No explanations.

Strict Classification Hierarchy:
1. Rule 1 (Venue Blindness): Ignore keywords in the location_name when determining category/tags.
   Example: A pop concert in a 'Jazz Club' is POP, not JAZZ.
2. Rule 2 (Primary Target): Focus 100% on the title and description for categorization.
3. Rule 3 (The 'Other' Ban): Forbid 'Other' if the text has musical keywords. Default to 'Music'.
""",
                    },
                    {
                        "role": "user",
                        "content": f"""Extract all event details from the following text.
Return a JSON list of events. Context country: {country_hint or "Global"}.

Strict Junk Detection: Exclude Noise. Only specific, single events.

Details to provide:
- search_term: descriptive term for geocoding
- city_hint: City/neighborhood
- street_address: specific street name and number
- sub_category: Identify specific genre/vibe
- tags: Select 2-5 tags from: {", ".join(global_tags)}.

Text: {cleaned_text}""",
                    }
                ],
                response_model=IterableExtractedEvent,
            )

            events = response.tasks

            # Post-process with Geocoder if needed
            for ev in events:
                ev.source_provider = source_domain or "unknown"
                ev.ingestion_method = "html_fallback"
                city_hint = ev.event_metadata.get("city") if ev.event_metadata else None
                logger.info(f"[CLEANSER] AI Extraction: loc='{ev.location_name}'")
                if (ev.lat is None or ev.lng is None) and ev.location_name:
                    try:
                        geo_res = await GeocoderService.get_coordinates(
                            str(ev.location_name),
                            country_hint or DEFAULT_COUNTRY_CODE,
                            city_hint=city_hint,
                            search_term=ev.search_term,
                            source_address=ev.street_address,
                        )
                        if geo_res:
                            ev.lat, ev.lng = geo_res.lat, geo_res.lng
                            ev.confidence_score = geo_res.relevance
                            ev.geocoding_status = geo_res.geocoding_status
                            ev.geocoding_metadata = geo_res.geocoding_metadata
                    except Exception as geo_err:
                        logger.error(
                            f"[CLEANSER] Geocoding failed for '{ev.location_name}': {geo_err}"
                        )
                        ev.geocoding_status = "failed"
                elif ev.lat is not None and ev.lng is not None:
                    ev.geocoding_status = "verified"
                    ev.confidence_score = 1.0
                    ev.geocoding_metadata = {"source": "provided", "query": ev.location_name}

            return events
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return []
