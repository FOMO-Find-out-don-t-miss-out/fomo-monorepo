import asyncio
import json
import logging
import sys
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from geoalchemy2 import WKTElement
from sqlmodel import Session, select

from app.core.config import settings
from app.db.session import engine, get_db
from app.schemas.event import EventIngest, IngestSummary
from app.services.harvester.cleanser import CleansingService, ExtractedEvent
from app.services.harvester.geocoder import GeocoderService
from packages.domain.models import Event, PendingEvent, Venue

router = APIRouter()
logger = logging.getLogger(__name__)


def detect_country_from_url(url: str) -> str:
    """Detect country code from URL domain."""
    if not url:
        return "GR"
    url_lower = url.lower()
    if ".gr" in url_lower or "more.com" in url_lower:
        return "GR"
    if ".de" in url_lower:
        return "DE"
    if ".fr" in url_lower:
        return "FR"
    if ".it" in url_lower:
        return "IT"
    if ".es" in url_lower:
        return "ES"
    if ".nl" in url_lower:
        return "NL"
    if ".at" in url_lower:
        return "AT"
    if ".be" in url_lower:
        return "BE"
    if ".cy" in url_lower:
        return "CY"
    if ".co.uk" in url_lower or "uk." in url_lower:
        return "UK"
    return "GR"


def get_domain_from_url(url: str | None) -> str:
    """Extract domain from URL, removing www."""
    if not url:
        return "unknown"
    try:
        domain = urlparse(url).netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain or "unknown"
    except Exception:
        return "unknown"


async def internal_ingest_logic(db: Session, events: list[ExtractedEvent]) -> IngestSummary:
    """Ingests ExtractedEvent objects into the PendingEvent table with Auto-Approve Gate."""
    added_count = 0
    updated_count = 0

    for event_data in events:
        if event_data.category == "Junk":
            logger.info(f"[INGEST] Skipping junk (AI Category): {event_data.title}")
            continue

        junk_keywords = [
            "προσφορές",
            "προσφορά",
            "εκδηλώσεις",
            "εισιτήρια",
            "tickets",
            "offers",
            "newsletter",
            "τριήμερο",
            "διήμερο",
        ]
        if (
            any(keyword in event_data.title.lower() for keyword in junk_keywords)
            and len(event_data.title) < 100
        ):
            logger.info(f"[INGEST] Skipping junk (Title Match): {event_data.title}")
            continue

        # Ensure event_metadata is a dict
        if not isinstance(event_data.event_metadata, dict):
            logger.warning(f"event_metadata for '{event_data.title}' is not a dict, fixing.")
            event_data.event_metadata = {}

        if event_data.location_name:
            venue = db.exec(select(Venue).where(Venue.name == event_data.location_name)).first()
            if venue:
                logger.info(f"[INGEST] Venue Match Found: '{event_data.location_name}'")
                event_data.lat = venue.lat
                event_data.lng = venue.lng
                event_data.geocoding_status = "verified"
                event_data.confidence_score = 1.0
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
                from app.repositories.venue_repository import VenueRepository

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

                VenueRepository(db).save_venue(
                    name=event_data.location_name,
                    country_code=event_data.country_code or "GR",
                    lat=event_data.lat,
                    lng=event_data.lng,
                    full_address=event_data.street_address or event_data.location_name,
                    relevance=event_data.confidence_score or 0.9,
                    city=str(final_city) if final_city else None,
                )

        is_auto_approved = (
            event_data.ingestion_method == "json_ld"
            and event_data.geocoding_status == "verified"
            and (event_data.confidence_score or 0) >= 0.9
            and event_data.start_time > datetime.now(UTC)
        )

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
                    parent_id=live_id,
                )
                db.add(live_event)

    db.commit()
    return IngestSummary(added=added_count, updated=updated_count)


