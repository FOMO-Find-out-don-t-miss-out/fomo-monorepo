from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlmodel import Session


@pytest.mark.asyncio
async def test_merge_venues_endpoint(client: AsyncClient, session: Session) -> None:
    from uuid import uuid4

    from app.models.venue import Venue

    v1_id = uuid4()
    v2_id = uuid4()
    v1 = Venue(
        id=v1_id, name="V1", country_code="GR", lat=1.0, lng=1.0, full_address="A", relevance=1.0
    )
    v2 = Venue(
        id=v2_id, name="V2", country_code="GR", lat=2.0, lng=2.0, full_address="B", relevance=1.0
    )
    session.add(v1)
    session.add(v2)
    session.commit()

    payload = {"source_venue_id": str(v1_id), "target_venue_id": str(v2_id)}
    response = await client.post("/api/v1/moderation/venues/merge", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify V1 is gone
    assert session.get(Venue, v1_id) is None


@pytest.mark.asyncio
async def test_merge_venues_not_found(client: AsyncClient) -> None:
    from uuid import uuid4

    payload = {"source_venue_id": str(uuid4()), "target_venue_id": str(uuid4())}
    response = await client.post("/api/v1/moderation/venues/merge", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_batch_update_location_endpoint(client: AsyncClient) -> None:
    payload = {
        "target_name": "My Venue",
        "lat": 38.0,
        "lng": 23.5,
        "status": "verified",
        "confidence": 1.0,
        "metadata": {"note": "manually set"},
    }
    # Mock the service to avoid side effects
    with patch(
        "app.services.moderation.moderation_service.ModerationService.batch_update_location_by_name"
    ) as mock_service:
        response = await client.post("/api/v1/moderation/batch-update-location", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert mock_service.called


@pytest.mark.asyncio
async def test_get_geocode_suggestions_endpoint(client: AsyncClient) -> None:
    # Mock Geocoder
    with patch(
        "app.services.harvester.geocoder.GeocoderService.get_suggestions", new_callable=AsyncMock
    ) as mock_suggest:
        mock_suggest.return_value = []
        response = await client.get("/api/v1/moderation/geocode/suggestions", params={"q": "test"})
        assert response.status_code == 200
        assert response.json() == []
