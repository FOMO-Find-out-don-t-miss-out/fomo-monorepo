from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from app.services.harvester.cleanser import CleansingService
from sqlmodel import Session

from packages.domain.schemas.extracted_event import ExtractedEvent


@pytest.mark.asyncio
async def test_clean_json_ld_basic(session: Session) -> None:
    data = {
        "@type": "Event",
        "name": "Live Concert",
        "startDate": "2026-03-20T21:00:00Z",
        "location": {"name": "Technopolis", "address": {"addressLocality": "Athens"}},
    }
    # We must patch the engine/session used inside CleansingService/GeocoderService
    with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            result = await CleansingService.clean_json_ld(data)
            assert result is not None
            assert result.title == "Live Concert"
            assert result.location_name == "Technopolis"


@pytest.mark.asyncio
async def test_cleansing_sanitization(session: Session) -> None:
    data = {
        "@type": "Event",
        "name": "CONCERT NAME &amp; MORE   | MORE.COM",
        "startDate": "2026-03-20T21:00:00Z",
        "location": {"name": "Technopolis   ", "address": {"addressLocality": "Athens"}},
        "description": "This is a   description\nwith multiple lines and\ttabs.",
    }
    with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            result = await CleansingService.clean_json_ld(data)
            assert result is not None
            assert result.title == "Concert Name & More"
            assert result.location_name == "Technopolis"
            # description is explicitly stripped by JsonLdExtractor by design
            assert result.description is None


def test_sanitize_event_logic() -> None:
    """Directly tests the _sanitize_event internal method."""
    event = ExtractedEvent(
        title="DIRTY   TITLE | MORE.COM",
        location_name="  DIRTY   VENUE  ",
        description="Line 1\nLine 2\tTabbed",
        start_time=datetime.now(UTC),
    )
    CleansingService._sanitize_event(event)
    assert event.title == "Dirty Title"
    assert event.location_name == "DIRTY VENUE"
    assert event.description == "Line 1 Line 2 Tabbed"


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
    with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            result = await CleansingService.clean_json_ld(data)
            assert result is not None
            assert result.category == "Music"


