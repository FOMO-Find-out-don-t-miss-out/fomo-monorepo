import json
import asyncio
import httpx
import logging
from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select
from app.db.session import get_db, engine
from app.models.event import Event, PendingEvent
from app.schemas.event import EventIngest, IngestSummary
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def internal_ingest_logic(db: Session, payload: EventIngest) -> IngestSummary:
    """Reusable ingestion logic for both API and background tasks."""
    added_count = 0
    updated_count = 0

    for event_data in payload.events:
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
            existing_pending.source_url = event_data.source_url
            existing_pending.event_metadata = event_data.event_metadata
            existing_pending.raw_content = payload.raw_content
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
                source_url=event_data.source_url,
                event_metadata=event_data.event_metadata,
                raw_content=payload.raw_content,
                status="pending"
            )
            db.add(new_pending)
            added_count += 1

    db.commit()
    return IngestSummary(added=added_count, updated=updated_count)


async def run_scraper_and_ingest_task():
    """Background task to run scraper, ingest results, and notify n8n."""
    script_path = "/app/services/harvester/simple_scraper.py"
    
    try:
        process = await asyncio.create_subprocess_exec(
            "python", script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"Scraper task failed: {stderr.decode()}")
            return

        scraped_data = json.loads(stdout.decode())
        
        # Note: Since the simple_scraper returns raw objects or JSON-LD, 
        # a real production app would use an LLM/Parser here to map to EventBase.
        # For this logic, we'll assume the ingestion logic handles the mapping 
        # or we ingest a placeholder for the moderation queue to see.
        
        added, updated = 0, 0
        with Session(engine) as db:
            # Placeholder mapping logic - in a real scenario, you'd map scraped_data fields
            # Here we just acknowledge the script finished and log results.
            logger.info(f"Scraper finished. Processed {len(scraped_data)} raw items.")

        # Notify n8n if URL is configured
        if settings.N8N_WEBHOOK_URL:
            async with httpx.AsyncClient() as client:
                await client.post(
                    settings.N8N_WEBHOOK_URL, 
                    json={
                        "status": "completed", 
                        "items_scraped": len(scraped_data),
                        "source": "scraper_v1"
                    }
                )

    except Exception as e:
        logger.error(f"Error in background scraper task: {str(e)}")


@router.post("/ingest", response_model=IngestSummary)
async def ingest_events(payload: EventIngest, db: Session = Depends(get_db)):
    return internal_ingest_logic(db, payload)


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
    """
    Triggers the scraper in the background and returns 202 immediately.
    """
    background_tasks.add_task(run_scraper_and_ingest_task)
    return {"message": "Scraper started in background"}
