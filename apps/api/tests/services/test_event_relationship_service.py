from datetime import UTC, datetime
from uuid import uuid4

from app.services.event_relationship_service import EventRelationshipService
from sqlmodel import Session, select

from packages.domain.models import (
    Event,
    EventProvenance,
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
    provenance: EventProvenance = EventProvenance.aggregated,
    visibility: EventVisibility = EventVisibility.public,
) -> Event:
    event = Event(
        title=title,
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 4, 1, 20, 0, tzinfo=UTC),
        category="Music",
        status=status,
        provenance=provenance,
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


# ---------------------------------------------------------------------------
# Mutual exclusivity: interested ↔ going
# ---------------------------------------------------------------------------


def _mark(
    service: EventRelationshipService, user: User, event: Event, rt: RelationshipType
) -> None:
    service.mark_relationship(user_id=user.id, event_id=event.id, relationship_type=rt)


def _remove(
    service: EventRelationshipService, user: User, event: Event, rt: RelationshipType
) -> None:
    service.remove_relationship(user_id=user.id, event_id=event.id, relationship_type=rt)


def _types(session: Session, user: User, event: Event) -> set[RelationshipType]:
    rows = session.exec(
        select(EventRelationship).where(
            EventRelationship.user_id == user.id,
            EventRelationship.event_id == event.id,
        )
    ).all()
    return {r.relationship_type for r in rows}


