from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from packages.domain.models import PendingEvent, Venue

pytestmark = pytest.mark.usefixtures("moderator_auth")


@pytest.mark.asyncio
async def test_update_venue_success(client: AsyncClient, session: Session) -> None:
    venue = Venue(
        name="Old Name",
        country_code="GR",
        city="Athens",
        lat=37.0,
        lng=23.0,
        full_address="Old Address",
        relevance=1.0,
    )
    session.add(venue)
    session.commit()
    session.refresh(venue)

    response = await client.patch(
        f"/api/v1/moderation/venues/{venue.id}", json={"name": "New Name"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_venue_success(client: AsyncClient, session: Session) -> None:
    venue = Venue(
        name="To Delete",
        country_code="GR",
        city="Athens",
        lat=37.0,
        lng=23.0,
        full_address="Address",
        relevance=1.0,
    )
    session.add(venue)
    session.commit()
    session.refresh(venue)

    response = await client.delete(f"/api/v1/moderation/venues/{venue.id}")
    assert response.status_code == 200

    # Verify it's gone
    assert session.get(Venue, venue.id) is None


@pytest.mark.asyncio
async def test_merge_venues_success(client: AsyncClient, session: Session) -> None:
    v1 = Venue(
        name="Source",
        country_code="GR",
        city="Athens",
        lat=37.0,
        lng=23.0,
        full_address="A1",
        relevance=1.0,
    )
    v2 = Venue(
        name="Target",
        country_code="GR",
        city="Athens",
        lat=37.0,
        lng=23.0,
        full_address="A2",
        relevance=1.0,
    )
    session.add(v1)
    session.add(v2)
    session.commit()
    session.refresh(v1)
    session.refresh(v2)

    payload = {"source_venue_id": str(v1.id), "target_venue_id": str(v2.id)}
    response = await client.post("/api/v1/moderation/venues/merge", json=payload)
    assert response.status_code == 200

    # Source should be deleted
    assert session.get(Venue, v1.id) is None


@pytest.mark.asyncio
async def test_batch_update_location_existing(client: AsyncClient, session: Session) -> None:
    pending = PendingEvent(
        title="Event",
        location_name="Target Venue",
        start_time=datetime(2026, 1, 1, 20, 0, 0, tzinfo=UTC),
        country_code="GR",
    )
    session.add(pending)
    session.commit()

    payload = {
        "target_name": "Target Venue",
        "lat": 38.0,
        "lng": 24.0,
        "status": "verified",
        "confidence": 0.95,
        "metadata": {"updated": True},
    }
    response = await client.post("/api/v1/moderation/batch-update-location", json=payload)
    assert response.status_code == 200
