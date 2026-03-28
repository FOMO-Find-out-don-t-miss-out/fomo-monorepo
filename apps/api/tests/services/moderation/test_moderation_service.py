from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.models.event import Event, PendingEvent
from app.models.venue import Venue
from sqlmodel import Session, select

# Mock WKTElement globally for this test file
with patch("app.services.moderation.moderation_service.WKTElement", side_effect=lambda x, srid: x):
    from app.services.moderation.moderation_service import ModerationService


def test_approve_events(session: Session):
    # Setup
    pending = PendingEvent(
        title="Test Event",
        location_name="Test Venue",
        start_time=datetime.now(UTC),
        status="pending",
        geocoding_status="verified",
        location="POINT(23.7 37.9)",  # Mocked WKTElement
        geocoding_metadata={"city": "Athens", "full_address": "Street 1"},
    )
    session.add(pending)
    session.commit()

    # We need to mock to_shape since it will fail on string mock
    with patch("app.services.moderation.moderation_service.to_shape") as mock_to_shape:
        mock_shape = MagicMock()
        mock_shape.x = 23.7
        mock_shape.y = 37.9
        mock_to_shape.return_value = mock_shape

        service = ModerationService(session)
        count = service.approve_events([pending.id])

    assert count == 1

    # Check if live event was created
    live_event = session.exec(select(Event).where(Event.title == "Test Event")).first()
    assert live_event is not None
    assert live_event.location_name == "Test Venue"

    # Check if venue was created
    venue = session.exec(select(Venue).where(Venue.name == "Test Venue")).first()
    assert venue is not None
    assert venue.city == "Athens"

    # Check if pending event status updated
    session.refresh(pending)
    assert pending.status == "published"


def test_reject_events(session: Session):
    pending = PendingEvent(title="To be rejected", status="pending")
    session.add(pending)
    session.commit()

    service = ModerationService(session)
    count = service.reject_events([pending.id])

    assert count == 1
    assert session.get(PendingEvent, pending.id) is None


def test_update_pending_event_rename_venue(session: Session):
    p1 = PendingEvent(title="E1", location_name="Old Venue", country_code="GR", status="pending")
    p2 = PendingEvent(title="E2", location_name="Old Venue", country_code="GR", status="pending")
    v = Venue(
        name="Old Venue",
        country_code="GR",
        city="Athens",
        lat=1.0,
        lng=1.0,
        full_address="Addr",
        relevance=1.0,
    )
    session.add_all([p1, p2, v])
    session.commit()

    service = ModerationService(session)
    updated = service.update_pending_event(p1.id, location_name="New Venue")

    assert updated.location_name == "New Venue"

    # Check if p2 was also updated
    session.refresh(p2)
    assert p2.location_name == "New Venue"

    # Check if venue was renamed
    session.refresh(v)
    assert v.name == "New Venue"


def test_batch_update_location_by_name(session: Session):
    p = PendingEvent(title="E", location_name="V", status="pending")
    e = Event(title="E", location_name="V")
    session.add_all([p, e])
    session.commit()

    service = ModerationService(session)
    service.batch_update_location_by_name(
        target_name="V",
        location_wkt="POINT(23.7 37.9)",
        status="verified",
        confidence=0.95,
        metadata={"city": "Athens"},
    )

    session.refresh(p)
    assert p.geocoding_status == "verified"
    assert p.confidence_score == 0.95
    assert p.geocoding_metadata == {"city": "Athens"}
    # Note: in test env, WKTElement(location_wkt) might return the string itself due to mock


def test_add_occurrence(session: Session):
    p = PendingEvent(title="Original", location_name="V", status="pending")
    session.add(p)
    session.commit()

    service = ModerationService(session)
    new_start = datetime(2026, 1, 1)
    new_occ = service.add_occurrence(p.id, new_start)

    assert new_occ is not None
    assert new_occ.title == "Original"
    assert new_occ.start_time.replace(tzinfo=None) == new_start
    assert new_occ.parent_id == p.id

    session.refresh(p)
    assert p.parent_id == p.id


def test_add_occurrence_not_found(session: Session):
    service = ModerationService(session)
    result = service.add_occurrence(uuid4(), datetime.now())
    assert result is None


def test_update_pending_event_not_found(session: Session):
    service = ModerationService(session)
    result = service.update_pending_event(uuid4(), title="New")
    assert result is None
