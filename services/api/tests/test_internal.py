import pytest
import json
from uuid import uuid4
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlmodel import Session, select
from app.models.event import PendingEvent, Event
from app.core.config import settings
from app.utils.datetime_utils import DateTimeHelper

@pytest.mark.asyncio
async def test_ingest_events_new(client: AsyncClient, session: Session):
    """Test ingesting new events."""
    payload = {
        "events": [
            {
                "title": "Test Event 1",
                "lat": 37.7749,
                "lng": -122.4194,
                "start_time": "2026-04-01T20:00:00Z",
                "end_time": "2026-04-01T23:00:00Z",
                "category": "Music",
                "hype_score": 80,
                "source_url": "http://example.com/event1"
            }
        ],
        "raw_content": "Raw data for test"
    }
    
    response = await client.post("/api/v1/internal/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["added"] == 1
    assert data["updated"] == 0
    
    # Verify DB state
    pending = session.exec(select(PendingEvent).where(PendingEvent.title == "Test Event 1")).first()
    assert pending is not None
    assert pending.status == "pending"

@pytest.mark.asyncio
async def test_ingest_events_update(client: AsyncClient, session: Session):
    """Test updating existing pending events during ingestion."""
    first_payload = {
        "events": [
            {
                "title": "Duplicate Event",
                "lat": None,
                "lng": None,
                "start_time": "2026-04-01T20:00:00Z",
                "end_time": "2026-04-01T23:00:00Z",
                "category": "Old Category",
                "source_url": "http://example.com/old"
            }
        ]
    }
    
    first_response = await client.post("/api/v1/internal/ingest", json=first_payload)
    assert first_response.status_code == 200
    assert first_response.json()["added"] == 1
    
    second_payload = {
        "events": [
            {
                "title": "Duplicate Event",
                "lat": None,
                "lng": None,
                "start_time": "2026-04-01T20:00:00Z",
                "end_time": "2026-04-02T01:00:00Z",
                "category": "New Category",
                "source_url": "http://example.com/updated"
            }
        ]
    }
    
    second_response = await client.post("/api/v1/internal/ingest", json=second_payload)
    assert second_response.status_code == 200
    data = second_response.json()
    assert data["added"] == 0
    assert data["updated"] == 1
    
    updated = session.exec(select(PendingEvent).where(PendingEvent.title == "Duplicate Event")).first()
    assert updated is not None
    assert updated.category == "New Category"
    assert updated.source_url == "http://example.com/updated"

@pytest.mark.asyncio
async def test_approve_event(client: AsyncClient, session: Session):
    """Test approving a pending event."""
    pending_id = uuid4()
    pending = PendingEvent(
        id=pending_id,
        title="To Be Approved",
        location="POINT(0 0)",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        category="Test",
        status="pending"
    )
    session.add(pending)
    session.commit()
    
    response = await client.post(f"/api/v1/internal/approve/{pending_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Event approved"
    
    # Verify status changed to published
    session.expire(pending)
    assert pending.status == "published"
    
    # Verify live event created
    live = session.exec(select(Event).where(Event.title == "To Be Approved")).first()
    assert live is not None
    assert live.id != pending_id

@pytest.mark.asyncio
async def test_approve_event_not_found(client: AsyncClient):
    """Test approving non-existent event."""
    response = await client.post(f"/api/v1/internal/approve/{uuid4()}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_approve_already_approved(client: AsyncClient, session: Session):
    """Test approving an already approved event."""
    pending_id = uuid4()
    pending = PendingEvent(
        id=pending_id,
        title="Already Approved",
        location="POINT(0 0)",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        category="Test",
        status="published"
    )
    session.add(pending)
    session.commit()
    
    response = await client.post(f"/api/v1/internal/approve/{pending_id}")
    assert response.status_code == 400
    assert "already approved" in response.json()["detail"]

@pytest.mark.asyncio
async def test_reject_event(client: AsyncClient, session: Session):
    """Test rejecting a pending event."""
    pending_id = uuid4()
    pending = PendingEvent(
        id=pending_id,
        title="To Be Rejected",
        location="POINT(0 0)",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        category="Test",
        status="pending"
    )
    session.add(pending)
    session.commit()
    
    response = await client.delete(f"/api/v1/internal/reject/{pending_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Event rejected and deleted"
    
    # Verify DB state
    rejected = session.get(PendingEvent, pending_id)
    assert rejected is None

@pytest.mark.asyncio
async def test_reject_event_not_found(client: AsyncClient):
    """Test rejecting non-existent event."""
    response = await client.delete(f"/api/v1/internal/reject/{uuid4()}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_trigger_scraper(client: AsyncClient):
    """Test triggering the scraper background task."""
    response = await client.post("/api/v1/internal/run-scraper")
    assert response.status_code == 202
    assert "Scraper started in background" in response.json()["message"]
