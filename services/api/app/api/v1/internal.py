import json
import asyncio
import httpx
import logging
import sys
import os
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select
from app.db.session import get_db, engine
from app.models.event import Event, PendingEvent
from app.schemas.event import EventIngest, IngestSummary, EventBase
from app.core.config import settings
from app.utils.datetime_utils import DateTimeHelper
from app.services.harvester.cleanser import CleansingService, ExtractedEvent

router = APIRouter()
logger = logging.getLogger(__name__)


def internal_ingest_logic(db: Session, events: List[ExtractedEvent]) -> IngestSummary:
    """Ingests ExtractedEvent objects into the PendingEvent table."""
    added_count = 0
    updated_count = 0

    for event_data in events:
        wkt_point = f"POINT({event_data.lng} {event_data.lat})"
        
        existing_pending = db.exec(
            select(PendingEvent).where(
                PendingEvent.title == event_data.title,
                PendingEvent.start_time == event_data.start_time
            )
        ).first()

        if existing_pending:
            existing_pending.end_time = event_data.end_time
            existing_pending.category = event_data.category
            existing_pending.location = wkt_point
            existing_pending.ticket_url = event_data.ticket_url
            # Preserve existing source_url if new one is missing
            if event_data.event_metadata.get("original_link"):
                existing_pending.source_url = event_data.event_metadata["original_link"]
            
            existing_pending.event_metadata = {**existing_pending.event_metadata, **event_data.event_metadata}
            db.add(existing_pending)
            updated_count += 1
        else:
            new_pending = PendingEvent(
                title=event_data.title,
                location=wkt_point,
                start_time=event_data.start_time,
                end_time=event_data.end_time,
                category=event_data.category,
                hype_score=event_data.hype_score,
                ticket_url=event_data.ticket_url,
                source_url=event_data.event_metadata.get("original_link"),
                event_metadata=event_data.event_metadata,
                status="pending"
            )
            db.add(new_pending)
            added_count += 1

    db.commit()
    return IngestSummary(added=added_count, updated=updated_count)


async def run_scraper_and_ingest_task():
    """Background task to run scraper, cleanse data using AI fallbacks, and ingest."""
    logger.info("Background Task: Starting scraper pipeline")
    
    try:
        # 1. Execute Subprocess Scraper
        script_path = "/app/services/harvester/simple_scraper.py"
        process = await asyncio.create_subprocess_exec(
            sys.executable, script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180.0)
        except asyncio.TimeoutError:
            process.kill()
            logger.error("Scraper subprocess timed out")
            return

        if process.returncode != 0:
            logger.error(f"Scraper exited with code {process.returncode}: {stderr.decode()}")
            return

        # 2. Parse Raw JSON
        try:
            raw_scraped_data = json.loads(stdout.decode())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse scraper JSON: {e}")
            return

        logger.info(f"Scraper returned {len(raw_scraped_data)} raw items")

        # 3. Cleansing & Mapping
        cleaned_events: List[ExtractedEvent] = []
        for item in raw_scraped_data:
            source = item.get("source")
            extracted = None

            if source == "json-ld":
                extracted = CleansingService.clean_json_ld(item.get("structured_data", {}))
            elif source == "html-fallback":
                # AI-powered extraction for raw HTML/Text
                extracted = await CleansingService.clean_html_fallback(item.get("raw_text", ""))
            
            if extracted:
                # Ensure the original link is preserved in metadata for the ingest logic
                extracted.event_metadata["original_link"] = item.get("original_link")
                cleaned_events.append(extracted)

        logger.info(f"Cleansing complete: {len(cleaned_events)}/{len(raw_scraped_data)} items valid")

        # 4. DB Ingestion
        summary = IngestSummary(added=0, updated=0)
        if cleaned_events:
            try:
                with Session(engine) as db:
                    summary = internal_ingest_logic(db, cleaned_events)
                logger.info(f"Ingestion Result: Added={summary.added}, Updated={summary.updated}")
            except Exception as db_err:
                logger.error(f"Database error during ingestion: {db_err}")

        # 5. n8n Notification
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
                                "db_updated": summary.updated
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        timeout=10.0
                    )
            except Exception as web_err:
                logger.warning(f"Failed to notify n8n: {web_err}")

    except Exception:
        logger.error(f"Fatal exception in background task:\n{traceback.format_exc()}")


@router.post("/ingest", response_model=IngestSummary)
async def ingest_events(payload: EventIngest, db: Session = Depends(get_db)):
    """Manual ingestion endpoint for pre-formatted EventIngest payloads."""
    # Convert EventBase to ExtractedEvent for compatibility with internal_ingest_logic
    extracted_list = []
    for e in payload.events:
        extracted_list.append(ExtractedEvent(
            title=e.title,
            start_time=e.start_time,
            end_time=e.end_time,
            lat=e.lat,
            lng=e.lng,
            category=e.category,
            hype_score=e.hype_score,
            ticket_url=e.ticket_url,
            event_metadata={**e.event_metadata, "original_link": e.source_url}
        ))
    return internal_ingest_logic(db, extracted_list)


@router.post("/approve/{pending_id}")
async def approve_event(pending_id: UUID, db: Session = Depends(get_db)):
    pending = db.get(PendingEvent, pending_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Pending event not found")
    
    if pending.status == "approved":
        raise HTTPException(status_code=400, detail="Event already approved")

    live_event = Event(
        title=pending.title,
        location=pending.location,
        start_time=pending.start_time,
        end_time=pending.end_time,
        category=pending.category,
        hype_score=pending.hype_score,
        ticket_url=pending.ticket_url,
        source_url=pending.source_url,
        event_metadata=pending.event_metadata
    )
    pending.status = "approved"
    db.add(live_event)
    db.add(pending)
    db.commit()
    return {"message": "Event approved", "event_id": live_event.id}


@router.post("/run-scraper", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scraper(background_tasks: BackgroundTasks):
    """Triggers the scraper and cleanser pipeline in the background."""
    background_tasks.add_task(run_scraper_and_ingest_task)
    return {"message": "Scraper started in background"}
