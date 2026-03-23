from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.db.session import get_db
from app.models.event import PendingEvent, Event
from app.models.venue import Venue
from app.schemas.moderation import (
    PendingEventUpdate, 
    VenueUpdate, 
    BatchApproveRequest, 
    BatchRejectRequest, 
    VenueMergeRequest,
    LocationBatchUpdate,
    OccurrenceCreate,
    GeocodeSuggestion,
    PendingEventResponse
)
from app.services.moderation.moderation_service import ModerationService
from app.services.moderation.venue_service import VenueModerationService
from app.services.harvester.geocoder import GeocoderService
from geoalchemy2.shape import to_shape
from shapely.wkb import loads as wkb_loads
import binascii

router = APIRouter()

def _to_pending_event_response(ev: Any) -> PendingEventResponse:
    # Handle location serialization manually
    location_data = None
    if ev.location is not None:
        try:
            # Try to_shape first (for WKBElement)
            shape = to_shape(ev.location)
            location_data = {"type": "Point", "coordinates": [shape.x, shape.y]}
        except Exception:
            try:
                # Try parsing as hex WKB string if it's a string
                if isinstance(ev.location, str):
                    shape = wkb_loads(binascii.unhexlify(ev.location))
                    location_data = {"type": "Point", "coordinates": [shape.x, shape.y]}
                else:
                    location_data = str(ev.location)
            except Exception:
                location_data = str(ev.location)
            
    return PendingEventResponse(
        id=ev.id,
        title=ev.title,
        start_time=ev.start_time,
        end_time=ev.end_time,
        hype_score=ev.hype_score,
        category=ev.category,
        sub_category=ev.sub_category,
        ticket_url=ev.ticket_url,
        source_url=ev.source_url,
        location_name=ev.location_name,
        country_code=ev.country_code,
        parent_id=ev.parent_id,
        location=location_data,
        photo_url=ev.photo_url,
        event_metadata=ev.event_metadata,
        tags=ev.tags,
        status=getattr(ev, 'status', 'published'),
        raw_content=getattr(ev, 'raw_content', None),
        rejection_reason=getattr(ev, 'rejection_reason', None),
        confidence_score=getattr(ev, 'confidence_score', None),
        geocoding_status=getattr(ev, 'geocoding_status', 'verified'),
        geocoding_metadata=getattr(ev, 'geocoding_metadata', {})
    )

@router.get("/pending-events", response_model=List[PendingEventResponse])
def get_pending_events(
    location_name: Optional[str] = None,
    geocoding_status: Optional[List[str]] = Query(None),
    session: Session = Depends(get_db)
):
    statement = select(PendingEvent).where(PendingEvent.status == "pending")
    if location_name:
        statement = statement.where(PendingEvent.location_name == location_name)
    if geocoding_status:
        statement = statement.where(PendingEvent.geocoding_status.in_(geocoding_status))
    
    statement = statement.order_by(PendingEvent.location_name)
    events = session.exec(statement).all()
    return [_to_pending_event_response(e) for e in events]

@router.get("/events", response_model=List[PendingEventResponse])
def get_published_events(
    location_name: Optional[str] = None,
    session: Session = Depends(get_db)
):
    service = ModerationService(session)
    events = service.get_published_events(location_name)
    return [_to_pending_event_response(e) for e in events]

