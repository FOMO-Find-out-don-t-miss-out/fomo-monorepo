from unittest.mock import patch
from uuid import uuid4

from app.models.event import Event, PendingEvent
from app.models.venue import Venue
from sqlmodel import Session

# Mock WKTElement globally for this test file
with patch("app.services.moderation.venue_service.WKTElement", side_effect=lambda x, srid: x):
    from app.services.moderation.venue_service import VenueModerationService


def test_update_venue_record_and_sync(session: Session):
    v = Venue(
        name="V", city="C", country_code="GR", lat=1.0, lng=1.0, full_address="A", relevance=1.0
    )
    p = PendingEvent(title="E", location_name="V", status="pending")
    e = Event(title="E", location_name="V")
    session.add_all([v, p, e])
    session.commit()

    service = VenueModerationService(session)
    updated = service.update_venue_record(v.id, name="New V", lat=2.0, lng=2.0)

    assert updated.name == "New V"
    assert updated.lat == 2.0

    # Check sync
    session.refresh(p)
    assert p.location_name == "New V"
    assert p.geocoding_status == "ambiguous"  # Since is_manually_verified defaults to False

    session.refresh(e)
    assert e.location_name == "New V"


def test_update_venue_collision(session: Session):
    v1 = Venue(
        name="V1", city="C", country_code="GR", lat=1.0, lng=1.0, full_address="A", relevance=1.0
    )
    v2 = Venue(
        name="V2", city="C", country_code="GR", lat=1.0, lng=1.0, full_address="A", relevance=1.0
    )
    session.add_all([v1, v2])
    session.commit()

    service = VenueModerationService(session)
    # Try to rename v1 to V2 in same city
    result = service.update_venue_record(v1.id, name="V2")

    assert result is None  # Collision check works


def test_merge_venues(session: Session):
    v1 = Venue(
        name="Source",
        city="C",
        country_code="GR",
        lat=1.0,
        lng=1.0,
        full_address="A",
        relevance=1.0,
    )
    v2 = Venue(
        name="Target",
        city="C",
        country_code="GR",
        lat=2.0,
        lng=2.0,
        full_address="A2",
        relevance=1.0,
        is_manually_verified=True,
    )
    p = PendingEvent(title="E", location_name="Source", status="pending")
    session.add_all([v1, v2, p])
    session.commit()

    service = VenueModerationService(session)
    success = service.merge_venues(v1.id, v2.id)

    assert success is True
    assert session.get(Venue, v1.id) is None

    session.refresh(p)
    assert p.location_name == "Target"
    assert p.geocoding_status == "verified"


def test_delete_venue_and_unlink(session: Session):
    v = Venue(
        name="V", city="C", country_code="GR", lat=1.0, lng=1.0, full_address="A", relevance=1.0
    )
    p = PendingEvent(title="E", location_name="V", status="pending", geocoding_status="verified")
    session.add_all([v, p])
    session.commit()

    service = VenueModerationService(session)
    success = service.delete_venue_and_unlink_events(v.id)

    assert success is True
    assert session.get(Venue, v.id) is None

    session.refresh(p)
    assert p.location is None
    assert p.geocoding_status == "failed"


def test_update_venue_not_found(session: Session):
    service = VenueModerationService(session)
    assert service.update_venue_record(uuid4(), name="N") is None


def test_merge_venues_not_found(session: Session):
    service = VenueModerationService(session)
    assert service.merge_venues(uuid4(), uuid4()) is False


def test_delete_venue_not_found(session: Session):
    service = VenueModerationService(session)
    assert service.delete_venue_and_unlink_events(uuid4()) is False
