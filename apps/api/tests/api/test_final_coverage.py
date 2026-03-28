from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from app.models.event import PendingEvent
from httpx import AsyncClient
from sqlmodel import Session


@pytest.mark.asyncio
async def test_purge_old_events(client: AsyncClient, session: Session) -> None:
    # Create an old published event
    old_event = PendingEvent(
        title="Old Event",
        status="published",
        start_time=datetime.now(UTC) - timedelta(days=40),
        location_name="V",
        country_code="GR",
    )
    session.add(old_event)
    session.commit()

    response = await client.delete("/api/v1/internal/cleanup-pending?days_old=30")
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1


def test_haversine_distance_same_point() -> None:
    from app.utils.geo_utils import haversine_distance

    assert haversine_distance(37.0, 23.0, 37.0, 23.0) == 0.0


@pytest.mark.asyncio
async def test_scraper_engine_load_registry_invalid_json() -> None:
    import tempfile

    from app.services.harvester.simple_scraper import ScraperEngine

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("invalid json")
        temp_path = f.name

    try:
        engine = ScraperEngine(registry_path=temp_path)
        assert engine.registry == {}
    finally:
        from pathlib import Path

        Path(temp_path).unlink()


@pytest.mark.asyncio
async def test_scraper_engine_ensure_string_non_str() -> None:
    from app.services.harvester.simple_scraper import ScraperEngine

    engine = ScraperEngine()
    # Test _ensure_string with None via scrape/schema
    html = (
        '<html><script type="application/ld+json">{"@type": "Event", "name": null, '
        '"startDate": "2026"}</script></html>'
    )
    mock_resp = MagicMock(status_code=200, text=html)
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        result = await engine.scrape("http://test.com")
        assert result.title is None


def test_datetime_helper_formats() -> None:
    from app.utils.datetime_utils import DateTimeHelper

    # Test various formats
    assert DateTimeHelper.safe_parse("2026-03-28 20:00:00").hour == 20
    assert DateTimeHelper.safe_parse("28/03/2026").day == 28
    assert DateTimeHelper.safe_parse("2026-03-28T20:00:00Z").hour == 20


@pytest.mark.asyncio
async def test_mapbox_client_error() -> None:
    from app.infrastructure.external.mapbox_client import MapboxClient

    client = MapboxClient()
    mock_resp = MagicMock(status_code=500)
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await client.search_box("Test", "GR")
        assert res is None


def test_purge_cache_error() -> None:
    from app.services.harvester.geocoder import GeocoderService

    with patch("app.services.harvester.geocoder.Session", side_effect=Exception("DB Error")):
        res = GeocoderService.purge_cache()
        assert res["deleted"] == 0
        assert "error" in res


def test_datetime_helper_list_dt() -> None:
    from app.utils.datetime_utils import DateTimeHelper

    dt = datetime(2026, 1, 1, tzinfo=UTC)
    assert DateTimeHelper.safe_parse([dt]) == dt


def test_datetime_helper_invalid_str() -> None:
    from app.utils.datetime_utils import DateTimeHelper

    default = datetime(2026, 1, 1, tzinfo=UTC)
    assert DateTimeHelper.safe_parse("invalid", default=default) == default


@pytest.mark.asyncio
async def test_clean_json_ld_headline(session: Session) -> None:
    from app.services.harvester.cleanser import CleansingService

    data = {"@type": "MusicEvent", "headline": "Headline Test", "startDate": "2026-01-01"}
    with patch("app.services.harvester.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            result = await CleansingService.clean_json_ld(data)
            assert result.title == "Headline Test"


@pytest.mark.asyncio
async def test_scraper_engine_normalize_www_more_com() -> None:
    from app.services.harvester.simple_scraper import ScraperEngine

    engine = ScraperEngine()
    registry = {"more.com": {"selectors": {"image": "img"}}}
    engine.registry_extractor.registry = registry
    html = '<html><img src="www.more.com/img.jpg"></html>'
    mock_resp = MagicMock(status_code=200, text=html)
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        result = await engine.scrape("https://more.com/event")
        assert result.photo_url == "https://www.more.com/img.jpg"


@pytest.mark.asyncio
async def test_mapbox_client_geocode_v6_error() -> None:
    from app.infrastructure.external.mapbox_client import MapboxClient

    client = MapboxClient()
    mock_resp = MagicMock(status_code=401)
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await client.geocode_v6("Test", "GR")
        assert res is None


@pytest.mark.asyncio
async def test_clean_json_ld_list_empty() -> None:
    from app.services.harvester.cleanser import CleansingService

    assert await CleansingService.clean_json_ld([]) is None


@pytest.mark.asyncio
async def test_to_pending_event_response_invalid_loc(session: Session, client: AsyncClient) -> None:
    # Trigger _to_pending_event_response with invalid location
    from uuid import uuid4

    from app.models.event import PendingEvent

    pending = PendingEvent(
        id=uuid4(),
        title="Invalid Loc",
        location="INVALID",  # This will fail to_shape and wkb_loads
        start_time=datetime.now(UTC),
        country_code="GR",
    )
    session.add(pending)
    session.commit()

    response = await client.get("/api/v1/moderation/pending-events")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_clean_json_ld_list_fields(session: Session) -> None:
    from app.services.harvester.cleanser import CleansingService

    data = {
        "@type": ["Event"],
        "name": ["N1"],
        "description": ["D1"],
        "startDate": ["2026-01-01T20:00:00Z"],
        "endDate": ["2026-01-01T22:00:00Z"],
        "location": {"name": "V"},
    }
    with patch("app.services.harvester.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            result = await CleansingService.clean_json_ld(data)
            assert result.title == "N1"
            assert result.description == "D1"


@pytest.mark.asyncio
async def test_batch_geocode_db_error() -> None:
    from app.services.harvester.geocoder import GeocoderService

    with patch("app.services.harvester.geocoder.Session", side_effect=Exception("DB Error")):
        res = await GeocoderService.batch_geocode_pending_events()
        assert res["updated"] == 0
        assert res["failed"] == 0


@pytest.mark.asyncio
async def test_clean_json_ld_image_dict(session: Session) -> None:
    from app.services.harvester.cleanser import CleansingService

    data = {
        "@type": "Event",
        "name": "T",
        "image": {"url": "https://img.com"},
        "location": {"name": "V"},
    }
    with patch("app.services.harvester.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            result = await CleansingService.clean_json_ld(data)
            assert result.event_metadata["image"] == "https://img.com"


@pytest.mark.asyncio
async def test_scraper_engine_load_registry_valid() -> None:
    import json
    import tempfile
    from pathlib import Path

    from app.services.harvester.simple_scraper import ScraperEngine

    data = {"test.com": {"country_code": "GR"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        temp_path = f.name

    try:
        engine = ScraperEngine(registry_path=temp_path)
        assert engine.registry["test.com"]["country_code"] == "GR"
    finally:
        Path(temp_path).unlink()
