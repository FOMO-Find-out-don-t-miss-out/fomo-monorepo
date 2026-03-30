import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from app.services.harvester.orchestrator import HarvesterOrchestrator
from sqlmodel import Session

from packages.domain.utils.url_utils import get_domain_from_url


def test_get_domain_from_url_coverage() -> None:
    """Test get_domain_from_url with various edge cases for coverage."""
    # Case: None or empty
    assert get_domain_from_url(None) == "unknown"
    assert get_domain_from_url("") == "unknown"

    # Case: starts with www.
    assert get_domain_from_url("https://www.google.com") == "google.com"

    # Case: no www.
    assert get_domain_from_url("https://google.com") == "google.com"

    # Case: empty netloc
    assert get_domain_from_url("mailto:someone@example.com") == "unknown"

    # Case: Exception (though urlparse rarely raises, we can mock it)
    with patch("packages.domain.utils.url_utils.urlparse", side_effect=Exception("parse fail")):
        assert get_domain_from_url("http://test.com") == "unknown"


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_no_script() -> None:
    """Test run_scraper_and_ingest_task when script does not exist."""
    with patch("pathlib.Path.exists", return_value=False):
        await HarvesterOrchestrator.run_pipeline()
        # Should return early without error


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_scraper_error() -> None:
    """Test run_scraper_and_ingest_task when scraper returns non-zero code."""
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate.return_value = (b"", b"Error message")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        await HarvesterOrchestrator.run_pipeline()


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_json_error() -> None:
    """Test run_scraper_and_ingest_task when scraper returns invalid JSON."""
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"invalid json", b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        await HarvesterOrchestrator.run_pipeline()


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_various_items(session: Session) -> None:
    """Test run_scraper_and_ingest_task with various item cases."""
    from packages.domain.schemas.extracted_event import ExtractedEvent

    mock_process = AsyncMock()
    mock_process.returncode = 0
    scraped_data = [
        # Case: schema_org returning a list
        {
            "source": "schema_org",
            "original_link": "https://www.test.com/list",
            "structured_data": [{"name": "Event 1"}, {"name": "Event 2"}],
        },
        # Case: Exception during processing
        {
            "source": "registry",
            "original_link": "invalid-url",
            "title": "Fail Event",
        },
    ]
    mock_process.communicate.return_value = (json.dumps(scraped_data).encode(), b"")

    extracted_list = [
        ExtractedEvent(
            title="Event 1", start_time=datetime.now(UTC), location_name="V", category="O"
        ),
        ExtractedEvent(
            title="Event 2", start_time=datetime.now(UTC), location_name="V", category="O"
        ),
    ]

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch(
            "app.services.harvester.cleansing_service.CleansingService.clean_json_ld",
            return_value=extracted_list,
        ):
            # Trigger exception in detect_country_from_url or similar by using a bad URL
            # but wait, it has a try/except in the loop
            with patch(
                "app.services.harvester.orchestrator.detect_country_from_url",
                side_effect=Exception("fail"),
            ):
                with patch("app.services.harvester.orchestrator.engine", session.get_bind()):
                    await HarvesterOrchestrator.run_pipeline()


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_n8n_error(session: Session) -> None:
    """Test run_scraper_and_ingest_task when n8n notification fails."""

    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"[]", b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch("app.core.config.settings.N8N_WEBHOOK_URL", "http://n8n.test"):
            with patch("httpx.AsyncClient.post", side_effect=Exception("n8n fail")):
                await HarvesterOrchestrator.run_pipeline()
