from unittest.mock import MagicMock, patch

from packages.domain.models import Event, EventProvenance, EventStatus, PendingEvent

_LIFECYCLE = {"status": EventStatus.live, "provenance": EventProvenance.aggregated}


def test_event_photo_url_normalization():
    # Test normalization logic during initialization
    e = Event(title="T", event_metadata={"image": "www.test.com/img.png"}, **_LIFECYCLE)
    assert e.photo_url == "https://www.test.com/img.png"

    e = Event(title="T", event_metadata={"photo_url": "//cdn.com/test.jpg"}, **_LIFECYCLE)
    assert e.photo_url == "https://cdn.com/test.jpg"

    e = Event(title="T", event_metadata={"photo_url": "http://direct.com/a.png"}, **_LIFECYCLE)
    assert e.photo_url == "http://direct.com/a.png"

    e = Event(title="T", event_metadata={"image": ["list.com/1.png"]}, **_LIFECYCLE)
    assert e.photo_url == "list.com/1.png"

    e = Event(title="T", event_metadata={"image": "  www.trimmed.com/a.png  "}, **_LIFECYCLE)
    assert e.photo_url == "https://www.trimmed.com/a.png"

    # Test explicit photo_url
    e = Event(title="T", photo_url="www.explicit.com/a.png", **_LIFECYCLE)
    assert e.photo_url == "https://www.explicit.com/a.png"


def test_event_location_serialization():
    from unittest.mock import MagicMock

    e = Event(title="T", **_LIFECYCLE)
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


def test_event_status_and_provenance_have_no_silent_defaults():
    # No Python-level default: fields are None until explicitly set.
    # Constraint enforcement happens at the DB level.
    e = Event(title="No lifecycle fields")  # type: ignore[call-arg]
    assert e.status is None
    assert e.provenance is None
