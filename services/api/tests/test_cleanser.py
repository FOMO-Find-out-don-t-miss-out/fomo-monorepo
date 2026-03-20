import pytest
import httpx
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.harvester.cleanser import CleansingService, ExtractedEvent
from datetime import datetime

def test_clean_json_ld_success():
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
    
    event = CleansingService.clean_json_ld(data)
    assert isinstance(event, ExtractedEvent)
    assert event.title == "Live Concert"
    assert event.lat == 40.7128
    assert event.category == "Music"
    assert event.ticket_url == "http://tickets.com"

def test_clean_json_ld_list():
    data = [{
        "name": "List Event",
        "startDate": "2026-05-20T20:00:00Z"
    }]
    event = CleansingService.clean_json_ld(data)
    assert event.title == "List Event"

def test_clean_json_ld_no_name():
    data = {"startDate": "2026-05-20T20:00:00Z"}
    event = CleansingService.clean_json_ld(data)
    assert event is None

def test_clean_json_ld_exception(monkeypatch):
    def mock_get(*args):
        raise Exception("Fatal Error")
    data = {"name": "Fail"}
    # We need to mock something inside the try block that will raise
    with patch("app.services.harvester.cleanser.DateTimeHelper.safe_parse", side_effect=Exception("DB Error")):
        event = CleansingService.clean_json_ld(data)
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
    assert result is None

@pytest.mark.asyncio
async def test_clean_html_fallback_too_short():
    # Ensure _client is NOT None for this test if it was set globally
    with patch("app.services.harvester.cleanser._client", MagicMock()):
        result = await CleansingService.clean_html_fallback("short")
        assert result is None

@pytest.mark.asyncio
async def test_clean_html_fallback_success():
    mock_client = MagicMock()
    mock_event = ExtractedEvent(
        title="AI Event",
        start_time=datetime(2026, 1, 1),
        category="Tech"
    )
    mock_client.chat.completions.create.return_value = mock_event
    
    with patch("app.services.harvester.cleanser._client", mock_client):
        result = await CleansingService.clean_html_fallback("This is a long enough text to trigger the AI extraction process.")
        assert result.title == "AI Event"

@pytest.mark.asyncio
async def test_clean_html_fallback_exception():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")
    
    with patch("app.services.harvester.cleanser._client", mock_client):
        result = await CleansingService.clean_html_fallback("This is a long enough text to trigger the AI extraction process.")
        assert result is None
