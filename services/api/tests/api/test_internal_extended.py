import pytest
from unittest.mock import patch, MagicMock
from app.api.v1.internal import run_scraper_and_ingest_task, trigger_batch_geocode
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_run_scraper_registry_source(session):
    # Mock the scraper output to include a 'registry' source
    mock_scraped_data = [
        {
            "source": "registry",
            "title": "Registry Event",
            "start_time": "2026-01-01T10:00:00Z",
            "location_name": "Venue X",
            "original_link": "https://test.gr"
        }
    ]
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = MagicMock()
        import asyncio
        fut = asyncio.Future()
        fut.set_result((str(mock_scraped_data).replace("'", '"').encode(), b""))
        mock_process.communicate.return_value = fut
        mock_process.returncode = 0
        mock_exec.return_value = mock_process
        
        with patch("app.services.harvester.geocoder.GeocoderService.get_coordinates") as mock_geo:
            mock_geo.return_value = MagicMock(lat=1.0, lng=2.0, relevance=1.0, geocoding_status="verified", geocoding_metadata={})
            
            await run_scraper_and_ingest_task("GR")
            
            # Use a fresh session to check results
            from app.db.session import Session, engine
            from sqlmodel import select
            with Session(engine) as check_session:
                from app.models.event import PendingEvent
                ev = check_session.exec(select(PendingEvent).where(PendingEvent.title == "Registry Event")).first()
                assert ev is not None
                assert ev.source_url == "https://test.gr"

@pytest.mark.asyncio
async def test_run_scraper_error_handling():
    # Test error in processing one item doesn't crash the loop
    mock_scraped_data = [
        {"source": "schema_org", "structured_data": {}}, # Will likely fail or be skipped
        {"source": "unknown"} # Should be skipped
    ]
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = MagicMock()
        import asyncio
        fut = asyncio.Future()
        fut.set_result((str(mock_scraped_data).replace("'", '"').encode(), b""))
        mock_process.communicate.return_value = fut
        mock_process.returncode = 0
        mock_exec.return_value = mock_process
        
        # Should not raise exception
        await run_scraper_and_ingest_task("GR")

@pytest.mark.asyncio
async def test_trigger_batch_geocode_endpoint(client: AsyncClient, session):
    # Add an event that needs geocoding to avoid empty loop issues or potential errors
    from app.models.event import PendingEvent
    p = PendingEvent(title="Needs Geo", location_name="Athens", geocoding_status="failed", status="pending")
    session.add(p)
    session.commit()

    # This covers lines 421-426 in internal.py
    response = await client.post("/api/v1/internal/batch-geocode?batch_size=10")
    assert response.status_code == 202
    assert response.json()["message"] == "Batch geocoding started in background"
