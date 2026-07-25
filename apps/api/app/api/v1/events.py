from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import Geography
from sqlalchemy import case, func, or_
from sqlmodel import Session, select

from app.db.session import get_db
from packages.domain.models.event import Event, EventCategory, EventStatus, EventVisibility
from packages.domain.models.organizer import Organizer
from packages.domain.schemas.event import EventDiscoveryResponse, EventSearchResponse

router = APIRouter()

# Escape character used for LIKE/ILIKE patterns built from user input, so that
# a literal '%' or '_' in a search query is matched as text rather than being
# interpreted as SQL wildcard syntax.
_LIKE_ESCAPE_CHAR = "\\"


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


# --- Explore v1 event-search helpers (FOMO-172) ------------------------------
#
# Kept as small private functions in this module rather than a separate
# helper file or service layer: this router has no existing service class to
# extend (discovery's query lives directly in the route above), and a single
# new endpoint does not warrant a new search framework.


def _escape_like_value(value: str) -> str:
    """Escape LIKE/ILIKE wildcard characters so user input is matched literally."""
    return (
        value.replace(_LIKE_ESCAPE_CHAR, _LIKE_ESCAPE_CHAR * 2)
        .replace("%", f"{_LIKE_ESCAPE_CHAR}%")
        .replace("_", f"{_LIKE_ESCAPE_CHAR}_")
    )


def _normalize_query(raw: str | None) -> str | None:
    """Strip whitespace, collapse an empty result to None, and reject a
    too-short (but non-empty) normalized query.

    Deliberately not implemented via Query(min_length=2): whitespace must be
    stripped *before* the minimum-length rule is applied, so a value like
    "  a  " is evaluated as "a" (too short) and "   " is evaluated as empty
    (i.e. no query at all), neither of which a raw min_length constraint on
    the unstripped input could express correctly.
    """
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    if len(stripped) < 2:
        raise HTTPException(
            status_code=422,
            detail="q must be at least 2 characters after trimming whitespace",
        )
    return stripped


def _validate_location(
    lat: float | None, lng: float | None, radius_km: float | None
) -> float | None:
    """Validate the lat/lng/radius_km trio and return the effective radius.

    Returns None when no location was supplied (lat and lng both absent).
    """
    if (lat is None) != (lng is None):
        raise HTTPException(status_code=422, detail="lat and lng must be supplied together")
    if lat is None and lng is None:
        if radius_km is not None:
            raise HTTPException(
                status_code=422, detail="radius_km requires both lat and lng"
            )
        return None
    return radius_km if radius_km is not None else 10.0


def _is_naive(value: datetime) -> bool:
    return value.tzinfo is None or value.tzinfo.utcoffset(value) is None


def _validate_date_range(date_from: datetime | None, date_to: datetime | None) -> None:
    for value, name in ((date_from, "date_from"), (date_to, "date_to")):
        if value is not None and _is_naive(value):
            raise HTTPException(status_code=422, detail=f"{name} must be timezone-aware")
    if date_from is not None and date_to is not None and date_to <= date_from:
        raise HTTPException(status_code=422, detail="date_to must be later than date_from")


def _has_search_criterion(
    normalized_q: str | None,
    category: list[EventCategory] | None,
    date_from: datetime | None,
    date_to: datetime | None,
    lat: float | None,
    lng: float | None,
) -> bool:
    """limit/offset/radius_km alone never count as a real search criterion."""
    return bool(
        normalized_q is not None
        or category
        or date_from is not None
        or date_to is not None
        or (lat is not None and lng is not None)
    )


@router.get("/search", response_model=EventSearchResponse)
async def search_events(
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[list[EventCategory] | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_km: Annotated[float | None, Query(gt=0, le=200)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EventSearchResponse:
    """
    Explore v1 intentional event search (FOMO-172).

    Distinct from /discovery: text query, category, date range and optional
    location/radius filters, with pagination. Reuses discovery's visibility
    contract (public_event_filters) and PostGIS ST_DWithin/Geography pattern
    unchanged. See docs/product/explore-v1-event-search-contract.md for the
    full canonical contract this implements.
    """
    normalized_q = _normalize_query(q)
    effective_radius_km = _validate_location(lat, lng, radius_km)
    _validate_date_range(date_from, date_to)

    if not _has_search_criterion(normalized_q, category, date_from, date_to, lat, lng):
        raise HTTPException(
            status_code=422, detail="At least one search criterion is required"
        )

    statement = select(Event)

    # Only join Organizer when text search needs to match organizer names —
    # category/date/location-only searches never need it.
    if normalized_q is not None:
        statement = statement.outerjoin(Organizer, Event.organizer_id == Organizer.id)

    statement = statement.where(*public_event_filters())

    # Explore always excludes events that have already ended — there is no
    # upcoming_only request parameter; this is unconditional in v1.
    statement = statement.where(
        func.coalesce(Event.end_time, Event.start_time) >= datetime.now(UTC)
    )

    match_priority = None
    if normalized_q is not None:
        q_lower = normalized_q.lower()
        escaped_q_lower = _escape_like_value(q_lower)
        contains_pattern = f"%{escaped_q_lower}%"
        prefix_pattern = f"{escaped_q_lower}%"

        title_lower = func.lower(Event.title)
        location_name_lower = func.lower(Event.location_name)
        organizer_name_lower = func.lower(Organizer.display_name)

        statement = statement.where(
            or_(
                title_lower.like(contains_pattern, escape=_LIKE_ESCAPE_CHAR),
                location_name_lower.like(contains_pattern, escape=_LIKE_ESCAPE_CHAR),
                organizer_name_lower.like(contains_pattern, escape=_LIKE_ESCAPE_CHAR),
            )
        )

        # Basic, deterministic match-priority ordering — not a relevance
        # score or ranking algorithm. Lower value sorts first.
        match_priority = case(
            (title_lower == q_lower, 0),
            (title_lower.like(prefix_pattern, escape=_LIKE_ESCAPE_CHAR), 1),
            (title_lower.like(contains_pattern, escape=_LIKE_ESCAPE_CHAR), 2),
            (location_name_lower.like(contains_pattern, escape=_LIKE_ESCAPE_CHAR), 3),
            (organizer_name_lower.like(contains_pattern, escape=_LIKE_ESCAPE_CHAR), 4),
            else_=5,
        )

    if category:
        statement = statement.where(Event.category.in_([c.value for c in category]))

    if date_from is not None:
        statement = statement.where(
            func.coalesce(Event.end_time, Event.start_time) >= date_from
        )
    if date_to is not None:
        statement = statement.where(Event.start_time < date_to)

    distance = None
    if lat is not None and lng is not None:
        point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326).cast(Geography)
        statement = statement.where(
            func.ST_DWithin(Event.location, point, effective_radius_km * 1000)
        )
        distance = func.ST_Distance(Event.location, point)

    order_clauses = []
    if match_priority is not None:
        order_clauses.append(match_priority)
    if distance is not None:
        order_clauses.append(distance)
    order_clauses.append(Event.start_time)
    order_clauses.append(Event.id)
    statement = statement.order_by(*order_clauses)

    # Fetch one extra row to determine has_more without a separate COUNT(*).
    statement = statement.limit(limit + 1).offset(offset)
    rows = list(db.exec(statement).all())
    has_more = len(rows) > limit
    page = rows[:limit]

    return EventSearchResponse(
        results=[EventDiscoveryResponse.model_validate(event) for event in page],
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


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