@router.post("/events/{event_id}/unpublish")
def unpublish_event(
    event_id: UUID,
    session: Session = Depends(get_db)
):
    service = ModerationService(session)
    success = service.unpublish_event(event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Published event not found")
    return {"status": "success"}

@router.patch("/events/{event_id}", response_model=PendingEventResponse)
def update_published_event(
    event_id: UUID,
    update: PendingEventUpdate,
    session: Session = Depends(get_db)
):
    service = ModerationService(session)
    updated = service.update_published_event(event_id, **update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Published event not found")
    return _to_pending_event_response(updated)

@router.patch("/pending-events/{event_id}", response_model=PendingEventResponse)
def update_pending_event(
    event_id: UUID,
    update: PendingEventUpdate,
    session: Session = Depends(get_db)
):
    service = ModerationService(session)
    updated = service.update_pending_event(event_id, **update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Pending event not found")
    return _to_pending_event_response(updated)

@router.post("/pending-events/{event_id}/approve")
def approve_event(
    event_id: UUID,
    session: Session = Depends(get_db)
):
    service = ModerationService(session)
    count = service.approve_events([event_id])
    if count == 0:
        raise HTTPException(status_code=404, detail="Pending event not found or already published")
    return {"status": "success", "approved_count": count}

@router.post("/pending-events/{event_id}/reject")
def reject_event(
    event_id: UUID,
    session: Session = Depends(get_db)
):
    service = ModerationService(session)
    count = service.reject_events([event_id])
    if count == 0:
        raise HTTPException(status_code=404, detail="Pending event not found")
    return {"status": "success", "rejected_count": count}

@router.post("/pending-events/approve-batch")
def approve_events_batch(
    request: BatchApproveRequest,
    session: Session = Depends(get_db)
):
    service = ModerationService(session)
    count = service.approve_events(request.event_ids)
    return {"status": "success", "approved_count": count}

@router.post("/pending-events/reject-batch")
def reject_events_batch(
    request: BatchRejectRequest,
    session: Session = Depends(get_db)
):
    service = ModerationService(session)
    count = service.reject_events(request.event_ids)
    return {"status": "success", "rejected_count": count}

@router.post("/pending-events/{event_id}/occurrences", response_model=PendingEventResponse)
def add_occurrence(
    event_id: UUID,
    occurrence: OccurrenceCreate,
    session: Session = Depends(get_db)
):
    service = ModerationService(session)
    new_occ = service.add_occurrence(event_id, occurrence.start_time)
    if not new_occ:
        raise HTTPException(status_code=404, detail="Pending event not found")
    return _to_pending_event_response(new_occ)

@router.get("/venues", response_model=List[Venue])
def get_venues(
    search_query: Optional[str] = None,
    only_unverified: bool = False,
    session: Session = Depends(get_db)
):
    statement = select(Venue).order_by(Venue.name)
    if search_query:
        statement = statement.where(Venue.name.ilike(f"%{search_query}%"))
    if only_unverified:
        statement = statement.where(Venue.is_manually_verified == False)
    return session.exec(statement).all()

@router.patch("/venues/{venue_id}", response_model=Venue)
def update_venue(
    venue_id: UUID,
    update: VenueUpdate,
    session: Session = Depends(get_db)
):
    service = VenueModerationService(session)
    updated = service.update_venue_record(venue_id, **update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Venue not found")
    return updated

@router.delete("/venues/{venue_id}")
def delete_venue(
    venue_id: UUID,
    session: Session = Depends(get_db)
):
    service = VenueModerationService(session)
    success = service.delete_venue_and_unlink_events(venue_id)
    if not success:
        raise HTTPException(status_code=404, detail="Venue not found")
    return {"status": "success"}

@router.post("/venues/merge")
def merge_venues(
    request: VenueMergeRequest,
    session: Session = Depends(get_db)
):
    service = VenueModerationService(session)
    success = service.merge_venues(request.source_venue_id, request.target_venue_id)
    if not success:
        raise HTTPException(status_code=404, detail="One or both venues not found")
    return {"status": "success"}

@router.post("/batch-update-location")
def batch_update_location(
    request: LocationBatchUpdate,
    session: Session = Depends(get_db)
):
    service = ModerationService(session)
    wkt_str = f"POINT({request.lng} {request.lat})"
    service.batch_update_location_by_name(
        request.target_name,
        wkt_str,
        request.status,
        request.confidence,
        request.metadata
    )
    return {"status": "success"}

@router.get("/geocode/suggestions", response_model=List[GeocodeSuggestion])
async def get_geocode_suggestions(
    q: str,
    country_code: str = "GR"
):
    suggestions = await GeocoderService.get_suggestions(q, country_code)
    return suggestions
