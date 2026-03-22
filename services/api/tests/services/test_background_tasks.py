import pytest
import json
import asyncio
import httpx
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch
from sqlmodel import Session, select
from app.api.v1.internal import run_scraper_and_ingest_task
from app.models.event import PendingEvent
from app.db.session import engine
from app.services.harvester.cleanser import ExtractedEvent

@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_success(session, monkeypatch, respx_mock):
    """Test successful scraper run and ingestion."""
    # 1. Mock subprocess
    mock_stdout = json.dumps([
        {
            "source": "schema_org",
            "original_link": "http://example.com/event",
            "structured_data": {
                "name": "Scraped Event",
                "startDate": "2026-05-01T10:00:00Z",
                "endDate": "2026-05-01T12:00:00Z",
                "location": {
                    "geo": {"latitude": "34.0522", "longitude": "-118.2437"}
                }
            }
        },
        {
            "source": "schema_org",
            "original_link": "http://example.com/event-list",
            "structured_data": {
                "name": ["Event List Name"], # Test list handling
                "startDate": ["2026-05-01T10:00:00Z"],
                "location": {
                    "geo": {"latitude": ["34.0522"], "longitude": ["-118.2437"]}
                }
            }
        },
        {
            "source": "llm_fallback",
            "original_link": "http://example.com/fallback",
            "raw_text": "Fallback content"
        }
    ]).encode()
    
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (mock_stdout, b"")
    mock_process.returncode = 0
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        # 2. Mock n8n webhook
        from app.core.config import settings
        respx_mock.post(settings.N8N_WEBHOOK_URL).mock(return_value=httpx.Response(200))
        
        # 3. Mock CleansingService to avoid requiring real Gemini client
        async def mock_clean_side_effect(data_or_text, country_hint=None):
            # Create a unique title based on input to avoid DB updates instead of additions
            title = f"Mocked Event {hash(str(data_or_text))}"
            return ExtractedEvent(
                title=title,
                start_time=datetime(2026, 5, 1, tzinfo=timezone.utc),
                lat=34.0522,
                lng=-118.2437,
                category="Music",
                event_metadata={}
            )
        
        async def mock_html_side_effect(text, country_hint=None):
            ev = await mock_clean_side_effect(text, country_hint)
            return [ev]
        
        with patch("app.api.v1.internal.CleansingService.clean_json_ld", side_effect=mock_clean_side_effect):
            with patch("app.api.v1.internal.CleansingService.clean_html_fallback", side_effect=mock_html_side_effect):
                # 4. Mock engine to use test session
                with patch("app.api.v1.internal.engine", session.bind):
                     await run_scraper_and_ingest_task()
        
    # Verify results
    pending_events = session.exec(select(PendingEvent)).all()
    assert len(pending_events) == 3

@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_subprocess_fail(monkeypatch):
    """Test scraper failure at subprocess level."""
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"", b"Error message")
    mock_process.returncode = 1
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        await run_scraper_and_ingest_task()

@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_json_fail(monkeypatch):
    """Test scraper failure with invalid JSON."""
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"invalid json", b"")
    mock_process.returncode = 0
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        await run_scraper_and_ingest_task()

@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_timeout(monkeypatch):
    """Test scraper timeout."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.side_effect = asyncio.TimeoutError()
        mock_process.kill = MagicMock() # Non-async kill
        mock_exec.return_value = mock_process
        
        await run_scraper_and_ingest_task()
        assert mock_process.kill.called

@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_webhook_conn_error(session, respx_mock):
    """Test ingestion success even if webhook has connection error."""
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"[]", b"")
    mock_process.returncode = 0
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        from app.core.config import settings
        respx_mock.post(settings.N8N_WEBHOOK_URL).mock(side_effect=httpx.ConnectError("Connection failed"))
        
        await run_scraper_and_ingest_task()

@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_db_fail(session, monkeypatch):
    """Test ingestion failure at database level."""
    mock_stdout = json.dumps([
        {
            "source": "schema_org",
            "original_link": "http://example.com/event",
            "structured_data": {"name": "DB Fail Event"}
        }
    ]).encode()
    
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (mock_stdout, b"")
    mock_process.returncode = 0
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        # Mock internal_ingest_logic to fail
        with patch("app.api.v1.internal.internal_ingest_logic", side_effect=Exception("DB Error")):
             await run_scraper_and_ingest_task()

@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_webhook_general_fail(session, respx_mock):
    """Test ingestion success even if webhook has a general error."""
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"[]", b"")
    mock_process.returncode = 0
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        from app.core.config import settings
        respx_mock.post(settings.N8N_WEBHOOK_URL).mock(side_effect=Exception("General Error"))
        
        await run_scraper_and_ingest_task()
