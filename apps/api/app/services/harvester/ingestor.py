import logging
from uuid import uuid4

from geoalchemy2 import WKTElement
from sqlmodel import Session, select

from app.schemas.event import IngestSummary
from app.services.dedup.collision_detector import (
    CollisionDetector,
    log_assessment,
    signature_from_extracted,
)
from app.services.harvester.location.geocoder import GeocoderService
from packages.domain.models import (
    DedupeStatus,
    Event,
    EventProvenance,
    EventStatus,
    EventTrustLevel,
    EventVisibility,
    PendingEvent,
    Place,
    SubmissionType,
)
from packages.domain.schemas.extracted_event import ExtractedEvent
from packages.domain.services.event_collision_service import CollisionBucket
from packages.domain.services.trust_engine import TrustEngine

logger = logging.getLogger(__name__)

# Maps a collision bucket to the dedupe_status persisted on the pending row.
_BUCKET_TO_DEDUPE_STATUS = {
    CollisionBucket.no_collision: DedupeStatus.not_checked,
    CollisionBucket.exact_source_match: DedupeStatus.duplicate_confirmed,
    CollisionBucket.high_confidence_collision: DedupeStatus.duplicate_confirmed,
    CollisionBucket.possible_collision: DedupeStatus.possible_match,
}

# Safe fields to backfill on a matched live Event when claiming an ingestion
# source signal — never touches title/start_time/location/place_id/status/
# trust_level/provenance/visibility.
_CLAIMABLE_FIELDS = ("ticket_url", "photo_url", "description", "end_time")


