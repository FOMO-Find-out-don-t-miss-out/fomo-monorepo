import math
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from packages.domain.models import Event, EventStatus, EventVisibility, Organizer, Place


# Simple spatial distance function for SQLite
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def sqlite_st_dwithin(loc: str, pnt: str, radius_m: float) -> int:
    # Parse "POINT(lng lat)"
    try:
        # Very crude parsing for mock purposes
        # loc and pnt will be something like 'POINT(23.7275 37.9838)'
        l_parts = loc.replace("POINT(", "").replace(")", "").split()
        p_parts = pnt.replace("POINT(", "").replace(")", "").split()

        lng1, lat1 = float(l_parts[0]), float(l_parts[1])
        lng2, lat2 = float(p_parts[0]), float(p_parts[1])

        dist_km = haversine(lat1, lng1, lat2, lng2)
        return 1 if (dist_km * 1000) <= radius_m else 0
    except Exception:
        return 0


def sqlite_st_distance(loc: str, pnt: str) -> float:
    try:
        l_parts = loc.replace("POINT(", "").replace(")", "").split()
        p_parts = pnt.replace("POINT(", "").replace(")", "").split()

        lng1, lat1 = float(l_parts[0]), float(l_parts[1])
        lng2, lat2 = float(p_parts[0]), float(p_parts[1])

        return haversine(lat1, lng1, lat2, lng2) * 1000
    except Exception:
        return 0.0


@pytest.mark.asyncio
async def test_events_discovery_spatial(client: AsyncClient, session: Session) -> None:
    # Register mock spatial functions for SQLite if we are using it
    # This is necessary because conftest.py uses sqlite:// for tests
    conn = session.connection().connection
    try:
        conn.create_function("ST_DWithin", 3, sqlite_st_dwithin)
        conn.create_function("ST_Distance", 2, sqlite_st_distance)
        conn.create_function("ST_SetSRID", 2, lambda x, s: x)
        conn.create_function("ST_MakePoint", 2, lambda x, y: f"POINT({x} {y})")
    except AttributeError:
        # Not a sqlite connection, likely real Postgres for some reason
        pass

    # Seed events
    # Athens: (37.9838, 23.7275)
    # Piraeus: (37.9422, 23.6462) - ~7km from Athens
    # Thessaloniki: (40.6401, 22.9444) - ~300km from Athens

    e1 = Event(
        title="Athens Event",
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 4, 1, 20, 0, tzinfo=UTC),
        category="Music",
        location_name="Athens Center",
        source_url="http://athens.com",
    )
    e2 = Event(
        title="Piraeus Event",
        location="POINT(23.6462 37.9422)",
        start_time=datetime(2026, 4, 1, 21, 0, tzinfo=UTC),
        category="Art",
        location_name="Piraeus Port",
        source_url="http://piraeus.com",
    )
    e3 = Event(
        title="Thessaloniki Event",
        location="POINT(22.9444 40.6401)",
        start_time=datetime(2026, 4, 1, 22, 0, tzinfo=UTC),
        category="Tech",
        location_name="White Tower",
        source_url="http://thessaloniki.com",
    )
    hidden = Event(
        title="Hidden Event",
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 4, 1, 23, 0, tzinfo=UTC),
        category="Music",
        visibility=EventVisibility.hidden,
    )
    restricted = Event(
        title="Restricted Event",
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 4, 2, 20, 0, tzinfo=UTC),
        category="Music",
        visibility=EventVisibility.restricted,
    )
    shadow_hidden = Event(
        title="Shadow Hidden Event",
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 4, 2, 21, 0, tzinfo=UTC),
        category="Music",
        visibility=EventVisibility.shadow_hidden,
    )
    removed = Event(
        title="Removed Event",
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 4, 2, 22, 0, tzinfo=UTC),
        category="Music",
        status=EventStatus.removed,
    )
    under_investigation = Event(
        title="Investigated Event",
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 4, 2, 23, 0, tzinfo=UTC),
        category="Music",
        status=EventStatus.under_investigation,
    )

    session.add_all([e1, e2, e3, hidden, restricted, shadow_hidden, removed, under_investigation])
    session.commit()

    # Discovery from Athens with 10km radius
    # Expect: Athens Event and Piraeus Event
    params: dict[str, Any] = {"lat": 37.9838, "lng": 23.7275, "radius_km": 10.0}
    response = await client.get("/api/v1/events/discovery", params=params)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    titles = [ev["title"] for ev in data]
    assert "Athens Event" in titles
    assert "Piraeus Event" in titles
    assert "Thessaloniki Event" not in titles
    assert "Hidden Event" not in titles
    assert "Restricted Event" not in titles
    assert "Shadow Hidden Event" not in titles
    assert "Removed Event" not in titles
    assert "Investigated Event" not in titles

    # Verify order (Athens Event should be first as distance is 0)
    assert data[0]["title"] == "Athens Event"

    # Verify response schema (Atomic Facts)
    first_event = data[0]
    assert "id" in first_event
    assert "title" in first_event
    assert "startTime" in first_event
    assert "endTime" in first_event
    assert "locationName" in first_event
    assert "lat" in first_event
    assert "lng" in first_event
    assert "sourceUrl" in first_event
    assert "provenance" in first_event
    assert "trust_level" in first_event
    assert "place_id" in first_event
    assert "organizer_id" in first_event

    # Test with larger radius
    params_large: dict[str, Any] = {"lat": 37.9838, "lng": 23.7275, "radius_km": 500.0}
    response_large = await client.get("/api/v1/events/discovery", params=params_large)
    assert response_large.status_code == 200
    assert len(response_large.json()) == 3


