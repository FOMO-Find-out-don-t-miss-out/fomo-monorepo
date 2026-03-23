import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlmodel import Session
from app.models.event import PendingEvent
from app.models.venue import Venue

@pytest.mark.asyncio
async def test_get_pending_events(client: AsyncClient, session: Session):
    p = PendingEvent(title="Test P", status="pending", location_name="V")
    session.add(p)
    session.commit()
    
    response = await client.get("/api/v1/moderation/pending-events")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test P"

@pytest.mark.asyncio
async def test_approve_event_endpoint(client: AsyncClient, session: Session):
    p = PendingEvent(title="To Approve", status="pending")
    session.add(p)
    session.commit()
    
    response = await client.post(f"/api/v1/moderation/pending-events/{p.id}/approve")
    assert response.status_code == 200
    assert response.json()["approved_count"] == 1
    
    session.refresh(p)
    assert p.status == "published"

@pytest.mark.asyncio
async def test_approve_batch_endpoint(client: AsyncClient, session: Session):
    p1 = PendingEvent(title="P1", status="pending")
    p2 = PendingEvent(title="P2", status="pending")
    session.add_all([p1, p2])
    session.commit()
    
    response = await client.post(
        "/api/v1/moderation/pending-events/approve-batch",
        json={"event_ids": [str(p1.id), str(p2.id)]}
    )
    assert response.status_code == 200
    assert response.json()["approved_count"] == 2

@pytest.mark.asyncio
async def test_update_venue_endpoint(client: AsyncClient, session: Session):
    v = Venue(name="V", city="C", country_code="GR", lat=1.0, lng=1.0, full_address="A", relevance=1.0)
    session.add(v)
    session.commit()
    
    response = await client.patch(
        f"/api/v1/moderation/venues/{v.id}",
        json={"name": "Updated V"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated V"

@pytest.mark.asyncio
async def test_merge_venues_endpoint(client: AsyncClient, session: Session):
    v1 = Venue(name="S", city="C", country_code="GR", lat=1.0, lng=1.0, full_address="A", relevance=1.0)
    v2 = Venue(name="T", city="C", country_code="GR", lat=2.0, lng=2.0, full_address="A", relevance=1.0)
    session.add_all([v1, v2])
    session.commit()
    
    response = await client.post(
        "/api/v1/moderation/venues/merge",
        json={"source_venue_id": str(v1.id), "target_venue_id": str(v2.id)}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_get_pending_events_filtered(client: AsyncClient, session: Session):
    p1 = PendingEvent(title="P1", status="pending", location_name="V1", geocoding_status="verified")
    p2 = PendingEvent(title="P2", status="pending", location_name="V2", geocoding_status="failed")
    session.add_all([p1, p2])
    session.commit()
    
    # Filter by location
    resp = await client.get("/api/v1/moderation/pending-events?location_name=V1")
    assert len(resp.json()) == 1
    
    # Filter by status
    resp = await client.get("/api/v1/moderation/pending-events?geocoding_status=failed")
    assert len(resp.json()) == 1

@pytest.mark.asyncio
async def test_reject_event_endpoint(client: AsyncClient, session: Session):
    p = PendingEvent(title="To Reject", status="pending")
    session.add(p)
    session.commit()
    
    response = await client.post(f"/api/v1/moderation/pending-events/{p.id}/reject")
    assert response.status_code == 200
    assert response.json()["rejected_count"] == 1
    assert session.get(PendingEvent, p.id) is None

@pytest.mark.asyncio
async def test_reject_event_not_found(client: AsyncClient):
    response = await client.post(f"/api/v1/moderation/pending-events/{uuid4()}/reject")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_add_occurrence_endpoint(client: AsyncClient, session: Session):
    p = PendingEvent(title="Orig", status="pending")
    session.add(p)
    session.commit()
    
    response = await client.post(
        f"/api/v1/moderation/pending-events/{p.id}/occurrences",
        json={"start_time": "2026-05-01T10:00:00"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Orig"

@pytest.mark.asyncio
async def test_get_venues_filtered(client: AsyncClient, session: Session):
    v1 = Venue(name="V1", city="C1", country_code="GR", lat=1, lng=1, full_address="A", relevance=1, is_manually_verified=True)
    v2 = Venue(name="V2", city="C2", country_code="GR", lat=1, lng=1, full_address="A", relevance=1, is_manually_verified=False)
    session.add_all([v1, v2])
    session.commit()
    
    resp = await client.get("/api/v1/moderation/venues?only_unverified=true")
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "V2"

@pytest.mark.asyncio
async def test_delete_venue_endpoint(client: AsyncClient, session: Session):
    v = Venue(name="V", city="C", country_code="GR", lat=1, lng=1, full_address="A", relevance=1)
    session.add(v)
    session.commit()
    
    resp = await client.delete(f"/api/v1/moderation/venues/{v.id}")
    assert resp.status_code == 200
    assert session.get(Venue, v.id) is None

@pytest.mark.asyncio
async def test_update_venue_collision_endpoint(client: AsyncClient, session: Session):
    v1 = Venue(name="V1", city="Athens", country_code="GR", lat=1, lng=1, full_address="A", relevance=1)
    v2 = Venue(name="V2", city="Athens", country_code="GR", lat=1, lng=1, full_address="A", relevance=1)
    session.add_all([v1, v2])
    session.commit()
    
    # Try to rename V1 to V2
    resp = await client.patch(f"/api/v1/moderation/venues/{v1.id}", json={"name": "V2"})
    assert resp.status_code == 404 # Because update_venue_record returns None on collision
