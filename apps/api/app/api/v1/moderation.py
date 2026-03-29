import binascii
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.shape import to_shape
from shapely.wkb import loads as wkb_loads
from sqlmodel import Session, select

from app.db.session import get_db
from app.schemas.moderation import (
    BatchApproveRequest,
    BatchRejectRequest,
    LocationBatchUpdate,
    OccurrenceCreate,
    PendingEventResponse,
    PendingEventUpdate,
    VenueMergeRequest,
    VenueUpdate,
)
from app.services.harvester.geocoder import GeocodeResult, GeocoderService
from app.services.moderation.moderation_service import ModerationService
from app.services.moderation.venue_service import VenueModerationService
from packages.domain.models import Event, PendingEvent, Venue

router = APIRouter()


def _to_pending_event_response(ev: PendingEvent | Event) -> PendingEventResponse:
    # Handle location serialization manually
    location_data: dict[str, Any] | str | None = None
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
        source_provider=ev.source_provider,
        ingestion_method=ev.ingestion_method,
        location_name=ev.location_name,
        country_code=ev.country_code,
        parent_id=ev.parent_id,
        location=location_data,
        photo_url=ev.photo_url,
        event_metadata=ev.event_metadata,
        tags=ev.tags,
        status=getattr(ev, "status", "published"),
        raw_content=getattr(ev, "raw_content", None),
        rejection_reason=getattr(ev, "rejection_reason", None),
        confidence_score=getattr(ev, "confidence_score", None),
        geocoding_status=getattr(ev, "geocoding_status", "verified"),
        geocoding_metadata={
            **getattr(ev, "geocoding_metadata", {}),
            "full_address": getattr(ev, "geocoding_metadata", {}).get("full_address")
            or ev.location_name,
        },
    )


@router.get("/pending-events", response_model=list[PendingEventResponse])
def get_pending_events(
    session: Annotated[Session, Depends(get_db)],
    location_name: str | None = None,
    geocoding_status: Annotated[list[str] | None, Query()] = None,
) -> list[PendingEventResponse]:
    statement = select(PendingEvent).where(PendingEvent.status == "pending")
    if location_name:
        statement = statement.where(PendingEvent.location_name == location_name)
    if geocoding_status:
        statement = statement.where(PendingEvent.geocoding_status.in_(geocoding_status))

    statement = statement.order_by(PendingEvent.location_name)
    events = session.exec(statement).all()
    return [_to_pending_event_response(e) for e in events]


@router.get("/events", response_model=list[PendingEventResponse])
def get_published_events(
    session: Annotated[Session, Depends(get_db)],
    location_name: str | None = None,
) -> list[PendingEventResponse]:
    service = ModerationService(session)
    events = service.get_published_events(location_name)
    return [_to_pending_event_response(e) for e in events]


