"""API-level tests for /api/v1/me event relationship endpoints (FOMO-171)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.core.security.rbac import require_authenticated_user
from app.main import app
from httpx import AsyncClient
from sqlmodel import Session

from packages.domain.models import (
    Event,
    EventProvenance,
    EventRelationship,
    EventStatus,
    EventVisibility,
    RelationshipType,
    User,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event(
    session: Session,
    title: str = "Test Event",
    *,
    status: EventStatus = EventStatus.live,
    visibility: EventVisibility = EventVisibility.public,
) -> Event:
    event = Event(
        title=title,
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 6, 1, 20, 0, tzinfo=UTC),
        category="Music",
        status=status,
        visibility=visibility,
        provenance=EventProvenance.aggregated,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


# ---------------------------------------------------------------------------
# Fixtures: inject known authenticated user
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_user(session: Session) -> Generator[User, None, None]:
    uid = uuid4()
    user = User(external_id=str(uid), email=f"me-{uid}@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)
    app.dependency_overrides[require_authenticated_user] = lambda: user
    yield user
    app.dependency_overrides.pop(require_authenticated_user, None)


@pytest.fixture
def other_user(session: Session) -> User:
    uid = uuid4()
    user = User(external_id=str(uid), email=f"other-{uid}@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Unauthenticated: all endpoints reject requests without a valid token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_relationship_requires_auth(
    client: AsyncClient, auth_overrides: None, session: Session
) -> None:
    event = make_event(session)
    response = await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_relationship_requires_auth(
    client: AsyncClient, auth_overrides: None, session: Session
) -> None:
    event = make_event(session)
    response = await client.delete(f"/api/v1/me/events/{event.id}/relationships/saved")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_saved_events_requires_auth(
    client: AsyncClient, auth_overrides: None
) -> None:
    response = await client.get("/api/v1/me/saved-events")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_event_relationships_requires_auth(
    client: AsyncClient, auth_overrides: None
) -> None:
    response = await client.get("/api/v1/me/event-relationships")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PUT: mark relationships
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_saved_succeeds(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Saved Event")
    response = await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    assert response.status_code == 200
    data = response.json()
    assert data["relationship_type"] == "saved"
    assert data["event_id"] == str(event.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_put_interested_succeeds(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Interested Event")
    response = await client.put(f"/api/v1/me/events/{event.id}/relationships/interested")
    assert response.status_code == 200
    assert response.json()["relationship_type"] == "interested"


@pytest.mark.asyncio
async def test_put_going_succeeds(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Going Event")
    response = await client.put(f"/api/v1/me/events/{event.id}/relationships/going")
    assert response.status_code == 200
    assert response.json()["relationship_type"] == "going"


@pytest.mark.asyncio
async def test_put_is_idempotent(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Idempotent Event")
    r1 = await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    r2 = await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_put_unknown_event_returns_404(
    client: AsyncClient, auth_user: User
) -> None:
    response = await client.put(f"/api/v1/me/events/{uuid4()}/relationships/saved")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_put_non_public_event_returns_404(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Hidden Event", visibility=EventVisibility.hidden)
    response = await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_put_non_live_event_returns_404(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Removed Event", status=EventStatus.removed)
    response = await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_put_invalid_relationship_type_returns_422(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session)
    response = await client.put(f"/api/v1/me/events/{event.id}/relationships/invalid_type")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE: remove relationships
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_relationship_succeeds(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Delete Me")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    response = await client.delete(f"/api/v1/me/events/{event.id}/relationships/saved")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_is_idempotent(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Delete Idempotent")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    r1 = await client.delete(f"/api/v1/me/events/{event.id}/relationships/saved")
    r2 = await client.delete(f"/api/v1/me/events/{event.id}/relationships/saved")
    assert r1.status_code == 204
    assert r2.status_code == 204


@pytest.mark.asyncio
async def test_delete_non_public_event_returns_404(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Delete Hidden", visibility=EventVisibility.hidden)
    response = await client.delete(f"/api/v1/me/events/{event.id}/relationships/saved")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_unknown_event_returns_404(
    client: AsyncClient, auth_user: User
) -> None:
    response = await client.delete(f"/api/v1/me/events/{uuid4()}/relationships/saved")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /me/saved-events
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_saved_events_returns_current_user_saves(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "My Saved Event")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    response = await client.get("/api/v1/me/saved-events")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(event.id)


@pytest.mark.asyncio
async def test_saved_events_excludes_other_users(
    client: AsyncClient,
    auth_user: User,
    other_user: User,
    session: Session,
) -> None:
    event = make_event(session, "Other User Saved")
    session.add(
        EventRelationship(
            user_id=other_user.id,
            event_id=event.id,
            relationship_type=RelationshipType.saved,
        )
    )
    session.commit()
    response = await client.get("/api/v1/me/saved-events")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_saved_events_returns_empty_when_none(
    client: AsyncClient, auth_user: User
) -> None:
    response = await client.get("/api/v1/me/saved-events")
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /me/event-relationships (batch state)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_relationships_returns_correct_types(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Multi-Rel Event")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/interested")

    response = await client.get(f"/api/v1/me/event-relationships?event_ids={event.id}")
    assert response.status_code == 200
    data = response.json()
    assert set(data["relationships"][str(event.id)]) == {"saved", "interested"}


@pytest.mark.asyncio
async def test_event_relationships_supports_multiple_events(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event1 = make_event(session, "Batch Event 1")
    event2 = make_event(session, "Batch Event 2")
    await client.put(f"/api/v1/me/events/{event1.id}/relationships/saved")
    await client.put(f"/api/v1/me/events/{event2.id}/relationships/going")

    response = await client.get(
        f"/api/v1/me/event-relationships?event_ids={event1.id}&event_ids={event2.id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert "saved" in data["relationships"][str(event1.id)]
    assert "going" in data["relationships"][str(event2.id)]


@pytest.mark.asyncio
async def test_event_relationships_excludes_other_users(
    client: AsyncClient,
    auth_user: User,
    other_user: User,
    session: Session,
) -> None:
    event = make_event(session, "Other Saved")
    session.add(
        EventRelationship(
            user_id=other_user.id,
            event_id=event.id,
            relationship_type=RelationshipType.saved,
        )
    )
    session.commit()

    response = await client.get(f"/api/v1/me/event-relationships?event_ids={event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["relationships"].get(str(event.id), []) == []


@pytest.mark.asyncio
async def test_event_relationships_empty_when_no_ids(
    client: AsyncClient, auth_user: User
) -> None:
    response = await client.get("/api/v1/me/event-relationships")
    assert response.status_code == 200
    assert response.json() == {"relationships": {}}


# ---------------------------------------------------------------------------
# GET /me/events?relationship_type= (generic collection endpoint)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_my_events_requires_auth(client: AsyncClient, auth_overrides: None) -> None:
    response = await client.get("/api/v1/me/events?relationship_type=saved")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_my_events_invalid_type_returns_422(
    client: AsyncClient, auth_user: User
) -> None:
    response = await client.get("/api/v1/me/events?relationship_type=wishlist")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_my_events_saved_returns_saved_events(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "My Saved")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    response = await client.get("/api/v1/me/events?relationship_type=saved")
    assert response.status_code == 200
    ids = [e["id"] for e in response.json()]
    assert str(event.id) in ids


@pytest.mark.asyncio
async def test_my_events_interested_returns_interested_events(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "My Interested")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/interested")
    response = await client.get("/api/v1/me/events?relationship_type=interested")
    assert response.status_code == 200
    ids = [e["id"] for e in response.json()]
    assert str(event.id) in ids


@pytest.mark.asyncio
async def test_my_events_going_returns_going_events(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "My Going")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/going")
    response = await client.get("/api/v1/me/events?relationship_type=going")
    assert response.status_code == 200
    ids = [e["id"] for e in response.json()]
    assert str(event.id) in ids


@pytest.mark.asyncio
async def test_my_events_excludes_other_users(
    client: AsyncClient,
    auth_user: User,
    other_user: User,
    session: Session,
) -> None:
    event = make_event(session, "Other User Going")
    session.add(
        EventRelationship(
            user_id=other_user.id,
            event_id=event.id,
            relationship_type=RelationshipType.going,
        )
    )
    session.commit()
    response = await client.get("/api/v1/me/events?relationship_type=going")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_my_events_excludes_non_live_events(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    removed = make_event(session, "Removed Event", status=EventStatus.removed)
    session.add(
        EventRelationship(
            user_id=auth_user.id,
            event_id=removed.id,
            relationship_type=RelationshipType.saved,
        )
    )
    session.commit()
    response = await client.get("/api/v1/me/events?relationship_type=saved")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_my_events_different_types_do_not_bleed(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Only Saved")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    interested = await client.get("/api/v1/me/events?relationship_type=interested")
    going = await client.get("/api/v1/me/events?relationship_type=going")
    assert interested.json() == []
    assert going.json() == []


@pytest.mark.asyncio
async def test_saved_events_legacy_endpoint_still_works(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    """/me/saved-events must remain backward compatible."""
    event = make_event(session, "Legacy Saved")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    response = await client.get("/api/v1/me/saved-events")
    assert response.status_code == 200
    assert any(e["id"] == str(event.id) for e in response.json())


# ---------------------------------------------------------------------------
# Mutual exclusivity: interested ↔ going
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_interested_removes_going(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Exclusive Intent: Interested Wins")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/going")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/interested")
    response = await client.get(f"/api/v1/me/event-relationships?event_ids={event.id}")
    assert response.status_code == 200
    types = response.json()["relationships"][str(event.id)]
    assert "interested" in types
    assert "going" not in types


@pytest.mark.asyncio
async def test_put_going_removes_interested(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Exclusive Intent: Going Wins")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/interested")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/going")
    response = await client.get(f"/api/v1/me/event-relationships?event_ids={event.id}")
    assert response.status_code == 200
    types = response.json()["relationships"][str(event.id)]
    assert "going" in types
    assert "interested" not in types


@pytest.mark.asyncio
async def test_put_saved_does_not_remove_interested(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Save + Interested")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/interested")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    response = await client.get(f"/api/v1/me/event-relationships?event_ids={event.id}")
    assert response.status_code == 200
    types = set(response.json()["relationships"][str(event.id)])
    assert types == {"interested", "saved"}


@pytest.mark.asyncio
async def test_put_saved_does_not_remove_going(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Save + Going")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/going")
    await client.put(f"/api/v1/me/events/{event.id}/relationships/saved")
    response = await client.get(f"/api/v1/me/event-relationships?event_ids={event.id}")
    assert response.status_code == 200
    types = set(response.json()["relationships"][str(event.id)])
    assert types == {"going", "saved"}


@pytest.mark.asyncio
async def test_batch_state_never_returns_both_interested_and_going(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Legacy Both Batch")
    # Insert legacy rows directly, bypassing the service.
    session.add(
        EventRelationship(
            user_id=auth_user.id,
            event_id=event.id,
            relationship_type=RelationshipType.interested,
        )
    )
    session.add(
        EventRelationship(
            user_id=auth_user.id,
            event_id=event.id,
            relationship_type=RelationshipType.going,
        )
    )
    session.commit()

    response = await client.get(f"/api/v1/me/event-relationships?event_ids={event.id}")
    assert response.status_code == 200
    types = response.json()["relationships"][str(event.id)]
    assert not ("interested" in types and "going" in types), "must not return both"


@pytest.mark.asyncio
async def test_batch_state_going_wins_over_interested_for_legacy_data(
    client: AsyncClient, auth_user: User, session: Session
) -> None:
    event = make_event(session, "Legacy Going Wins Batch")
    session.add(
        EventRelationship(
            user_id=auth_user.id,
            event_id=event.id,
            relationship_type=RelationshipType.interested,
        )
    )
    session.add(
        EventRelationship(
            user_id=auth_user.id,
            event_id=event.id,
            relationship_type=RelationshipType.going,
        )
    )
    session.commit()

    response = await client.get(f"/api/v1/me/event-relationships?event_ids={event.id}")
    assert response.status_code == 200
    types = response.json()["relationships"][str(event.id)]
    assert "going" in types
    assert "interested" not in types
