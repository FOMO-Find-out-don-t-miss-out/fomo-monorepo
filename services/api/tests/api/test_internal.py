import pytest
import json
import asyncio
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch
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

def test_detect_country_from_url():
    """Test country detection from URL."""
    from app.api.v1.internal import detect_country_from_url
    assert detect_country_from_url("https://www.more.com/gr/events") == "GR"
    assert detect_country_from_url("https://ticketmaster.de/event/1") == "DE"
    assert detect_country_from_url("https://fnacspectacles.fr/event/1") == "FR"
    assert detect_country_from_url("https://ticketone.it/event/1") == "IT"
    assert detect_country_from_url("https://ticketmaster.es/event/1") == "ES"
    assert detect_country_from_url("https://ticketmaster.nl/event/1") == "NL"
    assert detect_country_from_url("https://oeticket.at/event/1") == "AT"
    assert detect_country_from_url("https://ticketmaster.be/event/1") == "BE"
    assert detect_country_from_url("https://soldoutticketbox.com.cy/event/1") == "CY"
    assert detect_country_from_url("https://www.ticketmaster.co.uk/event/1") == "UK"
    assert detect_country_from_url("https://uk.reuters.com/news") == "UK"
    assert detect_country_from_url("https://example.com") == "GR"
    assert detect_country_from_url(None) == "GR"

@pytest.mark.asyncio
async def test_approve_event_with_occurrences(client: AsyncClient, session: Session):
    """Test approving a pending event that has multiple occurrences in metadata."""
    pending_id = uuid4()
    occ1_start = "2026-05-02T20:00:00"
    occ2_start = "2026-05-03T20:00:00"
    
    pending = PendingEvent(
        id=pending_id,
        title="Multi-day Event",
        location="POINT(1 1)",
        start_time=datetime(2026, 5, 1, 20, 0, tzinfo=timezone.utc),
        category="Test",
        status="pending",
        event_metadata={
            "occurrences": [
                {"start_time": occ1_start},
                {"start_time": occ2_start}
            ]
        }
    )
    session.add(pending)
    session.commit()
    
    response = await client.post(f"/api/v1/internal/approve/{pending_id}")
    assert response.status_code == 200
    assert response.json()["occurrences_created"] == 2
    
    # Verify events created
    events = session.exec(select(Event).where(Event.title == "Multi-day Event")).all()
    # 1 primary + 2 occurrences = 3 total
    assert len(events) == 3
    
    # Check parent_id link (there should be only one event with 2026-05-01 start time)
    # Filter by date to avoid exact microsecond/tz issues
    primary = [e for e in events if e.start_time.year == 2026 and e.start_time.month == 5 and e.start_time.day == 1][0]
    assert primary.parent_id == primary.id
    
    for e in events:
        assert e.parent_id == primary.id

@pytest.mark.asyncio
async def test_cleanup_pending_events(client: AsyncClient, session: Session):
    """Test cleanup of old published pending events."""
    from datetime import timedelta
    old_date = datetime.now(timezone.utc) - timedelta(days=40)
    recent_date = datetime.now(timezone.utc) - timedelta(days=10)
    
    # 1. Old published event (should be deleted)
    ev1 = PendingEvent(title="Old Published", status="published", start_time=old_date, category="T", location="POINT(0 0)")
    # 2. Recent published event (should stay)
    ev2 = PendingEvent(title="Recent Published", status="published", start_time=recent_date, category="T", location="POINT(0 0)")
    # 3. Old pending event (should stay)
    ev3 = PendingEvent(title="Old Pending", status="pending", start_time=old_date, category="T", location="POINT(0 0)")
    
    session.add(ev1)
    session.add(ev2)
    session.add(ev3)
    session.commit()
    
    response = await client.delete("/api/v1/internal/cleanup-pending?days_old=30")
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1
    
    # Verify DB
    assert session.exec(select(PendingEvent).where(PendingEvent.title == "Old Published")).first() is None
    assert session.exec(select(PendingEvent).where(PendingEvent.title == "Recent Published")).first() is not None
    assert session.exec(select(PendingEvent).where(PendingEvent.title == "Old Pending")).first() is not None