def test_mark_interested_removes_existing_going(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Exclusive Intent")
    service = EventRelationshipService(session)
    _mark(service, user, event, RelationshipType.going)
    _mark(service, user, event, RelationshipType.interested)
    assert _types(session, user, event) == {RelationshipType.interested}


def test_mark_going_removes_existing_interested(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Exclusive Intent 2")
    service = EventRelationshipService(session)
    _mark(service, user, event, RelationshipType.interested)
    _mark(service, user, event, RelationshipType.going)
    assert _types(session, user, event) == {RelationshipType.going}


def test_mark_saved_does_not_affect_interested(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Saved Independent")
    service = EventRelationshipService(session)
    _mark(service, user, event, RelationshipType.interested)
    _mark(service, user, event, RelationshipType.saved)
    types = _types(session, user, event)
    assert RelationshipType.interested in types
    assert RelationshipType.saved in types


def test_mark_saved_does_not_affect_going(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Saved Independent Going")
    service = EventRelationshipService(session)
    _mark(service, user, event, RelationshipType.going)
    _mark(service, user, event, RelationshipType.saved)
    types = _types(session, user, event)
    assert RelationshipType.going in types
    assert RelationshipType.saved in types


def test_saved_plus_interested_is_allowed(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Saved + Interested")
    service = EventRelationshipService(session)
    _mark(service, user, event, RelationshipType.saved)
    _mark(service, user, event, RelationshipType.interested)
    assert relationship_count(session) == 2


def test_saved_plus_going_is_allowed(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Saved + Going")
    service = EventRelationshipService(session)
    _mark(service, user, event, RelationshipType.saved)
    _mark(service, user, event, RelationshipType.going)
    assert relationship_count(session) == 2


def test_delete_going_does_not_restore_interested(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Delete Going")
    service = EventRelationshipService(session)
    # Mark interested then going (going removes interested); then remove going.
    _mark(service, user, event, RelationshipType.interested)
    _mark(service, user, event, RelationshipType.going)
    _remove(service, user, event, RelationshipType.going)
    assert relationship_count(session) == 0


def test_delete_interested_does_not_affect_saved(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Delete Interested Keeps Saved")
    service = EventRelationshipService(session)
    _mark(service, user, event, RelationshipType.saved)
    _mark(service, user, event, RelationshipType.interested)
    _remove(service, user, event, RelationshipType.interested)
    assert _types(session, user, event) == {RelationshipType.saved}


def test_delete_saved_does_not_affect_going(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Delete Saved Keeps Going")
    service = EventRelationshipService(session)
    _mark(service, user, event, RelationshipType.saved)
    _mark(service, user, event, RelationshipType.going)
    _remove(service, user, event, RelationshipType.saved)
    assert _types(session, user, event) == {RelationshipType.going}


def test_batch_state_normalizes_going_wins_over_interested_legacy(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Legacy Both")
    service = EventRelationshipService(session)
    # Simulate legacy data: insert both directly, bypassing the service.
    session.add(EventRelationship(
        user_id=user.id, event_id=event.id, relationship_type=RelationshipType.interested,
    ))
    session.add(EventRelationship(
        user_id=user.id, event_id=event.id, relationship_type=RelationshipType.going,
    ))
    session.commit()

    result = service.get_relationships_for_events(user_id=user.id, event_ids=[event.id])
    types = result.get(event.id, [])
    assert RelationshipType.going in types
    assert RelationshipType.interested not in types


# ---------------------------------------------------------------------------
# Legacy dual-row scenarios (both interested + going in DB simultaneously)
# These simulate data that existed before mutual exclusivity was enforced.
# ---------------------------------------------------------------------------


def _seed_both_intents(
    session: Session, user: User, event: Event
) -> None:
    """Insert both interested and going rows directly, bypassing the service."""
    session.add(
        EventRelationship(
            user_id=user.id,
            event_id=event.id,
            relationship_type=RelationshipType.interested,
        )
    )
    session.add(
        EventRelationship(
            user_id=user.id,
            event_id=event.id,
            relationship_type=RelationshipType.going,
        )
    )
    session.commit()


def test_mark_interested_when_both_rows_exist_removes_going(session: Session) -> None:
    """Legacy: both rows exist → mark interested → only interested remains."""
    user = create_user(session)
    event = create_event(session, "Legacy Both → Interested")
    _seed_both_intents(session, user, event)

    service = EventRelationshipService(session)
    result = service.mark_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.interested,
    )

    assert result is not None
    assert result.relationship_type == RelationshipType.interested
    assert _types(session, user, event) == {RelationshipType.interested}


def test_mark_going_when_both_rows_exist_removes_interested(session: Session) -> None:
    """Legacy: both rows exist → mark going → only going remains."""
    user = create_user(session)
    event = create_event(session, "Legacy Both → Going")
    _seed_both_intents(session, user, event)

    service = EventRelationshipService(session)
    result = service.mark_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.going,
    )

    assert result is not None
    assert result.relationship_type == RelationshipType.going
    assert _types(session, user, event) == {RelationshipType.going}


def test_mark_interested_when_going_already_exists_removes_going_and_keeps_interested(
    session: Session,
) -> None:
    """Legacy: interested already exists AND going exists → mark interested →
    going is deleted, existing interested row is returned (idempotent path)."""
    user = create_user(session)
    event = create_event(session, "Idempotent Legacy Both → Interested")
    _seed_both_intents(session, user, event)

    service = EventRelationshipService(session)
    # Calling mark_relationship with the already-existing type triggers the
    # early-return path. The conflict (going) must still be deleted.
    result = service.mark_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.interested,
    )

    assert result is not None
    rows = _types(session, user, event)
    assert rows == {RelationshipType.interested}, (
        f"Expected only interested, got {rows}. Going row was not cleaned up."
    )


def test_mark_going_when_interested_already_exists_removes_interested_and_keeps_going(
    session: Session,
) -> None:
    """Legacy: going already exists AND interested exists → mark going →
    interested is deleted, existing going row is returned (idempotent path)."""
    user = create_user(session)
    event = create_event(session, "Idempotent Legacy Both → Going")
    _seed_both_intents(session, user, event)

    service = EventRelationshipService(session)
    result = service.mark_relationship(
        user_id=user.id,
        event_id=event.id,
        relationship_type=RelationshipType.going,
    )

    assert result is not None
    rows = _types(session, user, event)
    assert rows == {RelationshipType.going}, (
        f"Expected only going, got {rows}. Interested row was not cleaned up."
    )


# ---------------------------------------------------------------------------
# List endpoint exclusivity: no event may appear in both interested and going
# ---------------------------------------------------------------------------


def test_list_interested_never_contains_events_in_going_list(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Interested Only")
    service = EventRelationshipService(session)
    _mark(service, user, event, RelationshipType.going)
    _mark(service, user, event, RelationshipType.interested)

    interested = service.list_interested_events(user_id=user.id)
    going = service.list_going_events(user_id=user.id)

    interested_ids = {e.id for e in interested}
    going_ids = {e.id for e in going}
    overlap = interested_ids & going_ids
    assert not overlap, f"Event(s) appeared in both lists: {overlap}"


def test_list_going_never_contains_events_in_interested_list(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Going Only")
    service = EventRelationshipService(session)
    _mark(service, user, event, RelationshipType.interested)
    _mark(service, user, event, RelationshipType.going)

    interested = service.list_interested_events(user_id=user.id)
    going = service.list_going_events(user_id=user.id)

    interested_ids = {e.id for e in interested}
    going_ids = {e.id for e in going}
    overlap = interested_ids & going_ids
    assert not overlap, f"Event(s) appeared in both lists: {overlap}"


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
