from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from packages.domain.models import Event, EventProvenance, EventStatus, PendingEvent

pytestmark = pytest.mark.usefixtures("moderator_auth")


@pytest.mark.asyncio
async def test_get_pending_events(client: AsyncClient, session: Session) -> None:
    # Add a pending event
    ev = PendingEvent(
        title="Pending 1",
        status="pending",
        start_time=datetime.now(UTC),
        category="Music",
        location_name="Venue A",
    )
    session.add(ev)
    session.commit()

    response = await client.get("/api/v1/moderation/pending-events")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["title"] == "Pending 1"


@pytest.mark.asyncio
async def test_get_published_events(client: AsyncClient, session: Session) -> None:
    # Add a published event (Event table)
    ev = Event(
        title="Live 1",
        start_time=datetime.now(UTC),
        category="Music",
        location_name="Venue B",
        location="POINT(0 0)",
        status=EventStatus.live,
        provenance=EventProvenance.aggregated,
    )
    session.add(ev)
    session.commit()

    response = await client.get("/api/v1/moderation/events")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["title"] == "Live 1"


@pytest.mark.asyncio
async def test_approve_events_batch(client: AsyncClient, session: Session) -> None:
    ev = PendingEvent(title="Batch 1", status="pending", start_time=datetime.now(UTC), category="T")
    session.add(ev)
    session.commit()

    payload = {"event_ids": [str(ev.id)]}
    response = await client.post("/api/v1/moderation/pending-events/approve-batch", json=payload)
    assert response.status_code == 200
    assert response.json()["approved_count"] == 1

    # Verify DB
    session.expire(ev)
    assert ev.status == "published"


@pytest.mark.asyncio
async def test_reject_events_batch(client: AsyncClient, session: Session) -> None:
    ev = PendingEvent(
        title="Reject 1", status="pending", start_time=datetime.now(UTC), category="T"
    )
    session.add(ev)
    session.commit()

    payload = {"event_ids": [str(ev.id)]}
    response = await client.post("/api/v1/moderation/pending-events/reject-batch", json=payload)
    assert response.status_code == 200
    assert response.json()["rejected_count"] == 1

    # Verify DB
    session.refresh(ev)
    assert ev.status == "rejected"
    assert ev.reviewed_at is not None


@pytest.mark.asyncio
async def test_unpublish_event(client: AsyncClient, session: Session) -> None:
    # Create Event and matching PendingEvent
    start = datetime.now(UTC)
    live = Event(
        title="Live",
        start_time=start,
        category="T",
        location="POINT(0 0)",
        status=EventStatus.live,
        provenance=EventProvenance.aggregated,
    )
    pending = PendingEvent(title="Live", start_time=start, category="T", status="published")
    session.add(live)
    session.add(pending)
    session.commit()

    response = await client.post(f"/api/v1/moderation/events/{live.id}/unpublish")
    assert response.status_code == 200

    # Verify live gone, pending status reverted
    assert session.get(Event, live.id) is None
    session.expire(pending)
    assert pending.status == "pending"


@pytest.mark.asyncio
async def test_update_pending_event(client: AsyncClient, session: Session) -> None:
    ev = PendingEvent(title="Old", status="pending", start_time=datetime.now(UTC), category="T")
    session.add(ev)
    session.commit()

    payload = {"title": "New Title"}
    response = await client.patch(f"/api/v1/moderation/pending-events/{ev.id}", json=payload)
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_get_venues(client: AsyncClient, session: Session) -> None:
    from packages.domain.models import Venue

    v = Venue(name="Venue X", country_code="GR", lat=0, lng=0, full_address="A", relevance=1.0)
    session.add(v)
    session.commit()

    response = await client.get("/api/v1/moderation/venues", params={"search_query": "Venue X"})
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_delete_venue(client: AsyncClient, session: Session) -> None:
    from packages.domain.models import Venue

    v = Venue(name="Delete Me", country_code="GR", lat=0, lng=0, full_address="A", relevance=1.0)
    session.add(v)
    session.commit()

    response = await client.delete(f"/api/v1/moderation/venues/{v.id}")
    assert response.status_code == 200
    assert session.get(Venue, v.id) is None
