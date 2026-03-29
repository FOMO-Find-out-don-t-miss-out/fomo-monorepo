from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from app.services.harvester.cleanser import CleansingService, ExtractedEvent
from sqlmodel import Session


@pytest.mark.asyncio
async def test_clean_json_ld_basic(session: Session) -> None:
    data = {
        "@type": "Event",
        "name": "Live Concert",
        "startDate": "2026-03-20T21:00:00Z",
        "location": {"name": "Technopolis", "address": {"addressLocality": "Athens"}},
    }
    # We must patch the engine/session used inside CleansingService/GeocoderService
    with patch("app.services.harvester.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            result = await CleansingService.clean_json_ld(data)
            assert result is not None
            assert result.title == "Live Concert"
            assert result.location_name == "Technopolis"


@pytest.mark.asyncio
async def test_clean_json_ld_list(session: Session) -> None:
    data = [
        {
            "@type": "MusicEvent",
            "name": "Festival",
            "startDate": "2026-04-01T18:00:00Z",
            "location": {"name": "Plateia"},
        }
    ]
    with patch("app.services.harvester.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            result = await CleansingService.clean_json_ld(data)
            assert result is not None
            assert result.category == "Music"


@pytest.mark.asyncio
async def test_clean_json_ld_exception() -> None:
    data = {"name": "Fail", "location": {"name": "Some Venue"}}
    # The cleanser catches internal exceptions and returns None
    with patch(
        "app.services.harvester.geocoder.GeocoderService.get_coordinates",
        side_effect=Exception("Geo Error"),
    ):
        result = await CleansingService.clean_json_ld(data)
        assert result is None


@pytest.mark.asyncio
async def test_clean_html_fallback_success(session: Session) -> None:
    html = (
        "<html><body>This is a sufficiently long text to pass the 50 character minimum check "
        "for events happening at Technopolis at 9pm.</body></html>"
    )
    mock_event = ExtractedEvent(
        title="AI Event", start_time="2026-01-01T00:00:00Z", category="Tech"
    )
    # We must use a real object or a very careful mock because pydantic validates the response
    mock_response = MagicMock()
    mock_response.tasks = [mock_event]

    with patch("app.services.harvester.cleanser._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        with patch("app.services.harvester.geocoder.engine", session.get_bind()):
            with patch("app.repositories.venue_repository.Session", return_value=session):
                result = await CleansingService.clean_html_fallback(html)
                assert len(result) == 1
                assert result[0].title == "AI Event"


@pytest.mark.asyncio
async def test_clean_html_fallback_no_client(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.harvester.cleanser as cleanser

    monkeypatch.setattr(cleanser, "_client", None)
    result = await CleansingService.clean_html_fallback("some text")
    assert result == []


@pytest.mark.asyncio
async def test_clean_html_fallback_short_text() -> None:
    result = await CleansingService.clean_html_fallback("too short")
    assert result == []


@pytest.mark.asyncio
async def test_clean_html_fallback_exception() -> None:
    with patch("app.services.harvester.cleanser._client") as mock_client:
        mock_client.chat.completions.create.side_effect = Exception("AI Fail")
        result = await CleansingService.clean_html_fallback(
            "This is a sufficiently long text to pass the 50 character minimum check."
        )
        assert result == []


@pytest.mark.asyncio
async def test_clean_html_fallback_with_geocoding(session: Session) -> None:
    mock_event = ExtractedEvent(
        title="AI Event",
        start_time="2026-01-01T00:00:00Z",
        location_name="Technopolis",
        category="Tech",
    )
    mock_response = MagicMock()
    mock_response.tasks = [mock_event]

    from app.services.harvester.geocoder import GeocodeResult

    mock_geo = GeocodeResult(
        lat=37.0,
        lng=23.0,
        relevance=1.0,
        full_address="A",
        country_code="GR",
        geocoding_status="verified",
    )

    with patch("app.services.harvester.cleanser._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        with patch("app.services.harvester.geocoder.engine", session.get_bind()):
            with patch("app.repositories.venue_repository.Session", return_value=session):
                with patch(
                    "app.services.harvester.geocoder.GeocoderService.get_coordinates",
                    return_value=mock_geo,
                ):
                    result = await CleansingService.clean_html_fallback(
                        "This is a sufficiently long text to pass the 50 character minimum check "
                        "for club events.",
                        country_hint="UK",
                    )
                    assert result[0].lat == 37.0
                    assert result[0].geocoding_status == "verified"


@pytest.mark.asyncio
async def test_clean_html_fallback_geocoding_fail() -> None:
    mock_event = ExtractedEvent(
        title="AI Event",
        start_time="2026-01-01T00:00:00Z",
        location_name="Unknown",
        category="Tech",
    )
    mock_response = MagicMock()
    mock_response.tasks = [mock_event]

    with patch("app.services.harvester.cleanser._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        with patch(
            "app.services.harvester.geocoder.GeocoderService.get_coordinates", return_value=None
        ):
            result = await CleansingService.clean_html_fallback(
                "This is a sufficiently long text to pass the 50 character minimum check."
            )
            assert result[0].geocoding_status == "failed"


def test_extracted_event_validators() -> None:
    # Test start_time validator
    ev = ExtractedEvent(title="T", start_time="2026-01-01T10:00:00Z")
    assert isinstance(ev.start_time, datetime)

    # Test end_time validator
    ev = ExtractedEvent(title="T", start_time=datetime.now(UTC), end_time="2026-01-01T12:00:00Z")
    assert isinstance(ev.end_time, datetime)


@pytest.mark.asyncio
async def test_clean_html_fallback_client_none() -> None:
    with patch("app.services.harvester.cleanser._client", None):
        result = await CleansingService.clean_html_fallback(
            "Some long enough text to pass the check"
        )
        assert result == []
