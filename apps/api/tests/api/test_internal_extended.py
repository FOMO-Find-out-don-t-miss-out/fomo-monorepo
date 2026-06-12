from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from app.services.harvester.orchestrator import HarvesterOrchestrator
from httpx import AsyncClient
from sqlmodel import Session

pytestmark = pytest.mark.usefixtures("service_auth")


@pytest.mark.asyncio
async def test_run_scraper_registry_source(session: Session) -> None:
    # Mock the scraper output to include a 'registry' source
    mock_scraped_data = [
        {
            "source": "registry",
            "title": "Registry Event",
            "start_time": "2026-07-01T19:00:00Z",
            "location_name": "Registry Venue",
            "original_link": "https://example.com/reg",
        }
    ]

    mock_process = AsyncMock()
    mock_process.returncode = 0
    import json

    mock_process.communicate.return_value = (json.dumps(mock_scraped_data).encode(), b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch(
            "app.services.harvester.location.geocoder.GeocoderService.get_coordinates"
        ) as mock_c:
            from app.services.harvester.location.geocoder import GeocodeResult

            mock_c.return_value = GeocodeResult(
                lat=38.0,
                lng=23.0,
                relevance=1.0,
                full_address="A",
                country_code="GR",
                geocoding_status="verified",
            )
            with patch("app.services.harvester.orchestrator.engine", session.get_bind()):
                await HarvesterOrchestrator.run_pipeline(default_country="GR")

    from sqlmodel import select

    from packages.domain.models import PendingEvent

    statement = select(PendingEvent).where(PendingEvent.title == "Registry Event")
    pending = session.exec(statement).first()
    assert pending is not None
    assert pending.geocoding_status == "verified"


@pytest.mark.asyncio
async def test_trigger_batch_geocode_endpoint(client: AsyncClient, session: Session) -> None:
    # Add an event that needs geocoding
    from packages.domain.models import PendingEvent

    pending = PendingEvent(
        title="Needs Geocode",
        start_time=datetime.now(UTC),
        location_name="Some Place",
        category="Test",
        geocoding_status="failed",
    )
    session.add(pending)
    session.commit()

    # We mock the actual service method to avoid network/Mapbox
    with patch(
        "app.services.harvester.location.geocoder.GeocoderService.batch_geocode_pending_events",
        new_callable=AsyncMock,
    ) as mock_batch:
        mock_batch.return_value = {"updated": 1, "failed": 0, "skipped": 0}
        response = await client.post("/api/v1/ingestion/batch-geocode", params={"batch_size": 10})
        assert response.status_code == 202
        assert "Batch geocoding started" in response.json()["message"]