@pytest.mark.asyncio
async def test_clean_json_ld_exception() -> None:
    data = {"name": "Fail", "location": {"name": "Some Venue"}}
    # The cleanser catches internal exceptions and returns None
    with patch(
        "app.services.harvester.location.geocoder.GeocoderService.get_coordinates",
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

    with patch("app.services.harvester.cleansing.ai_extractor._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
            with patch("app.repositories.venue_repository.Session", return_value=session):
                result = await CleansingService.clean_html_fallback(html)
                assert len(result) == 1
                assert result[0].title == "AI Event"


@pytest.mark.asyncio
async def test_clean_html_fallback_no_client(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.harvester.cleansing.ai_extractor as ai_extractor

    monkeypatch.setattr(ai_extractor, "_client", None)
    result = await CleansingService.clean_html_fallback("some text")
    assert result == []


@pytest.mark.asyncio
async def test_clean_html_fallback_short_text() -> None:
    result = await CleansingService.clean_html_fallback("too short")
    assert result == []


@pytest.mark.asyncio
async def test_clean_html_fallback_exception() -> None:
    with patch("app.services.harvester.cleansing.ai_extractor._client") as mock_client:
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

    from app.services.harvester.location.geocoder import GeocodeResult

    mock_geo = GeocodeResult(
        lat=37.0,
        lng=23.0,
        relevance=1.0,
        full_address="A",
        country_code="GR",
        geocoding_status="verified",
    )

    with patch("app.services.harvester.cleansing.ai_extractor._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
            with patch("app.repositories.venue_repository.Session", return_value=session):
                with patch(
                    "app.services.harvester.location.geocoder.GeocoderService.get_coordinates",
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

    with patch("app.services.harvester.cleansing.ai_extractor._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        with patch(
            "app.services.harvester.location.geocoder.GeocoderService.get_coordinates",
            return_value=None,
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
    with patch("app.services.harvester.cleansing.ai_extractor._client", None):
        result = await CleansingService.clean_html_fallback(
            "Some long enough text to pass the check"
        )
        assert result == []


# ── FOMO-166: category normalization scenarios ─────────────────────────────


@pytest.mark.asyncio
async def test_clean_json_ld_concert_maps_to_music(session: Session) -> None:
    """A More.com-style concert event with no explicit category resolves to Music."""
    data = {
        "@type": "Event",
        "name": "Coldplay Live in Athens",
        "startDate": "2026-06-20T21:00:00Z",
        "location": {"name": "OAKA", "address": {"addressLocality": "Athens"}},
    }
    with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            result = await CleansingService.clean_json_ld(data)
            assert result is not None
            assert result.category == "Music"


@pytest.mark.asyncio
async def test_clean_json_ld_greek_music_event_maps_to_music(session: Session) -> None:
    data = {
        "@type": "Event",
        "name": "Μεγάλη Συναυλία στο Ωδείο Ηρώδου Αττικού",
        "startDate": "2026-07-15T21:00:00Z",
        "location": {"name": "Odeon of Herodes Atticus"},
    }
    with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            result = await CleansingService.clean_json_ld(data)
            assert result is not None
            assert result.category == "Music"


@pytest.mark.asyncio
async def test_clean_json_ld_unrelated_event_remains_other(session: Session) -> None:
    """An event with no music/art/tech signal anywhere conservatively stays Other."""
    data = {
        "@type": "Event",
        "name": "Annual Neighborhood Cleanup Day",
        "startDate": "2026-05-01T10:00:00Z",
        "location": {"name": "Town Square"},
    }
    with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            result = await CleansingService.clean_json_ld(data)
            assert result is not None
            assert result.category == "Other"


@pytest.mark.asyncio
async def test_clean_html_fallback_lowercase_ai_category_normalized_to_music(
    session: Session,
) -> None:
    """Regression test: the DeepSeek AI path previously returned a lowercase
    "music" category which bypassed the domain classifier override (the
    cleanser only re-classified when category was exactly "Other"). Category
    values are now normalized at the ExtractedEvent schema boundary, so the
    canonical "Music" value is kept end to end."""
    html = (
        "<html><body>This is a sufficiently long text to pass the 50 character "
        "minimum check for a live concert at Technopolis tonight.</body></html>"
    )
    mock_event = ExtractedEvent(
        title="Live Concert at Technopolis", start_time="2026-01-01T00:00:00Z", category="music"
    )
    assert mock_event.category == "Music"

    mock_response = MagicMock()
    mock_response.tasks = [mock_event]

    with patch("app.services.harvester.cleansing.ai_extractor._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
            with patch("app.repositories.venue_repository.Session", return_value=session):
                result = await CleansingService.clean_html_fallback(html)
                assert len(result) == 1
                assert result[0].category == "Music"


@pytest.mark.asyncio
async def test_clean_html_fallback_unrecognized_ai_category_falls_back_to_classifier(
    session: Session,
) -> None:
    """When the AI's category doesn't resolve to any canonical value, it
    normalizes to "Other" at the schema boundary, allowing the domain
    classifier's own (conservative) result to take over."""
    html = (
        "<html><body>This is a sufficiently long text to pass the 50 character "
        "minimum check for an AI conference happening downtown.</body></html>"
    )
    mock_event = ExtractedEvent(
        title="AI Conference", start_time="2026-01-01T00:00:00Z", category="not-a-real-category"
    )
    assert mock_event.category == "Other"

    mock_response = MagicMock()
    mock_response.tasks = [mock_event]

    with patch("app.services.harvester.cleansing.ai_extractor._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
            with patch("app.repositories.venue_repository.Session", return_value=session):
                result = await CleansingService.clean_html_fallback(html)
                assert len(result) == 1
                assert result[0].category == "Tech"
