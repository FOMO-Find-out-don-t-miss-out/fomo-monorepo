import pytest
import httpx
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.harvester.cleanser import CleansingService, ExtractedEvent
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_clean_json_ld_success():
    data = {
        "@type": "MusicEvent",
        "name": "Live Concert",
        "startDate": "2026-05-20T20:00:00Z",
        "location": {
            "name": "Arena",
            "geo": {
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        },
        "url": "http://tickets.com"
    }
    
    event = await CleansingService.clean_json_ld(data)
    assert isinstance(event, ExtractedEvent)
    assert event.title == "Live Concert"
    assert event.lat == 40.7128
    assert event.category == "Music"
    assert event.ticket_url == "http://tickets.com"

@pytest.mark.asyncio
async def test_clean_json_ld_list():
    data = [{
        "name": "List Event",
        "startDate": "2026-05-20T20:00:00Z"
    }]
    event = await CleansingService.clean_json_ld(data)
    assert event.title == "List Event"

@pytest.mark.asyncio
async def test_clean_json_ld_no_name():
    data = {"startDate": "2026-05-20T20:00:00Z"}
    event = await CleansingService.clean_json_ld(data)
    assert event is None

@pytest.mark.asyncio
async def test_clean_json_ld_exception(monkeypatch):
    data = {"name": "Fail"}
    with patch("app.services.harvester.cleanser.DateTimeHelper.safe_parse", side_effect=Exception("DB Error")):
        event = await CleansingService.clean_json_ld(data)
        assert event is None

def test_strip_html_noise():
    html = "<html><script>alert(1)</script><body><h1>Hello</h1><p>World</p></body></html>"
    cleaned = CleansingService._strip_html_noise(html)
    assert cleaned == "Hello World"
    assert "alert" not in cleaned
    assert CleansingService._strip_html_noise("") == ""

@pytest.mark.asyncio
async def test_clean_html_fallback_no_client(monkeypatch):
    import app.services.harvester.cleanser as cleanser
    monkeypatch.setattr(cleanser, "_client", None)
    
    result = await CleansingService.clean_html_fallback("Some long text that should be processed but no client")
    assert result == []

@pytest.mark.asyncio
async def test_clean_html_fallback_too_short():
    with patch("app.services.harvester.cleanser._client", MagicMock()):
        result = await CleansingService.clean_html_fallback("short")
        assert result == []

@pytest.mark.asyncio
async def test_clean_html_fallback_success():
    mock_client = MagicMock()
    mock_event = ExtractedEvent(
        title="AI Event",
        start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        category="Tech"
    )
    # Mock instructor client structure: _client.chat.completions.create
    mock_client.chat.completions.create.return_value = [mock_event]
    
    with patch("app.services.harvester.cleanser._client", mock_client):
        result = await CleansingService.clean_html_fallback("This is a long enough text to trigger the AI extraction process.")
        assert len(result) == 1
        assert result[0].title == "AI Event"

@pytest.mark.asyncio
async def test_clean_html_fallback_exception():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")
    
    with patch("app.services.harvester.cleanser._client", mock_client):
        result = await CleansingService.clean_html_fallback("This is a long enough text to trigger the AI extraction process.")
        assert result == []

@pytest.mark.asyncio
async def test_clean_html_fallback_geocoder_fallback():
    mock_client = MagicMock()
    mock_event = ExtractedEvent(
        title="No Coords Event",
        start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        location_name="Specific Club",
        lat=None,
        lng=None
    )
    mock_client.chat.completions.create.return_value = [mock_event]
    
    from app.services.harvester.geocoder import GeocodeResult
    mock_geo = GeocodeResult(lat=5.6, lng=7.8, relevance=1.0, full_address="Club address", country_code="UK")
    
    with patch("app.services.harvester.cleanser._client", mock_client):
        with patch("app.services.harvester.geocoder.GeocoderService.get_coordinates", return_value=mock_geo):
            result = await CleansingService.clean_html_fallback("This is a sufficiently long text to pass the 50 character minimum check for club events.", country_hint="UK")
            assert len(result) == 1
            assert result[0].lat == 5.6
            assert result[0].lng == 7.8

@pytest.mark.asyncio
async def test_clean_json_ld_geocoder_fallback():
    data = {
        "name": "Geocoded Concert",
        "startDate": "2026-05-20T20:00:00Z",
        "location": {"name": "Remote Venue"}
    }
    
    from app.services.harvester.geocoder import GeocodeResult
    mock_geo = GeocodeResult(lat=1.2, lng=3.4, relevance=1.0, full_address="Test", country_code="GR")
    
    with patch("app.services.harvester.geocoder.GeocoderService.get_coordinates", return_value=mock_geo):
        event = await CleansingService.clean_json_ld(data, country_hint="GR")
        assert event.lat == 1.2
        assert event.lng == 3.4
