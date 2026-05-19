import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.session import get_db
from app.schemas.event import EventIngest, IngestSummary
from app.services.harvester.ingestor import IngestionService
from app.services.harvester.location.geocoder import GeocoderService
from app.services.harvester.orchestrator import HarvesterOrchestrator
from packages.domain.models import (
    Event,
    EventProvenance,
    EventStatus,
    EventTrustLevel,
    EventVisibility,
    PendingEvent,
)
from packages.domain.schemas.extracted_event import ExtractedEvent
from packages.domain.utils.url_utils import get_domain_from_url

router = APIRouter()
logger = logging.getLogger(__name__)


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
    return await IngestionService.ingest_events(db, extracted_list)


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
        place_id=pending.place_candidate_id,
        status=EventStatus.live,
        provenance=EventProvenance.aggregated,
        trust_level=EventTrustLevel.unverified,
        visibility=EventVisibility.public,
        approved_at=datetime.now(UTC),
        published_at=datetime.now(UTC),
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
            place_id=pending.place_candidate_id,
            status=EventStatus.live,
            provenance=EventProvenance.aggregated,
            trust_level=EventTrustLevel.unverified,
            visibility=EventVisibility.public,
            approved_at=datetime.now(UTC),
            published_at=datetime.now(UTC),
        )
        db.add(occ_event)

    pending.status = "published"
    pending.reviewed_at = datetime.now(UTC)
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
    background_tasks.add_task(HarvesterOrchestrator.run_pipeline, default_country)
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
