import logging
from typing import Any

from app.core.geography_constants import DEFAULT_COUNTRY_CODE
from app.services.harvester.cleansing.ai_extractor import AiExtractor
from app.services.harvester.cleansing.json_ld_extractor import JsonLdExtractor
from app.services.harvester.location.geocoder import GeocoderService
from app.services.harvester.utils.text_sanitizer import TextSanitizer
from packages.domain.models.event import EventCategory
from packages.domain.schemas.extracted_event import ExtractedEvent
from packages.domain.services.event_classifier import EventClassifier

logger = logging.getLogger(__name__)


class CleansingService:
    """
    Orchestrates the cleansing pipeline:
    1. Extraction (JSON-LD or AI/LLM)
    2. Sanitization (Normalizing titles and text)
    3. Classification (Domain-driven tagging and categorization)
    4. Geocoding (Enriching with coordinates and verified addresses)
    """

    @staticmethod
    async def clean_json_ld(
        data: dict[str, Any] | list[dict[str, Any]],
        country_hint: str | None = None,
        source_domain: str | None = None,
    ) -> ExtractedEvent | list[ExtractedEvent] | None:
        """
        Orchestrates JSON-LD extraction, classification, and geocoding.
        """
        events = JsonLdExtractor.extract(data, source_domain=source_domain)
        if not events:
            return None

        for event in events:
            # 1. Sanitization
            CleansingService._sanitize_event(event)

            # 2. Enrich Classification using domain service
            # description is now guaranteed to be None or empty from scraped sources
            category, sub_category, tags = EventClassifier.classify(
                event.title, event.description, event.event_metadata
            )
            event.category = category
            event.sub_category = sub_category
            event.tags = list(set(event.tags + tags))

            # 3. Geocoding
            await CleansingService._enrich_geocoding(event, country_hint)

        if isinstance(events, list) and len(events) == 1:
            return events[0]
        return events

    @staticmethod
    async def clean_html_fallback(
        html_text: str, country_hint: str | None = None, source_domain: str | None = None
    ) -> list[ExtractedEvent]:
        """
        Orchestrates AI extraction and subsequent enrichment.
        """
        events = await AiExtractor.extract(
            html_text, country_hint=country_hint, source_domain=source_domain
        )

        for event in events:
            # 1. Sanitization
            CleansingService._sanitize_event(event)

            # AI might have already done some classification,
            # but we re-run domain logic for consistency and enrichment
            category, sub_category, tags = EventClassifier.classify(
                event.title, event.description, event.event_metadata
            )

            # event.category was already normalized to a canonical EventCategory
            # value by ExtractedEvent's validator (e.g. AI's "music" -> "Music"),
            # so this equality check reliably catches "no real category found"
            # instead of silently keeping a miscased AI value.
            if event.category == EventCategory.Other.value:
                event.category = category

            # Prefer AI's sub_category if it's more specific
            if not event.sub_category:
                event.sub_category = sub_category

            event.tags = list(set(event.tags + tags))

            # Geocoding
            await CleansingService._enrich_geocoding(event, country_hint)

        return events

    @staticmethod
    def _sanitize_event(event: ExtractedEvent) -> None:
        """Applies text sanitization to an ExtractedEvent."""
        event.title = TextSanitizer.clean_title(event.title)
        if event.description:
            event.description = TextSanitizer.normalize_whitespace(event.description)
        if event.location_name:
            event.location_name = TextSanitizer.normalize_whitespace(event.location_name)

    @staticmethod
    async def _enrich_geocoding(event: ExtractedEvent, country_hint: str | None) -> None:
        """Helper to handle geocoding for any ExtractedEvent."""
        if (event.lat is None or event.lng is None) and event.location_name:
            # Use city from metadata if available
            city_hint = None
            if event.event_metadata:
                city_hint = event.event_metadata.get("city") or event.event_metadata.get(
                    "city_hint"
                )

            try:
                geo_res = await GeocoderService.get_coordinates(
                    str(event.location_name),
                    country_hint or DEFAULT_COUNTRY_CODE,
                    city_hint=city_hint,
                    search_term=event.search_term,
                    source_address=event.street_address,
                )
                if geo_res:
                    event.lat, event.lng = geo_res.lat, geo_res.lng
                    event.confidence_score = geo_res.relevance
                    event.geocoding_status = geo_res.geocoding_status
                    event.geocoding_metadata = geo_res.geocoding_metadata
            except Exception as geo_err:
                logger.error(f"[CLEANSER] Geocoding failed for '{event.location_name}': {geo_err}")
                event.geocoding_status = "failed"
        elif event.lat is not None and event.lng is not None:
            event.geocoding_status = "verified"
            event.confidence_score = 1.0
            event.geocoding_metadata = {"source": "provided", "query": event.location_name}
