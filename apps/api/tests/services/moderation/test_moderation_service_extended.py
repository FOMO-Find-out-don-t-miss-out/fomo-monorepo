from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

from sqlmodel import Session

from packages.domain.models import Event, EventProvenance, EventStatus, PendingEvent

# Mock WKTElement globally
with patch("app.services.moderation.moderation_service.WKTElement", side_effect=lambda x, srid: x):
    from app.services.moderation.moderation_service import ModerationService


def test_get_published_events(session: Session):
    e1 = Event(
        title="Published 1",
        start_time=datetime.now(UTC),
        location_name="V1",
        status=EventStatus.live,
        provenance=EventProvenance.aggregated,
    )
    e2 = Event(
        title="Published 2",
        start_time=datetime.now(UTC),
        location_name="V2",
        status=EventStatus.live,
        provenance=EventProvenance.aggregated,
    )
    session.add_all([e1, e2])
    session.commit()

    service = ModerationService(session)
    events = service.get_published_events()
    assert len(events) == 2

    events_v1 = service.get_published_events(location_name="V1")
    assert len(events_v1) == 1
    assert events_v1[0].title == "Published 1"


def test_unpublish_event(session: Session):
    # Setup: Live event and its pending counterpart
    start = datetime(2026, 1, 1, tzinfo=UTC)
    e = Event(
        title="To Unpublish",
        start_time=start,
        location_name="V",
        status=EventStatus.live,
        provenance=EventProvenance.aggregated,
    )
    p = PendingEvent(title="To Unpublish", start_time=start, status="published")
    session.add_all([e, p])
    session.commit()

    service = ModerationService(session)
    success = service.unpublish_event(e.id)

    assert success is True
    # Check live event deleted
    assert session.get(Event, e.id) is None
    # Check pending status reverted
    session.refresh(p)
    assert p.status == "pending"


def test_unpublish_event_not_found(session: Session):
    service = ModerationService(session)
    assert service.unpublish_event(uuid4()) is False


def test_update_published_event(session: Session):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    e = Event(
        title="Old Title",
        start_time=start,
        location_name="V",
        hype_score=10,
        status=EventStatus.live,
        provenance=EventProvenance.aggregated,
    )
    p = PendingEvent(title="Old Title", start_time=start, status="published", hype_score=10)
    session.add_all([e, p])
    session.commit()

    service = ModerationService(session)
    updated = service.update_published_event(e.id, title="New Title", hype_score=20)

    assert updated.title == "New Title"
    assert updated.hype_score == 20

    # Check sync to pending
    session.refresh(p)
    assert p.title == "New Title"
    assert p.hype_score == 20


def test_update_published_event_not_found(session: Session):
    service = ModerationService(session)
    assert service.update_published_event(uuid4(), title="New") is None