@pytest.mark.asyncio
async def test_event_detail_filters_non_public_events(
    client: AsyncClient, session: Session
) -> None:
    public = Event(
        title="Public Detail",
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 4, 1, 20, 0, tzinfo=UTC),
        category="Music",
    )
    hidden = Event(
        title="Hidden Detail",
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 4, 1, 21, 0, tzinfo=UTC),
        category="Music",
        visibility=EventVisibility.hidden,
    )
    removed = Event(
        title="Removed Detail",
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 4, 1, 22, 0, tzinfo=UTC),
        category="Music",
        status=EventStatus.removed,
    )
    session.add_all([public, hidden, removed])
    session.commit()

    public_response = await client.get(f"/api/v1/events/{public.id}")
    assert public_response.status_code == 200
    assert public_response.json()["title"] == "Public Detail"

    hidden_response = await client.get(f"/api/v1/events/{hidden.id}")
    assert hidden_response.status_code == 404

    removed_response = await client.get(f"/api/v1/events/{removed.id}")
    assert removed_response.status_code == 404


@pytest.mark.asyncio
async def test_public_event_response_includes_place_and_organizer_ids(
    client: AsyncClient, session: Session
) -> None:
    place = Place(
        name="Canonical Place",
        country_code="GR",
        lat=37.9838,
        lng=23.7275,
        full_address="Athens",
        relevance=1.0,
        location="POINT(23.7275 37.9838)",
    )
    organizer = Organizer(display_name="Organizer")
    session.add_all([place, organizer])
    session.commit()

    event = Event(
        title="Linked Event",
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 4, 1, 20, 0, tzinfo=UTC),
        category="Music",
        place_id=place.id,
        organizer_id=organizer.id,
    )
    session.add(event)
    session.commit()

    response = await client.get(f"/api/v1/events/{event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["provenance"] == "aggregated"
    assert data["trust_level"] == "unverified"
    assert data["place_id"] == str(place.id)
    assert data["organizer_id"] == str(organizer.id)


@pytest.mark.asyncio
async def test_events_discovery_invalid_coords(client: AsyncClient) -> None:
    # Test invalid latitude
    response = await client.get("/api/v1/events/discovery", params={"lat": 95.0, "lng": 23.7275})
    assert response.status_code == 422

    # Test invalid longitude
    response = await client.get("/api/v1/events/discovery", params={"lat": 37.9838, "lng": 200.0})
    assert response.status_code == 422
