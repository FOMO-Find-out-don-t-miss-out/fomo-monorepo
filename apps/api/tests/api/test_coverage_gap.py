from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from app.main import app
from app.schemas.moderation import PendingEventResponse
from app.services.harvester.cleanser import CleansingService
from fastapi.testclient import TestClient

from packages.domain.schemas.extracted_event import ExtractedEvent

client = TestClient(app)

# --- Moderation.py Coverage ---


class MockEvent:
    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)
        # Set defaults for missing attributes to satisfy getattr/hasattr
        defaults = {
            "end_time": None,
            "hype_score": 0,
            "category": "Other",
            "sub_category": None,
            "ticket_url": None,
            "source_url": None,
            "source_provider": "unknown",
            "ingestion_method": "unknown",
            "location_name": None,
            "country_code": None,
            "parent_id": None,
            "photo_url": None,
            "event_metadata": {},
            "tags": [],
            "status": "pending",
            "raw_content": None,
            "rejection_reason": None,
            "confidence_score": None,
            "geocoding_status": "failed",
            "geocoding_metadata": {},
        }
        for k, v in defaults.items():
            if not hasattr(self, k):
                setattr(self, k, v)

    def model_dump(self) -> dict[str, Any]:
        return {k: v for k, v in vars(self).items() if not k.startswith("_") and k != "model_dump"}


def test_to_pending_event_response_hex_location():
    # Covers geo_utils.py: 16-24 (parsing hex WKB string)
    event = MockEvent(id=uuid4(), title="Test", start_time=datetime.now(UTC), location="some_hex")

    mock_shape = MagicMock()
    mock_shape.x = 1.0
    mock_shape.y = 2.0

    with patch("packages.domain.utils.geo_utils.to_shape", side_effect=Exception("not WKBElement")):
        with patch("packages.domain.utils.geo_utils.wkb_loads", return_value=mock_shape):
            with patch("binascii.unhexlify", return_value=b"some_bytes"):
                resp = PendingEventResponse.model_validate(event)
                assert resp.location == {"type": "Point", "coordinates": [1.0, 2.0]}


def test_to_pending_event_response_invalid_location():
    # Covers the second 'except' in geo_utils.py location parsing
    event = MockEvent(id=uuid4(), title="Test", start_time=datetime.now(UTC), location=MagicMock())
    event.location.__str__.return_value = "raw_string"

    with patch("packages.domain.utils.geo_utils.to_shape", side_effect=Exception("to_shape fail")):
        resp = PendingEventResponse.model_validate(event)
        # In the new implementation, if it fails all parsing, it returns None
        # or original if it was not None.
        # Actually parse_wkb_to_geojson returns None if it fails.
        assert resp.location is None


def test_moderation_404_errors():
    # Covers HTTPException(404) in moderation router
    uid = uuid4()
    mod_svc = "app.services.moderation.moderation_service.ModerationService"

    with patch(f"{mod_svc}.unpublish_event", return_value=False):
        response = client.post(f"/api/v1/moderation/events/{uid}/unpublish")
        assert response.status_code == 404

    with patch(f"{mod_svc}.update_published_event", return_value=None):
        response = client.patch(f"/api/v1/moderation/events/{uid}", json={"title": "new"})
        assert response.status_code == 404

    with patch(f"{mod_svc}.approve_events", return_value=0):
        response = client.post(f"/api/v1/moderation/pending-events/{uid}/approve")
        assert response.status_code == 404

    with patch(f"{mod_svc}.reject_events", return_value=0):
        response = client.post(f"/api/v1/moderation/pending-events/{uid}/reject")
        assert response.status_code == 404

    with patch(f"{mod_svc}.add_occurrence", return_value=None):
        resp = client.post(
            f"/api/v1/moderation/pending-events/{uid}/occurrences",
            json={"start_time": "2026-01-01T00:00:00Z"},
        )
        assert resp.status_code == 404


# --- Cleanser.py Coverage ---


@pytest.mark.asyncio
async def test_clean_json_ld_variations():
    # Covers cleanser.py: 89 (invalid startDate)
    data = {
        "@type": "Event",
        "name": "Test Event",
        "startDate": "invalid-date",
        "location": {"name": "Venue"},
    }
    with patch(
        "packages.domain.schemas.extracted_event.DateTimeHelper.safe_parse",
        return_value="not-a-datetime",
    ):
        res = await CleansingService.clean_json_ld(data)
        assert res is None


@pytest.mark.asyncio
async def test_clean_json_ld_image_variations():
    # Covers cleanser.py: 241-243 (image as list of dicts)
    data = {
        "@type": "Event",
        "name": "Test Event",
        "image": [{"url": "http://img.com/1.jpg"}],
        "startDate": "2026-01-01T00:00:00Z",
    }
    res = await CleansingService.clean_json_ld(data)
    # We STOP collecting images, so it shouldn't be in metadata as 'image' anymore
    assert "image" not in res.event_metadata


@pytest.mark.asyncio
async def test_clean_json_ld_exception():
    # Covers cleanser.py: 254 (except Exception)
    res = await CleansingService.clean_json_ld(None)
    assert res is None


@pytest.mark.asyncio
async def test_clean_html_fallback_no_client():
    # Covers cleanser.py: 268-270
    with patch("app.services.harvester.cleansing.ai_extractor._client", None):
        res = await CleansingService.clean_html_fallback("some html")
        assert res == []


@pytest.mark.asyncio
async def test_clean_html_fallback_short_text():
    # Covers cleanser.py: 273
    res = await CleansingService.clean_html_fallback("short")
    assert res == []


@pytest.mark.asyncio
async def test_clean_html_fallback_geocoding_fail():
    # Covers cleanser.py: 343-347 (geocoding Exception)
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_event = ExtractedEvent(title="E1", start_time="2026-01-01T10:00:00Z", location_name="V1")
    mock_response.tasks = [mock_event]
    mock_client.chat.completions.create.return_value = mock_response

    long_text = "Long enough text to trigger extraction " * 5
    with patch("app.services.harvester.cleansing.ai_extractor._client", mock_client):
        with patch(
            "app.services.harvester.location.geocoder.GeocoderService.get_coordinates",
            side_effect=Exception("Geo Fail"),
        ):
            res = await CleansingService.clean_html_fallback(long_text)
            assert len(res) == 1
            assert res[0].geocoding_status == "failed"


@pytest.mark.asyncio
async def test_clean_html_fallback_exception():
    # Covers cleanser.py: 349-351 (Gemini extraction failed)
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("Gemini Fail")

    long_text = "Long enough text to trigger extraction " * 5
    with patch("app.services.harvester.cleansing.ai_extractor._client", mock_client):
        res = await CleansingService.clean_html_fallback(long_text)
        assert res == []
