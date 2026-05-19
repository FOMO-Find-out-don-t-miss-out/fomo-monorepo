from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import Geography
from sqlalchemy import func
from sqlmodel import Session, select

from app.db.session import get_db
from packages.domain.models.event import Event, EventStatus, EventVisibility
from packages.domain.schemas.event import EventDiscoveryResponse

router = APIRouter()


def public_event_filters() -> tuple[object, ...]:
    return (
        Event.status == EventStatus.live,
        Event.visibility == EventVisibility.public,
        Event.removed_at.is_(None),
    )


@router.get("/discovery", response_model=list[EventDiscoveryResponse])
async def get_events_discovery(
    db: Annotated[Session, Depends(get_db)],
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10.0, gt=0),
) -> list[Event]:
    """
    Find events within a certain radius from a given location.
    Returns atomic facts for mobile client consumption.
    """
    # Create point geography for the input coordinates
    # Note: ST_MakePoint takes (lng, lat)
    point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326).cast(Geography)

    # Use ST_DWithin for spatial filtering (radius in meters)
    statement = (
        select(Event)
        .where(func.ST_DWithin(Event.location, point, radius_km * 1000))
        .where(*public_event_filters())
        .order_by(func.ST_Distance(Event.location, point))
    )

    results = db.exec(statement).all()
    return list(results)


@router.get("/{event_id}", response_model=EventDiscoveryResponse)
async def get_event_detail(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Event:
    statement = select(Event).where(Event.id == event_id).where(*public_event_filters())
    event = db.exec(statement).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
