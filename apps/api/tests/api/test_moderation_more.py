from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.usefixtures("moderator_auth")


@pytest.mark.asyncio
async def test_get_pending_events_with_filters(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/moderation/pending-events?location_name=Test&geocoding_status=verified"
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_published_events_with_filters(client: AsyncClient) -> None:
    response = await client.get("/api/v1/moderation/events?location_name=Test")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_venues_only_unverified(client: AsyncClient) -> None:
    response = await client.get("/api/v1/moderation/venues?only_unverified=true")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_merge_venues_not_found(client: AsyncClient) -> None:
    payload = {"source_venue_id": str(uuid4()), "target_venue_id": str(uuid4())}
    response = await client.post("/api/v1/moderation/venues/merge", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_batch_update_location(client: AsyncClient) -> None:
    payload = {
        "target_name": "Test Venue",
        "lat": 37.0,
        "lng": 23.0,
        "status": "verified",
        "confidence": 1.0,
        "metadata": {},
    }
    response = await client.post("/api/v1/moderation/batch-update-location", json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_add_occurrence_not_found(client: AsyncClient) -> None:
    payload = {"start_time": "2026-01-01T20:00:00Z"}
    response = await client.post(
        f"/api/v1/moderation/pending-events/{uuid4()}/occurrences", json=payload
    )
    assert response.status_code == 404
