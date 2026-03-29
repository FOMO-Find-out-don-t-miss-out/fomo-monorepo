from unittest.mock import MagicMock, patch

from packages.domain.models import Event, PendingEvent


def test_event_photo_url_normalization():
    # Test normalization logic
    e = Event(title="T", event_metadata={"image": "www.test.com/img.png"})
    assert e.photo_url == "https://www.test.com/img.png"

    e.event_metadata = {"photo_url": "//cdn.com/test.jpg"}
    assert e.photo_url == "https://cdn.com/test.jpg"

    e.event_metadata = {"photo_url": "http://direct.com/a.png"}
    assert e.photo_url == "http://direct.com/a.png"

    e.event_metadata = {"image": ["list.com/1.png"]}
    assert (
        e.photo_url == "list.com/1.png"
    )  # No prefix here because it doesn't start with www or // or http

    e.event_metadata = {"image": "  www.trimmed.com/a.png  "}
    assert e.photo_url == "https://www.trimmed.com/a.png"


def test_event_location_serialization():
    from unittest.mock import MagicMock

    e = Event(title="T")
    # Test serializer directly
    assert e.serialize_location(None) is None

    # Mock a shape that to_shape can handle
    mock_shape = MagicMock()
    mock_shape.x = 1.0
    mock_shape.y = 2.0

    with patch("packages.domain.models.event.to_shape", return_value=mock_shape):
        res = e.serialize_location(MagicMock())
        assert res == {"type": "Point", "coordinates": [1.0, 2.0]}

    # Test exception path
    with patch("packages.domain.models.event.to_shape", side_effect=Exception("Fail")):
        val = "some_val"
        assert e.serialize_location(val) == val


def test_pending_event_location_serialization():
    p = PendingEvent(title="P")
    assert p.serialize_location(None) is None

    mock_shape = MagicMock()
    mock_shape.x = 3.0
    mock_shape.y = 4.0

    with patch("packages.domain.models.event.to_shape", return_value=mock_shape):
        res = p.serialize_location(MagicMock())
        assert res == {"type": "Point", "coordinates": [3.0, 4.0]}


def test_response_schema_location_serialization():
    from datetime import datetime
    from uuid import uuid4

    from app.schemas.moderation import EventBaseResponse

    resp = EventBaseResponse(
        id=uuid4(), title="T", start_time=datetime.now(), hype_score=0, category="Other"
    )

    assert resp.serialize_location(None) is None

    mock_shape = MagicMock()
    mock_shape.x = 5.0
    mock_shape.y = 6.0

    with patch("packages.domain.utils.geo_utils.to_shape", return_value=mock_shape):
        res = resp.serialize_location(MagicMock())
        assert res == {"type": "Point", "coordinates": [5.0, 6.0]}

    with patch("packages.domain.utils.geo_utils.to_shape", side_effect=Exception()):
        val = {"type": "Point"}
        # parse_wkb_to_geojson returns dicts as-is
        assert resp.serialize_location(val) == val


def test_pending_event_computed_fields():
    p = PendingEvent(title="P", event_metadata={"image": "www.more.com/img.png"})
    assert p.photo_url == "https://www.more.com/img.png"