async def run_scraper_and_ingest_task(default_country: str = "GR") -> None:
    """Background task to run scraper, cleanse data using AI fallbacks, and ingest."""
    logger.info(f"Background Task: Starting pipeline (country={default_country})")

    try:
        # Resolve script path relative to this file (app/api/v1/internal.py)
        # to app/services/harvester/simple_scraper.py
        current_file = Path(__file__)
        script_path = (
            current_file.parent.parent.parent / "services" / "harvester" / "simple_scraper.py"
        )

        if not script_path.exists():
            logger.error(f"Scraper script not found at {script_path}")
            return

        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180.0)
        except TimeoutError:
            process.kill()
            logger.error("Scraper subprocess timed out")
            return

        if process.returncode != 0:
            logger.error(f"Scraper error {process.returncode}: {stderr.decode()}")
            return

        try:
            raw_scraped_data = json.loads(stdout.decode())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse scraper JSON: {e}")
            return

        logger.info(f"Scraper returned {len(raw_scraped_data)} raw items")

        cleaned_events: list[ExtractedEvent] = []
        for item in raw_scraped_data:
            source = item.get("source")
            original_link = item.get("original_link")
            country_hint = (
                detect_country_from_url(original_link) if original_link else default_country
            )

            source_domain = "unknown"
            if original_link:
                try:
                    source_domain = urlparse(original_link).netloc
                    if source_domain.startswith("www."):
                        source_domain = source_domain[4:]
                except Exception:
                    source_domain = "unknown"

            try:
                if source == "schema_org":
                    extracted = await CleansingService.clean_json_ld(
                        item.get("structured_data", {}), country_hint, source_domain=source_domain
                    )
                    if isinstance(extracted, list):
                        for ev in extracted:
                            ev.event_metadata["original_link"] = original_link
                            ev.country_code = country_hint
                            cleaned_events.append(ev)
                    elif extracted:
                        extracted.event_metadata["original_link"] = original_link
                        extracted.country_code = country_hint
                        cleaned_events.append(extracted)
                elif source == "registry":
                    extracted = ExtractedEvent(
                        title=item.get("title") or "Untitled Event",
                        start_time=item.get("start_time"),
                        end_time=item.get("end_time"),
                        location_name=item.get("location_name"),
                        description=item.get("description"),
                        country_code=country_hint,
                        source_provider=source_domain,
                        ingestion_method="registry",
                        event_metadata={"original_link": original_link},
                    )
                    if (extracted.lat is None or extracted.lng is None) and extracted.location_name:
                        geo_res = await GeocoderService.get_coordinates(
                            extracted.location_name,
                            country_hint,
                            search_term=extracted.location_name,
                        )
                        if geo_res:
                            extracted.lat, extracted.lng = geo_res.lat, geo_res.lng
                            extracted.confidence_score = geo_res.relevance
                            extracted.geocoding_status = geo_res.geocoding_status
                            extracted.geocoding_metadata = geo_res.geocoding_metadata
                    cleaned_events.append(extracted)
                elif source == "llm_fallback":
                    extracted_list = await CleansingService.clean_html_fallback(
                        item.get("raw_text", ""), country_hint, source_domain=source_domain
                    )
                    for extracted in extracted_list:
                        extracted.event_metadata["original_link"] = original_link
                        extracted.country_code = country_hint
                        cleaned_events.append(extracted)
            except Exception as e:
                logger.error(f"Error processing item from {source}: {e}")
                continue

        logger.info(f"Cleansing: {len(cleaned_events)}/{len(raw_scraped_data)} valid")

        summary = IngestSummary(added=0, updated=0)
        if cleaned_events:
            try:
                with Session(engine) as db:
                    summary = await internal_ingest_logic(db, cleaned_events)
                logger.info(f"Ingest Result: Added={summary.added}, Updated={summary.updated}")
            except Exception as db_err:
                logger.error(f"Database error during ingestion: {db_err}")

        if settings.N8N_WEBHOOK_URL:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        settings.N8N_WEBHOOK_URL,
                        json={
                            "status": "completed",
                            "summary": {
                                "raw_count": len(raw_scraped_data),
                                "cleaned_count": len(cleaned_events),
                                "db_added": summary.added,
                                "db_updated": summary.updated,
                            },
                            "default_country": default_country,
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                        timeout=10.0,
                    )
            except Exception as web_err:
                logger.warning(f"Failed to notify n8n: {web_err}")

    except Exception:
        logger.error(f"Fatal exception in background task:\n{traceback.format_exc()}")


@router.post("/ingest", response_model=IngestSummary)
async def ingest_events(
    payload: EventIngest, db: Annotated[Session, Depends(get_db)]
) -> IngestSummary:
    """Manual ingestion endpoint for pre-formatted EventIngest payloads."""
    extracted_list = []
    for e in payload.events:
        extracted_list.append(
            ExtractedEvent(
                title=e.title,
                start_time=e.safe_start_time,
                end_time=e.safe_end_time,
                lat=e.lat,
                lng=e.lng,
                category=e.category,
                hype_score=e.hype_score,
                ticket_url=e.ticket_url,
                source_provider=get_domain_from_url(e.source_url),
                ingestion_method="manual",
                event_metadata={**e.event_metadata, "original_link": e.source_url},
            )
        )
    return await internal_ingest_logic(db, extracted_list)


