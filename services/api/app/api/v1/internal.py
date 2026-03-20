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
from app.core.datetime_utils import DateTimeHelper

router = APIRouter()
logger = logging.getLogger(__name__)


def internal_ingest_logic(db: Session, payload: EventIngest) -> IngestSummary:
    """Reusable ingestion logic for both API and background tasks."""
    added_count = 0
    updated_count = 0

    for event_data in payload.events:
        wkt_point = f"POINT({event_data.lng} {event_data.lat})"
        
        raw_content = event_data.event_metadata.get("raw_content") or payload.raw_content

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
            existing_pending.event_metadata = {**existing_pending.event_metadata, **event_data.event_metadata}
            existing_pending.raw_content = raw_content
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
                raw_content=raw_content,
                status="pending"
            )
            db.add(new_pending)
            added_count += 1

    db.commit()
    return IngestSummary(added=added_count, updated=updated_count)


async def run_scraper_and_ingest_task():
    """Background task with high-visibility debugging, robust parsing, and n8n notification."""
    print('>>> DEBUG: Background Task Entry Point', flush=True)
    
    try:
        script_path = "/app/services/harvester/simple_scraper.py"
        print(f">>> DEBUG: Python Executable: {sys.executable}", flush=True)
        print(f">>> DEBUG: Script Path Exists: {os.path.exists(script_path)}", flush=True)
        
        # 1. Execute Subprocess
        print('>>> DEBUG: Starting scraper subprocess...', flush=True)
        process = await asyncio.create_subprocess_exec(
            sys.executable, script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Protective timeout for the communication
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180.0)
        except asyncio.TimeoutError:
            process.kill()
            print(">>> DEBUG: ERROR - Subprocess timed out after 180s", flush=True)
            return

        print(f'>>> DEBUG: Subprocess finished with code {process.returncode}', flush=True)
        
        stdout_raw = stdout.decode()
        if process.returncode != 0:
            print(f">>> DEBUG: ERROR - Scraper script exited with error: {stderr.decode()}", flush=True)
            return

        # 2. Parse JSON
        try:
            scraped_data = json.loads(stdout_raw)
        except json.JSONDecodeError as e:
            print(f">>> DEBUG: ERROR - JSON parsing failed: {str(e)}", flush=True)
            print(f">>> DEBUG: Raw Stdout (first 100): {stdout_raw[:100]}", flush=True)
            return

        print(f">>> DEBUG: Successfully parsed {len(scraped_data)} items from scraper", flush=True)

        # 3. Map Data to Schema
        events_to_ingest = []
        for item in scraped_data:
            source = item.get("source")
            if source == "json-ld":
                data = item.get("structured_data", {})
                location = data.get("location", {})
                geo = location.get("geo", {}) if isinstance(location, dict) else {}
                
                # Handle potential list values in JSON-LD
                def get_first(val): return val[0] if isinstance(val, list) else val

                events_to_ingest.append(EventBase(
                    title=get_first(data.get("name", "Unknown Event")),
                    lat=float(get_first(geo.get("latitude", 0.0))) if geo.get("latitude") else 0.0,
                    lng=float(get_first(geo.get("longitude", 0.0))) if geo.get("longitude") else 0.0,
                    start_time=DateTimeHelper.safe_parse(data.get("startDate")),
                    end_time=DateTimeHelper.safe_parse(data.get("endDate")),
                    category="Music",
                    source_url=item.get("original_link"),
                    event_metadata=data
                ))
            elif source == "html-fallback":
                events_to_ingest.append(EventBase(
                    title=f"Pending: {item.get('original_link', 'New Event')}",
                    lat=0.0,
                    lng=0.0,
                    start_time=datetime.now(timezone.utc),
                    end_time=datetime.now(timezone.utc),
                    category="Uncategorized",
                    source_url=item.get("original_link"),
                    event_metadata={"raw_content": item.get("raw_text")}
                ))

        # 4. DB Ingestion
        summary = IngestSummary(added=0, updated=0)
        if events_to_ingest:
            print(f">>> DEBUG: Calling internal_ingest_logic with {len(events_to_ingest)} events", flush=True)
            try:
                payload = EventIngest(events=events_to_ingest)
                with Session(engine) as db:
                    summary = internal_ingest_logic(db, payload)
                print(f">>> DEBUG: Ingestion Result: Added={summary.added}, Updated={summary.updated}", flush=True)
            except Exception as db_err:
                print(f">>> DEBUG: DATABASE ERROR during ingestion: {str(db_err)}", flush=True)
                print(traceback.format_exc(), flush=True)
                # We continue to notification even on DB failure to keep n8n informed

        # 5. n8n Notification logic
        if settings.N8N_WEBHOOK_URL:
            print(f'>>> DEBUG: Attempting to notify n8n at {settings.N8N_WEBHOOK_URL}', flush=True)
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        settings.N8N_WEBHOOK_URL, 
                        json={
                            "status": "completed", 
                            "scraped_data": scraped_data
                        },
                        timeout=30.0
                    )
                    print(f">>> DEBUG: n8n notification successful. Status Code: {resp.status_code}", flush=True)
            except (httpx.ConnectError, httpx.TimeoutException) as conn_err:
                print(f">>> DEBUG: WEBHOOK ERROR (Connectivity/Timeout): {type(conn_err).__name__}", flush=True)
            except Exception as web_err:
                print(f">>> DEBUG: WEBHOOK ERROR (General): {type(web_err).__name__} - {str(web_err)}", flush=True)

    except Exception:
        print(">>> DEBUG: FATAL - GLOBAL EXCEPTION IN BACKGROUND TASK", flush=True)
        print(traceback.format_exc(), flush=True)


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
