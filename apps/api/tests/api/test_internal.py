import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from packages.domain.models import Event, PendingEvent


@pytest.mark.asyncio
async def test_ingest_events_new(client: AsyncClient, session: Session) -> None:
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
                "source_url": "http://example.com/event1",
            }
        ],
        "raw_content": "Raw data for test",
    }

    response = await client.post("/api/v1/ingestion/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["added"] == 1
    assert data["updated"] == 0

    # Verify DB state
    pending = session.exec(select(PendingEvent).where(PendingEvent.title == "Test Event 1")).first()
    assert pending is not None
    assert pending.status == "pending"


@pytest.mark.asyncio
async def test_ingest_events_update(client: AsyncClient, session: Session) -> None:
    """Test updating existing pending events during ingestion."""
    # Detection: where(PendingEvent.title == ev.title, PendingEvent.start_time == ev.start_time)
    start_time = "2026-04-01T20:00:00Z"

    first_payload = {
        "events": [
            {
                "title": "Duplicate Event",
                "lat": None,
                "lng": None,
                "start_time": start_time,
                "end_time": "2026-04-01T23:00:00Z",
                "category": "Old Category",
                "source_url": "http://example.com/old",
            }
        ]
    }

    first_response = await client.post("/api/v1/ingestion/ingest", json=first_payload)
    assert first_response.status_code == 200
    assert first_response.json()["added"] == 1

    second_payload = {
        "events": [
            {
                "title": "Duplicate Event",
                "lat": None,
                "lng": None,
                "start_time": start_time,
                "end_time": "2026-04-02T01:00:00Z",
                "category": "New Category",
                "source_url": "http://example.com/updated",
            }
        ]
    }

    second_response = await client.post("/api/v1/ingestion/ingest", json=second_payload)
    assert second_response.status_code == 200
    data = second_response.json()
    assert data["updated"] == 1

    updated = session.exec(
        select(PendingEvent).where(PendingEvent.title == "Duplicate Event")
    ).first()
    assert updated is not None
    assert updated.category == "New Category"


@pytest.mark.asyncio
async def test_approve_event(client: AsyncClient, session: Session) -> None:
    """Test approving a pending event."""
    pending_id = uuid4()
    pending = PendingEvent(
        id=pending_id,
        title="To Be Approved",
        location="POINT(0 0)",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
        category="Test",
        status="pending",
    )
    session.add(pending)
    session.commit()

    response = await client.post(f"/api/v1/ingestion/approve/{pending_id}")
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
async def test_approve_event_not_found(client: AsyncClient) -> None:
    """Test approving non-existent event."""
    response = await client.post(f"/api/v1/ingestion/approve/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_approve_already_approved(client: AsyncClient, session: Session) -> None:
    """Test approving an already approved event."""
    pending_id = uuid4()
    pending = PendingEvent(
        id=pending_id,
        title="Already Approved",
        location="POINT(0 0)",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
        category="Test",
        status="published",
    )
    session.add(pending)
    session.commit()

    response = await client.post(f"/api/v1/ingestion/approve/{pending_id}")
    assert response.status_code == 400
    assert "already approved" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reject_event(client: AsyncClient, session: Session) -> None:
    """Test rejecting a pending event."""
    pending_id = uuid4()
    pending = PendingEvent(
        id=pending_id,
        title="To Be Rejected",
        location="POINT(0 0)",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC),
        category="Test",
        status="pending",
    )
    session.add(pending)
    session.commit()

    response = await client.delete(f"/api/v1/ingestion/reject/{pending_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Event rejected and deleted"

    # Verify DB state
    rejected = session.get(PendingEvent, pending_id)
    assert rejected is None


@pytest.mark.asyncio
async def test_reject_event_not_found(client: AsyncClient) -> None:
    """Test rejecting non-existent event."""
    response = await client.delete(f"/api/v1/ingestion/reject/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_trigger_scraper(client: AsyncClient) -> None:
    """Test triggering the scraper background task."""
    response = await client.post("/api/v1/ingestion/run-scraper")
    assert response.status_code == 202
    assert "Scraper started in background" in response.json()["message"]


def test_detect_country_from_url() -> None:
    """Test country detection from URL."""
    from packages.domain.utils.url_utils import detect_country_from_url

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
    assert detect_country_from_url("") == "GR"


@pytest.mark.asyncio
async def test_approve_event_with_occurrences(client: AsyncClient, session: Session) -> None:
    """Test approving a pending event that has multiple occurrences in metadata."""
    pending_id = uuid4()
    occ1_start = "2026-05-02T20:00:00"
    occ2_start = "2026-05-03T20:00:00"

    pending = PendingEvent(
        id=pending_id,
        title="Multi-day Event",
        location="POINT(1 1)",
        start_time=datetime(2026, 5, 1, 20, 0, tzinfo=UTC),
        category="Test",
        status="pending",
        event_metadata={"occurrences": [{"start_time": occ1_start}, {"start_time": occ2_start}]},
    )
    session.add(pending)
    session.commit()

    response = await client.post(f"/api/v1/ingestion/approve/{pending_id}")
    assert response.status_code == 200
    assert response.json()["occurrences_created"] == 2

    # Verify events created
    events = session.exec(select(Event).where(Event.title == "Multi-day Event")).all()
    # 1 primary + 2 occurrences = 3 total
    assert len(events) == 3

    primary = next(
        e
        for e in events
        if e.start_time.year == 2026 and e.start_time.month == 5 and e.start_time.day == 1
    )
    assert primary.parent_id == primary.id

    for e in events:
        assert e.parent_id == primary.id


@pytest.mark.asyncio
async def test_cleanup_pending_events(client: AsyncClient, session: Session) -> None:
    """Test cleanup of old published pending events."""
    old_date = datetime.now(UTC) - timedelta(days=40)
    recent_date = datetime.now(UTC) - timedelta(days=10)

    ev1 = PendingEvent(
        title="Old Published",
        status="published",
        start_time=old_date,
        category="T",
        location="POINT(0 0)",
    )
    ev2 = PendingEvent(
        title="Recent Published",
        status="published",
        start_time=recent_date,
        category="T",
        location="POINT(0 0)",
    )
    ev3 = PendingEvent(
        title="Old Pending",
        status="pending",
        start_time=old_date,
        category="T",
        location="POINT(0 0)",
    )

    session.add(ev1)
    session.add(ev2)
    session.add(ev3)
    session.commit()

    response = await client.delete("/api/v1/ingestion/cleanup-pending?days_old=30")
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1

    assert (
        session.exec(select(PendingEvent).where(PendingEvent.title == "Old Published")).first()
        is None
    )
    assert (
        session.exec(select(PendingEvent).where(PendingEvent.title == "Recent Published")).first()
        is not None
    )
    assert (
        session.exec(select(PendingEvent).where(PendingEvent.title == "Old Pending")).first()
        is not None
    )


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task(session: Session) -> None:
    """Test the full scraper background task pipeline."""
    from app.services.harvester.orchestrator import HarvesterOrchestrator

    from packages.domain.schemas.extracted_event import ExtractedEvent

    mock_process = AsyncMock()
    mock_process.returncode = 0
    scraped_data = [
        {
            "source": "schema_org",
            "original_link": "https://example.gr/event1",
            "structured_data": {"name": "Test Event"},
        }
    ]
    mock_process.communicate.return_value = (json.dumps(scraped_data).encode(), b"")

    extracted = ExtractedEvent(
        title="Test Event",
        start_time=datetime(2026, 6, 1, 20, 0, tzinfo=UTC),
        location_name="Venue",
        category="Other",
        event_metadata={},
    )

    mock_response = MagicMock()
    mock_response.status_code = 200

    from app.services.harvester.geocoder import GeocodeResult

    mock_geo = GeocodeResult(
        lat=37.9,
        lng=23.7,
        relevance=1.0,
        full_address="A",
        country_code="GR",
        geocoding_status="verified",
    )

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch(
            "app.services.harvester.cleansing_service.CleansingService.clean_json_ld",
            return_value=extracted,
        ):
            with patch(
                "app.services.harvester.geocoder.GeocoderService.get_coordinates",
                return_value=mock_geo,
            ):
                with patch("httpx.AsyncClient.post", return_value=mock_response):
                    with patch("app.services.harvester.orchestrator.engine", session.get_bind()):
                        with patch("app.core.config.settings.N8N_WEBHOOK_URL", "http://n8n.test"):
                            await HarvesterOrchestrator.run_pipeline(default_country="GR")

    pending = session.exec(select(PendingEvent).where(PendingEvent.title == "Test Event")).first()
    assert pending is not None
    assert pending.country_code == "GR"


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_html_fallback(session: Session) -> None:
    """Test the scraper background task with HTML fallback items."""
    from app.services.harvester.orchestrator import HarvesterOrchestrator

    from packages.domain.schemas.extracted_event import ExtractedEvent

    mock_process = AsyncMock()
    mock_process.returncode = 0
    scraped_data = [
        {
            "source": "llm_fallback",
            "original_link": "https://ticketmaster.de/event/2",
            "raw_text": "Some HTML text",
        }
    ]
    mock_process.communicate.return_value = (json.dumps(scraped_data).encode(), b"")

    extracted = ExtractedEvent(
        title="AI Extracted Event",
        start_time=datetime(2026, 6, 2, 20, 0, tzinfo=UTC),
        location_name="AI Venue",
        category="Tech",
        event_metadata={},
    )

    from app.services.harvester.geocoder import GeocodeResult

    mock_geo = GeocodeResult(
        lat=37.9,
        lng=23.7,
        relevance=1.0,
        full_address="A",
        country_code="GR",
        geocoding_status="verified",
    )

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch(
            "app.services.harvester.cleansing_service.CleansingService.clean_html_fallback",
            return_value=[extracted],
        ):
            with patch(
                "app.services.harvester.geocoder.GeocoderService.get_coordinates",
                return_value=mock_geo,
            ):
                with patch("httpx.AsyncClient.post"):
                    with patch("app.services.harvester.orchestrator.engine", session.get_bind()):
                        await HarvesterOrchestrator.run_pipeline(default_country="GR")

    pending = session.exec(
        select(PendingEvent).where(PendingEvent.title == "AI Extracted Event")
    ).first()
    assert pending is not None
    assert pending.country_code == "DE"


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_timeout() -> None:
    from app.services.harvester.orchestrator import HarvesterOrchestrator

    mock_process = AsyncMock()
    mock_process.communicate.side_effect = TimeoutError()
    mock_process.kill = MagicMock()

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        await HarvesterOrchestrator.run_pipeline()
        assert mock_process.kill.called


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_db_error(session: Session) -> None:
    from app.services.harvester.orchestrator import HarvesterOrchestrator

    from packages.domain.schemas.extracted_event import ExtractedEvent

    mock_process = AsyncMock()
    mock_process.returncode = 0
    scraped_data = [
        {
            "source": "schema_org",
            "original_link": "http://test.gr",
            "structured_data": {"name": "Test"},
        }
    ]
    mock_process.communicate.return_value = (json.dumps(scraped_data).encode(), b"")

    extracted = ExtractedEvent(
        title="Test", start_time=datetime.now(UTC), location_name="V", category="O"
    )

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch(
            "app.services.harvester.cleansing_service.CleansingService.clean_json_ld",
            return_value=extracted,
        ):
            with patch(
                "app.services.harvester.ingestion_service.IngestionService.ingest_events",
                side_effect=Exception("DB FAIL"),
            ):
                await HarvesterOrchestrator.run_pipeline()


@pytest.mark.asyncio
async def test_internal_ingest_logic_junk_filters(session: Session) -> None:
    from app.services.harvester.ingestion_service import IngestionService

    from packages.domain.schemas.extracted_event import ExtractedEvent

    events = [
        ExtractedEvent(title="Junk", category="Junk", start_time=datetime.now(UTC)),
        ExtractedEvent(title="Προσφορές tickets", category="Other", start_time=datetime.now(UTC)),
    ]

    summary = await IngestionService.ingest_events(session, events)
    assert summary.added == 0


@pytest.mark.asyncio
async def test_internal_ingest_logic_venue_match(session: Session) -> None:
    from app.services.harvester.ingestion_service import IngestionService

    from packages.domain.models import Venue
    from packages.domain.schemas.extracted_event import ExtractedEvent

    venue = Venue(
        name="MatchMe", country_code="GR", lat=10.0, lng=20.0, full_address="A", relevance=1.0
    )
    session.add(venue)
    session.commit()

    events = [
        ExtractedEvent(
            title="Event", location_name="MatchMe", start_time=datetime.now(UTC), category="Music"
        )
    ]

    summary = await IngestionService.ingest_events(session, events)
    assert summary.added == 1

    pending = session.exec(select(PendingEvent).where(PendingEvent.title == "Event")).first()
    assert pending is not None
    assert pending.location_name == "MatchMe"
    assert pending.geocoding_status == "verified"


@pytest.mark.asyncio
async def test_internal_ingest_logic_auto_approve(session: Session) -> None:
    from app.services.harvester.ingestion_service import IngestionService

    from packages.domain.schemas.extracted_event import ExtractedEvent

    future_date = datetime.now(UTC).replace(year=datetime.now(UTC).year + 1)
    events = [
        ExtractedEvent(
            title="Auto Event",
            start_time=future_date,
            category="Music",
            ingestion_method="json_ld",
            geocoding_status="verified",
            confidence_score=0.95,
            lat=1.0,
            lng=1.0,
        )
    ]
    summary = await IngestionService.ingest_events(session, events)
    assert summary.added == 1

    pending = session.exec(select(PendingEvent).where(PendingEvent.title == "Auto Event")).first()
    assert pending is not None
    assert pending.status == "published"