@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task(session: Session):
    """Test the full scraper background task pipeline."""
    from app.api.v1.internal import run_scraper_and_ingest_task
    from app.services.harvester.cleanser import ExtractedEvent
    
    # 1. Mock Subprocess
    mock_process = AsyncMock()
    mock_process.returncode = 0
    scraped_data = [
        {
            "source": "json-ld",
            "original_link": "https://example.gr/event1",
            "structured_data": {"name": "Test Event"}
        }
    ]
    mock_process.communicate.return_value = (json.dumps(scraped_data).encode(), b"")
    
    # 2. Mock Cleanser
    extracted = ExtractedEvent(
        title="Test Event",
        start_time=datetime(2026, 6, 1, 20, 0, tzinfo=timezone.utc),
        location_name="Venue",
        category="Other",
        event_metadata={}
    )
    
    # 3. Mock httpx for n8n notification
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch("app.services.harvester.cleanser.CleansingService.clean_json_ld", return_value=extracted):
            with patch("httpx.AsyncClient.post", return_value=mock_response):
                with patch("app.api.v1.internal.engine", session.get_bind()):
                    # Ensure settings.N8N_WEBHOOK_URL is set for the test
                    with patch("app.core.config.settings.N8N_WEBHOOK_URL", "http://n8n.test"):
                        await run_scraper_and_ingest_task(default_country="GR")
    
    # Verify DB state
    pending = session.exec(select(PendingEvent).where(PendingEvent.title == "Test Event")).first()
    assert pending is not None
    assert pending.country_code == "GR"

@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_html_fallback(session: Session):
    """Test the scraper background task with HTML fallback items."""
    from app.api.v1.internal import run_scraper_and_ingest_task
    from app.services.harvester.cleanser import ExtractedEvent
    
    mock_process = AsyncMock()
    mock_process.returncode = 0
    scraped_data = [
        {
            "source": "html-fallback",
            "original_link": "https://ticketmaster.de/event/2",
            "raw_text": "Some HTML text"
        }
    ]
    mock_process.communicate.return_value = (json.dumps(scraped_data).encode(), b"")
    
    extracted = ExtractedEvent(
        title="AI Extracted Event",
        start_time=datetime(2026, 6, 2, 20, 0, tzinfo=timezone.utc),
        location_name="AI Venue",
        category="Tech",
        event_metadata={}
    )
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch("app.services.harvester.cleanser.CleansingService.clean_html_fallback", return_value=[extracted]):
            with patch("httpx.AsyncClient.post") as mock_post:
                with patch("app.api.v1.internal.engine", session.get_bind()):
                    await run_scraper_and_ingest_task(default_country="GR")
    
    # Verify DB state
    pending = session.exec(select(PendingEvent).where(PendingEvent.title == "AI Extracted Event")).first()
    assert pending is not None
    assert pending.country_code == "DE" # Detected from URL

@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_timeout():
    from app.api.v1.internal import run_scraper_and_ingest_task
    mock_process = AsyncMock()
    mock_process.communicate.side_effect = asyncio.TimeoutError()
    mock_process.kill = MagicMock()
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        await run_scraper_and_ingest_task()
        assert mock_process.kill.called

@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_db_error(session: Session):
    from app.api.v1.internal import run_scraper_and_ingest_task
    from app.services.harvester.cleanser import ExtractedEvent
    
    mock_process = AsyncMock()
    mock_process.returncode = 0
    scraped_data = [{"source": "json-ld", "original_link": "http://test.gr", "structured_data": {"name": "Test"}}]
    mock_process.communicate.return_value = (json.dumps(scraped_data).encode(), b"")
    
    extracted = ExtractedEvent(title="Test", start_time=datetime.now(timezone.utc), location_name="V", category="O")
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch("app.services.harvester.cleanser.CleansingService.clean_json_ld", return_value=extracted):
            with patch("app.api.v1.internal.internal_ingest_logic", side_effect=Exception("DB FAIL")):
                # This should hit the logger.error in the ingestion block
                await run_scraper_and_ingest_task()
