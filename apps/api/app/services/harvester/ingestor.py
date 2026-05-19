import logging
from uuid import uuid4

from geoalchemy2 import WKTElement
from sqlmodel import Session, select

from app.schemas.event import IngestSummary
from app.services.harvester.location.geocoder import GeocoderService
from packages.domain.models import (
    DedupeStatus,
    Event,
    EventProvenance,
    PendingEvent,
    Place,
    SubmissionType,
)
from packages.domain.schemas.extracted_event import ExtractedEvent
from packages.domain.services.trust_engine import TrustEngine

logger = logging.getLogger(__name__)


class IngestionService:
    @staticmethod
    async def ingest_events(db: Session, events: list[ExtractedEvent]) -> IngestSummary:
        """Ingests ExtractedEvent objects into the PendingEvent table with Auto-Approve Gate."""
        added_count = 0
        updated_count = 0

        for event_data in events:
            # Junk Detection logic moved to TrustEngine
            trust_engine = TrustEngine(country_code=event_data.country_code or "GR")
            if trust_engine.is_junk(event_data):
                logger.info(f"[INGEST] Skipping junk (TrustEngine): {event_data.title}")
                continue

            # Ensure event_metadata is a dict
            if not isinstance(event_data.event_metadata, dict):
                logger.warning(f"event_metadata for '{event_data.title}' is not a dict, fixing.")
                event_data.event_metadata = {}

            place_candidate_id = None
            if event_data.location_name:
                venue = db.exec(select(Place).where(Place.name == event_data.location_name)).first()
                if venue:
                    logger.info(f"[INGEST] Venue Match Found: '{event_data.location_name}'")
                    event_data.lat = venue.lat
                    event_data.lng = venue.lng
                    event_data.geocoding_status = "verified"
                    event_data.confidence_score = 1.0
                    place_candidate_id = venue.id
                elif event_data.lat is None or event_data.lng is None:
                    logger.info(
                        f"[INGEST] No Venue Cache Match for '{event_data.location_name}'. "
                        "Triggering Geocoder."
                    )
                    geo_res = await GeocoderService.get_coordinates(
                        event_data.location_name,
                        event_data.country_code or "GR",
                        city_hint=event_data.event_metadata.get("city")
                        or event_data.event_metadata.get("addressLocality"),
                        source_address=event_data.street_address,
                    )
                    if geo_res:
                        event_data.lat, event_data.lng = geo_res.lat, geo_res.lng
                        event_data.confidence_score = geo_res.relevance
                        event_data.geocoding_status = geo_res.geocoding_status
                        event_data.geocoding_metadata = geo_res.geocoding_metadata

            logger.info(f">>> INGESTING: {event_data.title} at {event_data.location_name}")

            wkt_point = None
            if (
                event_data.lat is not None
                and event_data.lng is not None
                and event_data.lat != 0.0
                and event_data.lng != 0.0
            ):
                wkt_point = WKTElement(f"POINT({event_data.lng} {event_data.lat})", srid=4326)

                # SAVE/UPDATE VENUE CACHE
                if event_data.location_name:
                    from app.repositories.place_repository import PlaceRepository

                    # Safe city extraction
                    loc_meta = event_data.event_metadata.get("location", {})
                    loc_city = None
                    if isinstance(loc_meta, dict):
                        addr_meta = loc_meta.get("address", {})
                        if isinstance(addr_meta, dict):
                            loc_city = addr_meta.get("addressLocality")

                    final_city = (
                        event_data.event_metadata.get("city")
                        or event_data.event_metadata.get("addressLocality")
                        or loc_city
                    )

                    resolved_place = PlaceRepository(db).save_place(
                        name=event_data.location_name,
                        country_code=event_data.country_code or "GR",
                        lat=event_data.lat,
                        lng=event_data.lng,
                        full_address=event_data.street_address or event_data.location_name,
                        relevance=event_data.confidence_score or 0.9,
                        city=str(final_city) if final_city else None,
                    )
                    place_candidate_id = resolved_place.id

            is_auto_approved = trust_engine.is_trusted_for_autopublish(event_data)

            existing_pending = db.exec(
                select(PendingEvent).where(
                    PendingEvent.title == event_data.title,
                    PendingEvent.start_time == event_data.start_time,
                    PendingEvent.location_name == event_data.location_name,
                )
            ).first()

            pending_status = "published" if is_auto_approved else "pending"

            if existing_pending:
                existing_pending.end_time = event_data.end_time
                existing_pending.category = event_data.category
                existing_pending.sub_category = event_data.sub_category
                existing_pending.tags = event_data.tags
                existing_pending.location = wkt_point
                existing_pending.location_name = event_data.location_name
                existing_pending.ticket_url = event_data.ticket_url
                existing_pending.country_code = event_data.country_code
                existing_pending.confidence_score = event_data.confidence_score
                existing_pending.geocoding_status = event_data.geocoding_status
                existing_pending.geocoding_metadata = event_data.geocoding_metadata
                existing_pending.status = pending_status
                existing_pending.source_provider = event_data.source_provider
                existing_pending.ingestion_method = event_data.ingestion_method
                existing_pending.description = event_data.description
                existing_pending.photo_url = event_data.photo_url
                existing_pending.submission_type = SubmissionType.harvested
                existing_pending.dedupe_status = DedupeStatus.not_checked
                existing_pending.candidate_event_id = None
                existing_pending.place_candidate_id = place_candidate_id
                existing_pending.reviewed_by = None
                existing_pending.reviewed_at = None
                existing_pending.review_notes = None

                if event_data.event_metadata.get("original_link"):
                    existing_pending.source_url = event_data.event_metadata["original_link"]

                # Ensure existing metadata is also a dict
                if not isinstance(existing_pending.event_metadata, dict):
                    existing_pending.event_metadata = {}

                existing_pending.event_metadata = {
                    **existing_pending.event_metadata,
                    **event_data.event_metadata,
                }
                db.add(existing_pending)
                updated_count += 1
            else:
                new_pending = PendingEvent(
                    title=event_data.title,
                    location=wkt_point,
                    location_name=event_data.location_name,
                    country_code=event_data.country_code,
                    start_time=event_data.start_time,
                    end_time=event_data.end_time,
                    category=event_data.category,
                    sub_category=event_data.sub_category,
                    tags=event_data.tags,
                    hype_score=event_data.hype_score,
                    ticket_url=event_data.ticket_url,
                    source_url=event_data.event_metadata.get("original_link"),
                    event_metadata=event_data.event_metadata,
                    confidence_score=event_data.confidence_score,
                    geocoding_status=event_data.geocoding_status,
                    geocoding_metadata=event_data.geocoding_metadata,
                    status=pending_status,
                    source_provider=event_data.source_provider,
                    ingestion_method=event_data.ingestion_method,
                    description=event_data.description,
                    photo_url=event_data.photo_url,
                    submission_type=SubmissionType.harvested,
                    dedupe_status=DedupeStatus.not_checked,
                    candidate_event_id=None,
                    place_candidate_id=place_candidate_id,
                    reviewed_by=None,
                    reviewed_at=None,
                    review_notes=None,
                )
                db.add(new_pending)
                added_count += 1

            if is_auto_approved:
                existing_live = db.exec(
                    select(Event).where(
                        Event.title == event_data.title, Event.start_time == event_data.start_time
                    )
                ).first()

                if not existing_live:
                    logger.info(f"[INGEST] Auto-Approve: '{event_data.title}'")
                    live_id = uuid4()
                    live_event = Event(
                        id=live_id,
                        title=event_data.title,
                        description=event_data.description,
                        photo_url=event_data.photo_url,
                        location=wkt_point,
                        location_name=event_data.location_name,
                        country_code=event_data.country_code,
                        start_time=event_data.start_time,
                        end_time=event_data.end_time,
                        category=event_data.category,
                        sub_category=event_data.sub_category,
                        tags=event_data.tags,
                        hype_score=event_data.hype_score,
                        ticket_url=event_data.ticket_url,
                        source_url=event_data.event_metadata.get("original_link"),
                        source_provider=event_data.source_provider,
                        ingestion_method=event_data.ingestion_method,
                        event_metadata=event_data.event_metadata,
                        geocoding_status=event_data.geocoding_status,
                        geocoding_metadata=event_data.geocoding_metadata,
                        provenance=EventProvenance.aggregated,
                        place_id=place_candidate_id,
                    )
                    db.add(live_event)

        db.commit()
        return IngestSummary(added=added_count, updated=updated_count)
