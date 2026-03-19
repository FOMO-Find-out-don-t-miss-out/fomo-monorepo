from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_db
from app.models.event import Event, PendingEvent
from app.schemas.event import EventIngest, IngestSummary

router = APIRouter()


@router.post("/ingest", response_model=IngestSummary)
async def ingest_events(payload: EventIngest, db: Session = Depends(get_db)):
    """
    Ingests events from the harvester into the PendingEvent queue.
    """
    added_count = 0
    updated_count = 0

    for event_data in payload.events:
        wkt_point = f"POINT({event_data.lng} {event_data.lat})"
        
        # Check if already in Pending
        existing_pending = db.exec(
            select(PendingEvent).where(
                PendingEvent.title == event_data.title,
                PendingEvent.start_time == event_data.start_time
            )
        ).first()

        if existing_pending:
            # Update pending entry
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
            # Insert new pending entry
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


@router.post("/approve/{pending_id}")
async def approve_event(pending_id: UUID, db: Session = Depends(get_db)):
    """
    Approves a pending event and moves it to the main Event table.
    """
    pending = db.get(PendingEvent, pending_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Pending event not found")
    
    if pending.status == "approved":
        raise HTTPException(status_code=400, detail="Event already approved")

    # Create the live event
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
    
    # Update pending status
    pending.status = "approved"
    
    db.add(live_event)
    db.add(pending)
    db.commit()
    
    return {"message": "Event approved and moved to production", "event_id": live_event.id}
