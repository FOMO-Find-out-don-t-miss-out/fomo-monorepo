from datetime import UTC, datetime
from uuid import uuid4

from app.services.event_relationship_service import EventRelationshipService
from sqlmodel import Session, select

from packages.domain.models import (
    Event,
    EventRelationship,
    EventStatus,
    EventVisibility,
    RelationshipType,
    User,
)


def create_user(session: Session, email: str = "user@example.com") -> User:
    user = User(external_id=str(uuid4()), email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_event(
    session: Session,
    title: str,
    *,
    status: EventStatus = EventStatus.live,
    visibility: EventVisibility = EventVisibility.public,
) -> Event:
    event = Event(
        title=title,
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 4, 1, 20, 0, tzinfo=UTC),
        category="Music",
        status=status,
        visibility=visibility,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def relationship_count(session: Session) -> int:
    return len(session.exec(select(EventRelationship)).all())


def test_mark_interest_creates_relationship(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Interest")
    service = EventRelationshipService(session)

    relationship = service.mark_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.interested,
    )

    assert relationship is not None
    assert relationship.user_id == user.id
    assert relationship.event_id == event.id
    assert relationship.relationship_type == RelationshipType.interested


def test_mark_interest_is_idempotent(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Interest Idempotent")
    service = EventRelationshipService(session)

    first = service.mark_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.interested,
    )
    second = service.mark_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.interested,
    )

    assert first is not None
    assert second is not None
    assert first.id == second.id
    assert relationship_count(session) == 1


def test_remove_interest_is_idempotent(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Remove Interest")
    service = EventRelationshipService(session)
    service.mark_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.interested,
    )

    assert service.remove_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.interested,
    )
    assert service.remove_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.interested,
    )
    assert relationship_count(session) == 0


def test_mark_save_creates_relationship_and_is_idempotent(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Saved")
    service = EventRelationshipService(session)

    first = service.mark_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.saved,
    )
    second = service.mark_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.saved,
    )

    assert first is not None
    assert second is not None
    assert first.id == second.id
    assert first.relationship_type == RelationshipType.saved
    assert relationship_count(session) == 1


def test_remove_save_is_idempotent(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Remove Save")
    service = EventRelationshipService(session)
    service.mark_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.saved,
    )

    assert service.remove_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.saved,
    )
    assert service.remove_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.saved,
    )
    assert relationship_count(session) == 0


def test_non_public_events_are_not_actionable(session: Session) -> None:
    user = create_user(session)
    hidden = create_event(session, "Hidden", visibility=EventVisibility.hidden)
    restricted = create_event(session, "Restricted", visibility=EventVisibility.restricted)
    shadow_hidden = create_event(session, "Shadow", visibility=EventVisibility.shadow_hidden)
    removed = create_event(session, "Removed", status=EventStatus.removed)
    investigated = create_event(session, "Investigated", status=EventStatus.under_investigation)
    service = EventRelationshipService(session)

    for event in [hidden, restricted, shadow_hidden, removed, investigated]:
        relationship = service.mark_relationship(
            user_id=user.id,
            event_id=event.id,
            relationship_type=RelationshipType.saved,
        )
        assert relationship is None
        assert not service.remove_relationship(
            user_id=user.id,
            event_id=event.id,
            relationship_type=RelationshipType.saved,
        )

    assert relationship_count(session) == 0


def test_list_interested_events_for_user(session: Session) -> None:
    user = create_user(session)
    other_user = create_user(session, "other2@example.com")
    interested = create_event(session, "Interested Public")
    other_interested = create_event(session, "Other User Interested")
    service = EventRelationshipService(session)

    service.mark_relationship(
        user_id=user.id,
        event_id=interested.id,
        relationship_type=RelationshipType.interested,
    )
    service.mark_relationship(
        user_id=other_user.id,
        event_id=other_interested.id,
        relationship_type=RelationshipType.interested,
    )

    result = service.list_interested_events(user_id=user.id)

    assert [e.id for e in result] == [interested.id]


def test_list_going_events_for_user(session: Session) -> None:
    user = create_user(session)
    other_user = create_user(session, "other3@example.com")
    going = create_event(session, "Going Public")
    other_going = create_event(session, "Other User Going")
    service = EventRelationshipService(session)

    service.mark_relationship(
        user_id=user.id,
        event_id=going.id,
        relationship_type=RelationshipType.going,
    )
    service.mark_relationship(
        user_id=other_user.id,
        event_id=other_going.id,
        relationship_type=RelationshipType.going,
    )

    result = service.list_going_events(user_id=user.id)

    assert [e.id for e in result] == [going.id]


def test_list_saved_events_for_user_filters_visibility_and_other_users(session: Session) -> None:
    user = create_user(session)
    other_user = create_user(session, "other@example.com")
    public = create_event(session, "Public Saved")
    hidden = create_event(session, "Hidden Saved", visibility=EventVisibility.hidden)
    other_saved = create_event(session, "Other User Saved")
    service = EventRelationshipService(session)

    service.mark_relationship(
        user_id=user.id,
        event_id=public.id,
        relationship_type=RelationshipType.saved,
    )
    session.add(
        EventRelationship(
            user_id=user.id,
            event_id=hidden.id,
            relationship_type=RelationshipType.saved,
        )
    )
    service.mark_relationship(
        user_id=other_user.id,
        event_id=other_saved.id,
        relationship_type=RelationshipType.saved,
    )
    session.commit()

    saved = service.list_saved_events(user_id=user.id)

    assert [event.id for event in saved] == [public.id]
