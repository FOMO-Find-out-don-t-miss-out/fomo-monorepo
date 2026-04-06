import asyncio
import logging
import re
from typing import Any

import instructor
from app.core.config import settings
from bs4 import BeautifulSoup
from google import genai

from packages.domain.schemas.extracted_event import ExtractedEvent, IterableExtractedEvent

logger = logging.getLogger(__name__)

# --- Instructor Setup ---
_client: Any = None
if hasattr(settings, "GOOGLE_API_KEY") and settings.GOOGLE_API_KEY:
    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        _client = instructor.from_genai(client=client)
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")


class AiExtractor:
    """
    Specialized extractor using LLM (Gemini) for unstructured HTML content.
    """

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
    async def extract(
        cls, html_text: str, country_hint: str | None = None, source_domain: str | None = None
    ) -> list[ExtractedEvent]:
        """
        Strips noise from HTML and uses Gemini via Instructor to extract
        a list of structured event data.
        """
        if not _client:
            logger.warning("Gemini client not configured. AI extraction skipped.")
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
            # Small throttle to avoid hitting RPM limits
            await asyncio.sleep(1.0)

            response = _client.chat.completions.create(
                model=settings.GEMINI_MODEL,
                max_retries=3,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional event data extractor.
Return ONLY valid JSON. No explanations.

Extraction Rules:
1. Extract ONLY: Title, Start Time, End Time, and Venue details.
2. DO NOT extract descriptions or image URLs under any circumstances.
3. Strict Classification Hierarchy: Venue blindness, forbid 'Other' if musical keywords are present.
""",
                    },
                    {
                        "role": "user",
                        "content": f"""Extract event details from the following text.
Return a JSON list of events. Context country: {country_hint or "Global"}.

MANDATORY: Do NOT include 'description' or 'photo_url' in your output.

Details to provide:
- title: The name of the event
- location_name: The name of the venue
- search_term: descriptive term for geocoding (venue name + city)
- city_hint: City/neighborhood
- street_address: specific street name and number
- sub_category: Identify specific genre/vibe
- tags: Select 2-5 tags from: {", ".join(global_tags)}.

Text: {cleaned_text}""",
                    },
                ],
                response_model=IterableExtractedEvent,
            )

            events = response.tasks
            for ev in events:
                ev.source_provider = source_domain or "unknown"
                ev.ingestion_method = "html_fallback"

            return events
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return []
