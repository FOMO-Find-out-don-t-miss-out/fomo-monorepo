from unittest.mock import patch
from uuid import uuid4

from sqlmodel import Session

from packages.domain.models import (
    Event,
    EventProvenance,
    EventStatus,
    PendingEvent,
    PlaceVerificationStatus,
    Venue,
)

# Mock WKTElement globally for this test file
with patch("app.services.moderation.place_service.WKTElement", side_effect=lambda x, srid: x):
    from app.services.moderation.place_service import PlaceModerationService


def test_update_place_and_sync(session: Session):
    v = Venue(
        name="V", city="C", country_code="GR", lat=1.0, lng=1.0, full_address="A", relevance=1.0
    )
    p = PendingEvent(title="E", location_name="V", status="pending")
    e = Event(
        title="E",
        location_name="V",
        status=EventStatus.live,
        provenance=EventProvenance.aggregated,
    )
    session.add_all([v, p, e])
    session.commit()

    service = PlaceModerationService(session)
    updated = service.update_place(v.id, name="New V", lat=2.0, lng=2.0)

    assert updated.name == "New V"
    assert updated.lat == 2.0

    session.refresh(p)
    assert p.location_name == "New V"
    assert p.geocoding_status == "ambiguous"  # verification_status defaults to unverified

    session.refresh(e)
    assert e.location_name == "New V"


def test_update_place_collision(session: Session):
    v1 = Venue(
        name="V1", city="C", country_code="GR", lat=1.0, lng=1.0, full_address="A", relevance=1.0
    )
    v2 = Venue(
        name="V2", city="C", country_code="GR", lat=1.0, lng=1.0, full_address="A", relevance=1.0
    )
    session.add_all([v1, v2])
    session.commit()

    service = PlaceModerationService(session)
    result = service.update_place(v1.id, name="V2")

    assert result is None


def test_merge_places(session: Session):
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
        verification_status=PlaceVerificationStatus.manually_verified,
    )
    p = PendingEvent(title="E", location_name="Source", status="pending")
    session.add_all([v1, v2, p])
    session.commit()

    service = PlaceModerationService(session)
    success = service.merge_places(v1.id, v2.id)

    assert success is True
    assert session.get(Venue, v1.id) is None

    session.refresh(p)
    assert p.location_name == "Target"
    assert p.geocoding_status == "verified"


def test_delete_place_and_unlink(session: Session):
    v = Venue(
        name="V", city="C", country_code="GR", lat=1.0, lng=1.0, full_address="A", relevance=1.0
    )
    p = PendingEvent(title="E", location_name="V", status="pending", geocoding_status="verified")
    session.add_all([v, p])
    session.commit()

    service = PlaceModerationService(session)
    success = service.delete_place_and_unlink_events(v.id)

    assert success is True
    assert session.get(Venue, v.id) is None

    session.refresh(p)
    assert p.location is None
    assert p.geocoding_status == "failed"


def test_update_place_not_found(session: Session):
    service = PlaceModerationService(session)
    assert service.update_place(uuid4(), name="N") is None


def test_merge_places_not_found(session: Session):
    service = PlaceModerationService(session)
    assert service.merge_places(uuid4(), uuid4()) is False


def test_delete_place_not_found(session: Session):
    service = PlaceModerationService(session)
    assert service.delete_place_and_unlink_events(uuid4()) is False


def test_venue_service_compat_aliases(session: Session):
    """VenueModerationService and old method names are backward-compat aliases."""
    from app.services.moderation.venue_service import VenueModerationService

    assert VenueModerationService is PlaceModerationService
    service = VenueModerationService(session)
    # Verify old method names are still present
    assert callable(service.update_venue_record)
    assert callable(service.get_venues)
    assert callable(service.merge_venues)
    assert callable(service.delete_venue_and_unlink_events)
