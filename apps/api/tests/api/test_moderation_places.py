"""Tests for canonical /places routes (FOMO-101)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from packages.domain.models import Event, PendingEvent, Place

pytestmark = pytest.mark.usefixtures("moderator_auth")


def make_place(**kwargs: object) -> Place:
    defaults = dict(
        country_code="GR",
        lat=37.9838,
        lng=23.7275,
        full_address="Athens, Greece",
        relevance=1.0,
    )
    defaults.update(kwargs)
    return Place(**defaults)


@pytest.mark.asyncio
async def test_list_places(client: AsyncClient, session: Session) -> None:
    p = make_place(name="Place Alpha")
    session.add(p)
    session.commit()

    response = await client.get("/api/v1/moderation/places", params={"search_query": "Place Alpha"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Place Alpha"
    assert "verification_status" in data[0]


@pytest.mark.asyncio
async def test_list_places_only_unverified(client: AsyncClient, session: Session) -> None:
    response = await client.get("/api/v1/moderation/places?only_unverified=true")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_place(client: AsyncClient, session: Session) -> None:
    p = make_place(name="Original Name", city="Athens")
    session.add(p)
    session.commit()
    session.refresh(p)

    response = await client.patch(
        f"/api/v1/moderation/places/{p.id}", json={"name": "Updated Name"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_place_not_found(client: AsyncClient) -> None:
    response = await client.patch(f"/api/v1/moderation/places/{uuid4()}", json={"name": "X"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_place(client: AsyncClient, session: Session) -> None:
    p = make_place(name="To Delete")
    session.add(p)
    session.commit()
    session.refresh(p)

    response = await client.delete(f"/api/v1/moderation/places/{p.id}")
    assert response.status_code == 200
    assert session.get(Place, p.id) is None


@pytest.mark.asyncio
async def test_delete_place_not_found(client: AsyncClient) -> None:
    response = await client.delete(f"/api/v1/moderation/places/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_merge_places(client: AsyncClient, session: Session) -> None:
    src = make_place(name="Source Place")
    tgt = make_place(name="Target Place")
    session.add_all([src, tgt])
    session.commit()
    session.refresh(src)
    session.refresh(tgt)

    payload = {"source_place_id": str(src.id), "target_place_id": str(tgt.id)}
    response = await client.post("/api/v1/moderation/places/merge", json=payload)
    assert response.status_code == 200
    assert session.get(Place, src.id) is None


@pytest.mark.asyncio
async def test_merge_places_not_found(client: AsyncClient) -> None:
    payload = {"source_place_id": str(uuid4()), "target_place_id": str(uuid4())}
    response = await client.post("/api/v1/moderation/places/merge", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deprecated_venues_route_still_works(client: AsyncClient, session: Session) -> None:
    """Verify /venues routes still respond as deprecated aliases."""
    p = make_place(name="Compat Place")
    session.add(p)
    session.commit()

    response = await client.get(
        "/api/v1/moderation/venues", params={"search_query": "Compat Place"}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_deprecated_venues_delete_still_works(client: AsyncClient, session: Session) -> None:
    p = make_place(name="Compat Delete")
    session.add(p)
    session.commit()
    session.refresh(p)

    response = await client.delete(f"/api/v1/moderation/venues/{p.id}")
    assert response.status_code == 200
    assert session.get(Place, p.id) is None


@pytest.mark.asyncio
async def test_manual_place_verification_triggers_reconciliation(
    client: AsyncClient, session: Session
) -> None:
    """FOMO-163: verifying a place's coordinates in the dashboard must make any
    pending event still waiting on that location eligible for auto-approval."""
    place = make_place(name="Newly Verified Hall", city="Athens", verification_status="unverified")
    session.add(place)
    session.commit()
    session.refresh(place)

    pending = PendingEvent(
        title="Waiting On Verification",
        location_name="Newly Verified Hall",
        country_code="GR",
        start_time=datetime.now(UTC) + timedelta(days=30),
        category="Music",
        status="pending",
        geocoding_status="failed",
        ingestion_method="json_ld",
        place_candidate_id=place.id,
    )
    session.add(pending)
    session.commit()

    response = await client.patch(
        f"/api/v1/moderation/places/{place.id}",
        json={"lat": 37.9838, "lng": 23.7275, "verification_status": "manually_verified"},
    )
    assert response.status_code == 200

    session.refresh(pending)
    assert pending.status == "published"
    assert pending.geocoding_status == "verified"
    assert (
        session.exec(select(Event).where(Event.title == "Waiting On Verification")).first()
        is not None
    )


@pytest.mark.asyncio
async def test_deprecated_venues_merge_still_works(client: AsyncClient, session: Session) -> None:
    src = make_place(name="Compat Src")
    tgt = make_place(name="Compat Tgt")
    session.add_all([src, tgt])
    session.commit()
    session.refresh(src)
    session.refresh(tgt)

    payload = {"source_venue_id": str(src.id), "target_venue_id": str(tgt.id)}
    response = await client.post("/api/v1/moderation/venues/merge", json=payload)
    assert response.status_code == 200
    assert session.get(Place, src.id) is None
