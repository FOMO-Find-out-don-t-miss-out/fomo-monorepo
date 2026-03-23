import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlmodel import Session
from app.models.event import PendingEvent, Event

@pytest.mark.asyncio
async def test_get_published_events_endpoint(client: AsyncClient, session: Session):
    e = Event(title="Published", location_name="V")
    session.add(e)
    session.commit()
    
    response = await client.get("/api/v1/moderation/events")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Published"

@pytest.mark.asyncio
async def test_unpublish_event_endpoint(client: AsyncClient, session: Session):
    e = Event(title="To Unpublish", location_name="V")
    session.add(e)
    session.commit()
    
    response = await client.post(f"/api/v1/moderation/events/{e.id}/unpublish")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_unpublish_event_not_found_endpoint(client: AsyncClient):
    response = await client.post(f"/api/v1/moderation/events/{uuid4()}/unpublish")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_published_event_endpoint(client: AsyncClient, session: Session):
    e = Event(title="Old", location_name="V")
    session.add(e)
    session.commit()
    
    response = await client.patch(
        f"/api/v1/moderation/events/{e.id}",
        json={"title": "New"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "New"

@pytest.mark.asyncio
async def test_update_pending_event_endpoint(client: AsyncClient, session: Session):
    p = PendingEvent(title="Old P", status="pending")
    session.add(p)
    session.commit()
    
    response = await client.patch(
        f"/api/v1/moderation/pending-events/{p.id}",
        json={"title": "New P"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "New P"

@pytest.mark.asyncio
async def test_batch_update_location_endpoint(client: AsyncClient, session: Session):
    response = await client.post(
        "/api/v1/moderation/batch-update-location",
        json={
            "target_name": "Some Venue",
            "lat": 1.0,
            "lng": 2.0,
            "status": "verified",
            "confidence": 1.0,
            "metadata": {}
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