@router.post("/events/{event_id}/unpublish")
def unpublish_event(
    event_id: Annotated[UUID, Any], session: Annotated[Session, Depends(get_db)]
) -> dict[str, str]:
    service = ModerationService(session)
    success = service.unpublish_event(event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Published event not found")
    return {"status": "success"}


@router.patch("/events/{event_id}", response_model=PendingEventResponse)
def update_published_event(
    event_id: Annotated[UUID, Any],
    update: PendingEventUpdate,
    session: Annotated[Session, Depends(get_db)],
) -> PendingEventResponse:
    service = ModerationService(session)
    updated = service.update_published_event(event_id, **update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Published event not found")
    return _to_pending_event_response(updated)


@router.patch("/pending-events/{event_id}", response_model=PendingEventResponse)
def update_pending_event(
    event_id: Annotated[UUID, Any],
    update: PendingEventUpdate,
    session: Annotated[Session, Depends(get_db)],
) -> PendingEventResponse:
    service = ModerationService(session)
    updated = service.update_pending_event(event_id, **update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Pending event not found")
    return _to_pending_event_response(updated)


@router.post("/pending-events/{event_id}/approve")
def approve_event(
    event_id: Annotated[UUID, Any], session: Annotated[Session, Depends(get_db)]
) -> dict[str, Any]:
    service = ModerationService(session)
    count = service.approve_events([event_id])
    if count == 0:
        raise HTTPException(status_code=404, detail="Pending event not found or already published")
    return {"status": "success", "approved_count": count}


@router.post("/pending-events/{event_id}/reject")
def reject_event(
    event_id: Annotated[UUID, Any], session: Annotated[Session, Depends(get_db)]
) -> dict[str, Any]:
    service = ModerationService(session)
    count = service.reject_events([event_id])
    if count == 0:
        raise HTTPException(status_code=404, detail="Pending event not found")
    return {"status": "success", "rejected_count": count}


@router.post("/pending-events/approve-batch")
def approve_events_batch(
    request: BatchApproveRequest, session: Annotated[Session, Depends(get_db)]
) -> dict[str, Any]:
    service = ModerationService(session)
    count = service.approve_events(request.event_ids)
    return {"status": "success", "approved_count": count}


@router.post("/pending-events/reject-batch")
def reject_events_batch(
    request: BatchRejectRequest, session: Annotated[Session, Depends(get_db)]
) -> dict[str, Any]:
    service = ModerationService(session)
    count = service.reject_events(request.event_ids)
    return {"status": "success", "rejected_count": count}


@router.post("/pending-events/{event_id}/occurrences", response_model=PendingEventResponse)
def add_occurrence(
    event_id: Annotated[UUID, Any],
    occurrence: OccurrenceCreate,
    session: Annotated[Session, Depends(get_db)],
) -> PendingEventResponse:
    service = ModerationService(session)
    new_occ = service.add_occurrence(event_id, occurrence.start_time)
    if not new_occ:
        raise HTTPException(status_code=404, detail="Pending event not found")
    return _to_pending_event_response(new_occ)


@router.get("/venues", response_model=list[Venue])
def get_venues(
    session: Annotated[Session, Depends(get_db)],
    search_query: str | None = None,
    only_unverified: bool = False,
) -> list[Venue]:
    statement = select(Venue).order_by(Venue.name)
    if search_query:
        statement = statement.where(Venue.name.ilike(f"%{search_query}%"))
    if only_unverified:
        statement = statement.where(not Venue.is_manually_verified)
    return list(session.exec(statement).all())


@router.patch("/venues/{venue_id}", response_model=Venue)
def update_venue(
    venue_id: Annotated[UUID, Any],
    update: VenueUpdate,
    session: Annotated[Session, Depends(get_db)],
) -> Venue:
    service = VenueModerationService(session)
    updated = service.update_venue_record(venue_id, **update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Venue not found")
    return updated


@router.delete("/venues/{venue_id}")
def delete_venue(
    venue_id: Annotated[UUID, Any], session: Annotated[Session, Depends(get_db)]
) -> dict[str, str]:
    service = VenueModerationService(session)
    success = service.delete_venue_and_unlink_events(venue_id)
    if not success:
        raise HTTPException(status_code=404, detail="Venue not found")
    return {"status": "success"}


@router.post("/venues/merge")
def merge_venues(
    request: VenueMergeRequest, session: Annotated[Session, Depends(get_db)]
) -> dict[str, str]:
    service = VenueModerationService(session)
    success = service.merge_venues(request.source_venue_id, request.target_venue_id)
    if not success:
        raise HTTPException(status_code=404, detail="One or both venues not found")
    return {"status": "success"}


@router.post("/batch-update-location")
def batch_update_location(
    request: LocationBatchUpdate, session: Annotated[Session, Depends(get_db)]
) -> dict[str, str]:
    service = ModerationService(session)
    wkt_str = f"POINT({request.lng} {request.lat})"
    service.batch_update_location_by_name(
        request.target_name, wkt_str, request.status, request.confidence, request.metadata
    )
    return {"status": "success"}


@router.get("/geocode/suggestions", response_model=list[GeocodeResult])
async def get_geocode_suggestions(q: str, country_code: str = "GR") -> list[GeocodeResult]:
    suggestions = await GeocoderService.get_suggestions(q, country_code)
    return suggestions
