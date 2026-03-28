import json
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.api.v1.internal import run_scraper_and_ingest_task
from app.models.event import PendingEvent
from sqlmodel import Session, select


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_success(
    session: Session, monkeypatch: pytest.MonkeyPatch, respx_mock: object
) -> None:
    """Test successful scraper run and ingestion."""
    from app.services.harvester.cleanser import ExtractedEvent

    # 1. Mock subprocess
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_stdout = json.dumps(
        [
            {
                "source": "schema_org",
                "original_link": "http://test.gr",
                "structured_data": {"name": "Subprocess Event"},
            }
        ]
    )
    mock_process.communicate.return_value = (mock_stdout.encode(), b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        # 2. Mock Geocoder
        with patch(
            "app.services.harvester.geocoder.GeocoderService.get_coordinates",
            new_callable=AsyncMock,
        ):
            # 3. Mock CleansingService
            async def mock_clean_side_effect(
                data_or_text: object, country_hint: str | None = None, **kwargs: Any
            ) -> object:
                title = f"Mocked Event {hash(str(data_or_text))}"
                return ExtractedEvent(
                    title=title,
                    start_time=datetime.now(UTC),
                    location_name="Mock Venue",
                    category="Other",
                    event_metadata={},
                    source_provider=kwargs.get("source_domain", "unknown"),
                    ingestion_method="json_ld" if "source_domain" in kwargs else "unknown",
                )

            async def mock_html_side_effect(
                text: str, country_hint: str | None = None, **kwargs: Any
            ) -> list[object]:
                ev = await mock_clean_side_effect(text, country_hint, **kwargs)
                if isinstance(ev, ExtractedEvent):
                    ev.ingestion_method = "html_fallback"
                return [ev]

            with patch(
                "app.services.harvester.cleanser.CleansingService.clean_json_ld",
                side_effect=mock_clean_side_effect,
            ):
                with patch(
                    "app.services.harvester.cleanser.CleansingService.clean_html_fallback",
                    side_effect=mock_html_side_effect,
                ):
                    # 4. Mock Engine
                    with patch("app.api.v1.internal.engine", session.get_bind()):
                        await run_scraper_and_ingest_task(default_country="GR")

    all_pending = session.exec(select(PendingEvent)).all()
    assert len(all_pending) > 0


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_subprocess_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test scraper failure at subprocess level."""
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate.return_value = (b"", b"Error log")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        await run_scraper_and_ingest_task()


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_json_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test scraper failure with invalid JSON."""
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"invalid json", b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        await run_scraper_and_ingest_task()


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test scraper timeout."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.side_effect = TimeoutError()
        mock_process.kill = MagicMock()
        mock_exec.return_value = mock_process

        await run_scraper_and_ingest_task()
        assert mock_process.kill.called


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_webhook_conn_error(
    session: Session, respx_mock: object
) -> None:
    """Test ingestion success even if webhook has connection error."""
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_stdout = json.dumps([])
    mock_process.communicate.return_value = (mock_stdout.encode(), b"")

    with patch("app.core.config.settings.N8N_WEBHOOK_URL", "http://n8n.test"):
        cast(Any, respx_mock).post("http://n8n.test").side_effect = httpx.ConnectError("Fail")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("app.api.v1.internal.engine", session.get_bind()):
                await run_scraper_and_ingest_task()


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_db_fail(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test ingestion failure at database level."""
    mock_stdout = json.dumps(
        [
            {
                "source": "schema_org",
                "original_link": "http://test.gr",
                "structured_data": {"name": "Test"},
            }
        ]
    )
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (mock_stdout.encode(), b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch(
            "app.api.v1.internal.internal_ingest_logic", side_effect=Exception("DB connection lost")
        ):
            with patch("app.api.v1.internal.engine", session.get_bind()):
                await run_scraper_and_ingest_task()


@pytest.mark.asyncio
async def test_run_scraper_and_ingest_task_webhook_general_fail(
    session: Session, respx_mock: object
) -> None:
    """Test ingestion success even if webhook has a general error."""
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_stdout = json.dumps([])
    mock_process.communicate.return_value = (mock_stdout.encode(), b"")

    with patch("app.core.config.settings.N8N_WEBHOOK_URL", "http://n8n.test"):
        cast(Any, respx_mock).post("http://n8n.test").mock(return_value=httpx.Response(500))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("app.api.v1.internal.engine", session.get_bind()):
                await run_scraper_and_ingest_task()
