from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2 import Geography
from sqlalchemy import func
from sqlmodel import Session, select

from app.db.session import get_db
from packages.domain.models.event import Event
from packages.domain.schemas.event import EventDiscoveryResponse

router = APIRouter()


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
        .order_by(func.ST_Distance(Event.location, point))
    )

    results = db.exec(statement).all()
    return list(results)
