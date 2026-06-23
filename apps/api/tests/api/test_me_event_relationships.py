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
    user = User(external_id=str(uuid4()), email="me@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)
    app.dependency_overrides[require_authenticated_user] = lambda: user
    yield user
    app.dependency_overrides.pop(require_authenticated_user, None)


@pytest.fixture
def other_user(session: Session) -> User:
    user = User(external_id=str(uuid4()), email="other@example.com")
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