def _claim_safe_metadata(live_event: Event, event_data: ExtractedEvent) -> None:
    """Backfills only currently-missing safe fields on an existing live event."""
    for field_name in _CLAIMABLE_FIELDS:
        if getattr(live_event, field_name) is None:
            new_value = getattr(event_data, field_name, None)
            if new_value is not None:
                setattr(live_event, field_name, new_value)


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
            place_is_resolved = False  # True only when cached place has real coordinates
            if event_data.location_name:
                venue = db.exec(select(Place).where(Place.name == event_data.location_name)).first()
                if venue:
                    place_candidate_id = venue.id
                    if venue.lat is not None and venue.lng is not None:
                        logger.info(f"[INGEST] Venue Match Found: '{event_data.location_name}'")
                        event_data.lat = venue.lat
                        event_data.lng = venue.lng
                        event_data.geocoding_status = "verified"
                        event_data.confidence_score = 1.0
                        place_is_resolved = True
                    else:
                        # Unresolved place candidate — link for moderation but do not
                        # treat as geocoding success; auto-approval must not fire.
                        logger.info(
                            "[INGEST] Venue match is unresolved; auto-approval disabled "
                            "for '%s' place_id=%s",
                            event_data.title,
                            venue.id,
                        )
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
                        logger.info(
                            "[INGEST] Geocoder resolved '%s' → status=%s lat=%s lng=%s",
                            event_data.location_name,
                            geo_res.geocoding_status,
                            geo_res.lat,
                            geo_res.lng,
                        )
                    else:
                        logger.warning(
                            "[INGEST] Geocoder returned no result for '%s'",
                            event_data.location_name,
                        )
                        from app.repositories.place_repository import PlaceRepository

                        unresolved = PlaceRepository(db).save_unresolved_place(
                            name=event_data.location_name,
                            country_code=event_data.country_code or "GR",
                            source_provider=event_data.source_provider,
                        )
                        place_candidate_id = unresolved.id
                        logger.info(
                            "[INGEST] Unresolved place candidate linked: '%s' id=%s",
                            event_data.location_name,
                            unresolved.id,
                        )
                else:
                    # Coordinates already present (scraper or upstream cleansing provided
                    # them), but venue is not yet in the Place cache.  If no upstream
                    # component set a meaningful status (the default is "failed"), mark
                    # "ambiguous" so batch-geocode doesn't retry events that already have
                    # coordinates.  Preserve an explicit status (e.g. "verified") that
                    # was set by CleansingService.
                    if event_data.geocoding_status == "failed":
                        event_data.geocoding_status = "ambiguous"
                        logger.info(
                            "[INGEST] Scraper-provided coords for '%s' (lat=%s lng=%s) — "
                            "status upgraded from failed to ambiguous.",
                            event_data.location_name,
                            event_data.lat,
                            event_data.lng,
                        )

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

            # Defense-in-depth: never auto-approve when the linked place has no coordinates,
            # regardless of what the trust engine decided based on event fields alone.
            if is_auto_approved and place_candidate_id and not place_is_resolved:
                is_auto_approved = False
                logger.info("[INGEST] Auto-Approve skipped: unresolved place candidate")

            existing_pending = db.exec(
                select(PendingEvent).where(
                    PendingEvent.title == event_data.title,
                    PendingEvent.start_time == event_data.start_time,
                    PendingEvent.location_name == event_data.location_name,
                )
            ).first()

            # FOMO-16: shared collision detection — reused by reconciliation and (in
            # the future) any user-submission endpoint. Finds the best matching live
            # event and the best matching pending event near the same place/time,
            # even when titles differ slightly.
            candidate_signature = signature_from_extracted(
                event_data, place_id=place_candidate_id, place_is_resolved=place_is_resolved
            )
            assessment = CollisionDetector(db).assess(
                candidate_signature,
                exclude_pending_id=existing_pending.id if existing_pending else None,
            )

            # A near-duplicate pending row (close but not byte-identical title/time)
            # is treated the same as the legacy exact-triple match: update it in
            # place instead of creating a second pending row for the same event.
            if existing_pending is None and assessment.best_pending_match is not None:
                if assessment.best_pending_match.score.bucket in (
                    CollisionBucket.exact_source_match,
                    CollisionBucket.high_confidence_collision,
                ):
                    existing_pending = db.get(PendingEvent, assessment.best_pending_match.target_id)

            # Conservative: never auto-approve a new live event out of a row that
            # already collides (at any confidence) with something else. Routine
            # re-scrapes of the same source (exact_source_match) are exempted —
            # that's the normal "update existing pending row" path, not a risk.
            if assessment.bucket in (
                CollisionBucket.possible_collision,
                CollisionBucket.high_confidence_collision,
            ):
                is_auto_approved = False

            pending_status = "published" if is_auto_approved else "pending"
            dedupe_status = _BUCKET_TO_DEDUPE_STATUS[assessment.bucket]
            candidate_event_id = (
                assessment.best_live_match.target_id if assessment.best_live_match else None
            )

            # FOMO-163: a moderator's rejected/published decision is protected — a
            # repeated scrape of the same event must not silently overwrite it.
            protected = existing_pending is not None and existing_pending.status in (
                "rejected",
                "published",
            )
            if protected:
                logger.info(
                    "[INGEST] Skipping update for protected pending event (status=%s): '%s'",
                    existing_pending.status,
                    event_data.title,
                )
            elif existing_pending:
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
                existing_pending.dedupe_status = dedupe_status
                existing_pending.candidate_event_id = candidate_event_id
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
                    dedupe_status=dedupe_status,
                    candidate_event_id=candidate_event_id,
                    place_candidate_id=place_candidate_id,
                    reviewed_by=None,
                    reviewed_at=None,
                    review_notes=None,
                )
                db.add(new_pending)
                added_count += 1

            if assessment.best_live_match is not None:
                action = (
                    "block_duplicate"
                    if assessment.bucket is CollisionBucket.high_confidence_collision
                    else "link_to_existing"
                    if assessment.bucket is CollisionBucket.exact_source_match
                    else "mark_possible_collision"
                )
            elif protected:
                action = "skip_protected"
            elif is_auto_approved:
                action = "create_new"
            else:
                action = "create_pending"
            log_assessment(assessment, source_provider=event_data.source_provider, action=action)

            if protected:
                pass
            elif (
                assessment.best_live_match is not None
                and assessment.best_live_match.score.bucket
                in (
                    CollisionBucket.exact_source_match,
                    CollisionBucket.high_confidence_collision,
                )
            ):
                # Already collides with a live event — never create a second one,
                # regardless of this candidate's own auto-approval eligibility.
                # Claim only safe/missing metadata onto the existing row.
                live_event = db.get(Event, assessment.best_live_match.target_id)
                if live_event is not None:
                    _claim_safe_metadata(live_event, event_data)
                    db.add(live_event)
            elif assessment.best_live_match is not None:
                # possible_collision against a live event: never silently merge or
                # auto-approve — leave the pending row as-is for moderator review.
                pass
            elif is_auto_approved:
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
                    status=EventStatus.live,
                    provenance=EventProvenance.aggregated,
                    trust_level=EventTrustLevel.unverified,
                    visibility=EventVisibility.public,
                    place_id=place_candidate_id,
                )
                db.add(live_event)

        db.commit()
        return IngestSummary(added=added_count, updated=updated_count)
