from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_reject_event_not_found(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/moderation/pending-events/{uuid4()}/reject")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_pending_event_not_found(client: AsyncClient) -> None:
    response = await client.patch(
        f"/api/v1/moderation/pending-events/{uuid4()}", json={"title": "New"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_approve_event_not_found(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/moderation/pending-events/{uuid4()}/approve")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_publish_event_not_found(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/moderation/events/{uuid4()}/publish")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unpublish_event_not_found(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/moderation/events/{uuid4()}/unpublish")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_published_event_not_found(client: AsyncClient) -> None:
    response = await client.patch(f"/api/v1/moderation/events/{uuid4()}", json={"title": "New"})
    assert response.status_code == 404