@router.post("/approve/{pending_id}")
async def approve_event(
    pending_id: UUID, db: Annotated[Session, Depends(get_db)]
) -> dict[str, Any]:
    pending = db.get(PendingEvent, pending_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Pending event not found")

    if pending.status == "published":
        raise HTTPException(status_code=400, detail="Event already approved/published")

    primary_id = uuid4()
    live_event = Event(
        id=primary_id,
        title=pending.title,
        description=pending.description,
        location=pending.location,
        location_name=pending.location_name,
        country_code=pending.country_code,
        start_time=pending.start_time,
        end_time=pending.end_time,
        category=pending.category,
        sub_category=pending.sub_category,
        tags=pending.tags,
        hype_score=pending.hype_score,
        ticket_url=pending.ticket_url,
        source_url=pending.source_url,
        source_provider=pending.source_provider,
        ingestion_method=pending.ingestion_method,
        event_metadata=pending.event_metadata,
        geocoding_status=pending.geocoding_status,
        geocoding_metadata=pending.geocoding_metadata,
        parent_id=primary_id,
    )
    db.add(live_event)

    occurrences = pending.event_metadata.get("occurrences", [])
    for occ in occurrences:
        occ_start = datetime.fromisoformat(occ["start_time"])
        occ_event = Event(
            title=pending.title,
            description=pending.description,
            location=pending.location,
            location_name=pending.location_name,
            country_code=pending.country_code,
            start_time=occ_start,
            end_time=None,
            category=pending.category,
            sub_category=pending.sub_category,
            tags=pending.tags,
            hype_score=pending.hype_score,
            ticket_url=pending.ticket_url,
            source_url=pending.source_url,
            source_provider=pending.source_provider,
            ingestion_method=pending.ingestion_method,
            event_metadata=pending.event_metadata,
            geocoding_status=pending.geocoding_status,
            geocoding_metadata=pending.geocoding_metadata,
            parent_id=primary_id,
        )
        db.add(occ_event)

    pending.status = "published"
    db.add(pending)
    db.commit()
    return {
        "message": "Event approved",
        "event_id": primary_id,
        "occurrences_created": len(occurrences),
    }


@router.delete("/cleanup-pending", status_code=status.HTTP_200_OK)
async def cleanup_pending_events(
    db: Annotated[Session, Depends(get_db)], days_old: int = 30
) -> dict[str, Any]:
    """Deletes 'published' pending events older than a given number of days."""
    cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

    statement = select(PendingEvent).where(
        PendingEvent.status == "published", PendingEvent.start_time < cutoff_date
    )
    old_events = db.exec(statement).all()
    deleted_count = 0
    for ev in old_events:
        db.delete(ev)
        deleted_count += 1

    db.commit()
    return {"message": "Cleanup complete", "deleted_count": deleted_count}


@router.delete("/reject/{pending_id}")
async def reject_event(pending_id: UUID, db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    pending = db.get(PendingEvent, pending_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Pending event not found")

    db.delete(pending)
    db.commit()
    return {"message": "Event rejected and deleted"}


@router.post("/run-scraper", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scraper(
    background_tasks: BackgroundTasks, default_country: str = "GR"
) -> dict[str, Any]:
    """Triggers the scraper and cleanser pipeline in the background."""
    background_tasks.add_task(run_scraper_and_ingest_task, default_country)
    return {"message": "Scraper started in background", "default_country": default_country}


@router.post("/batch-geocode", status_code=status.HTTP_202_ACCEPTED)
async def trigger_batch_geocode(
    background_tasks: BackgroundTasks, batch_size: int = 50
) -> dict[str, Any]:
    """Batch geocode all pending_events that need geocoding."""

    async def _run_batch_geocode() -> None:
        stats = await GeocoderService.batch_geocode_pending_events(batch_size=batch_size)
        logger.info(f"Batch geocoding completed: {stats}")

    background_tasks.add_task(_run_batch_geocode)
    return {"message": "Batch geocoding started in background", "batch_size": batch_size}
