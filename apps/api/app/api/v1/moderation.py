from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.security.rbac import require_moderator
from app.db.session import get_db
from app.schemas.moderation import (
    BatchApproveRequest,
    BatchRejectRequest,
    LocationBatchUpdate,
    OccurrenceCreate,
    PendingEventResponse,
    PendingEventUpdate,
    PlaceMergeRequest,
    PlaceResponse,
    PlaceUpdate,
    VenueMergeRequest,
)
from app.services.harvester.location.geocoder import GeocodeResult, GeocoderService
from app.services.moderation.moderation_service import ModerationService
from app.services.moderation.place_service import PlaceModerationService

router = APIRouter(dependencies=[Depends(require_moderator)])


@router.get("/pending-events", response_model=list[PendingEventResponse])
def get_pending_events(
    session: Annotated[Session, Depends(get_db)],
    location_name: str | None = None,
    geocoding_status: Annotated[list[str] | None, Query()] = None,
    dedupe_status: Annotated[list[str] | None, Query()] = None,
) -> list[PendingEventResponse]:
    service = ModerationService(session)
    events = service.get_pending_events(location_name, geocoding_status, dedupe_status)
    return [PendingEventResponse.model_validate(e) for e in events]


@router.get("/events", response_model=list[PendingEventResponse])
def get_published_events(
    session: Annotated[Session, Depends(get_db)],
    location_name: str | None = None,
) -> list[PendingEventResponse]:
    service = ModerationService(session)
    events = service.get_published_events(location_name)
    return [PendingEventResponse.model_validate(e) for e in events]


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
    return PendingEventResponse.model_validate(updated)


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
    return PendingEventResponse.model_validate(updated)


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
    return PendingEventResponse.model_validate(new_occ)


# --- Canonical /places routes ---


@router.get("/places", response_model=list[PlaceResponse])
def list_places(
    session: Annotated[Session, Depends(get_db)],
    search_query: str | None = None,
    only_unverified: bool = False,
) -> list[PlaceResponse]:
    service = PlaceModerationService(session)
    return service.get_places(search_query, only_unverified)


@router.post("/places/merge")
def merge_places(
    request: PlaceMergeRequest, session: Annotated[Session, Depends(get_db)]
) -> dict[str, str]:
    service = PlaceModerationService(session)
    success = service.merge_places(request.source_place_id, request.target_place_id)
    if not success:
        raise HTTPException(status_code=404, detail="One or both places not found")
    return {"status": "success"}


@router.patch("/places/{place_id}", response_model=PlaceResponse)
def update_place(
    place_id: Annotated[UUID, Any],
    update: PlaceUpdate,
    session: Annotated[Session, Depends(get_db)],
) -> PlaceResponse:
    service = PlaceModerationService(session)
    updated = service.update_place(place_id, **update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Place not found")
    return updated


@router.delete("/places/{place_id}")
def delete_place(
    place_id: Annotated[UUID, Any], session: Annotated[Session, Depends(get_db)]
) -> dict[str, str]:
    service = PlaceModerationService(session)
    success = service.delete_place_and_unlink_events(place_id)
    if not success:
        raise HTTPException(status_code=404, detail="Place not found")
    return {"status": "success"}


# --- Deprecated /venues routes — kept as backward-compatible aliases ---


@router.get("/venues", response_model=list[PlaceResponse], include_in_schema=False)
def get_venues(
    session: Annotated[Session, Depends(get_db)],
    search_query: str | None = None,
    only_unverified: bool = False,
) -> list[PlaceResponse]:
    return list_places(session, search_query, only_unverified)


@router.post("/venues/merge", include_in_schema=False)
def merge_venues(
    request: VenueMergeRequest, session: Annotated[Session, Depends(get_db)]
) -> dict[str, str]:
    service = PlaceModerationService(session)
    success = service.merge_places(request.source_venue_id, request.target_venue_id)
    if not success:
        raise HTTPException(status_code=404, detail="One or both venues not found")
    return {"status": "success"}


@router.patch("/venues/{venue_id}", response_model=PlaceResponse, include_in_schema=False)
def update_venue(
    venue_id: Annotated[UUID, Any],
    update: PlaceUpdate,
    session: Annotated[Session, Depends(get_db)],
) -> PlaceResponse:
    return update_place(venue_id, update, session)


@router.delete("/venues/{venue_id}", include_in_schema=False)
def delete_venue(
    venue_id: Annotated[UUID, Any], session: Annotated[Session, Depends(get_db)]
) -> dict[str, str]:
    return delete_place(venue_id, session)


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
