from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from packages.domain.models import Event, PendingEvent


@pytest.mark.asyncio
async def test_update_published_event_success(client: AsyncClient, session: Session) -> None:
    # Create a live event
    event = Event(
        title="Live",
        start_time=datetime(2026, 1, 1, tzinfo=UTC),
        location_name="V",
        country_code="GR",
    )
    session.add(event)
    session.commit()
    session.refresh(event)

    response = await client.patch(
        f"/api/v1/moderation/events/{event.id}", json={"title": "Updated Live"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Live"


@pytest.mark.asyncio
async def test_approve_events_batch_success(client: AsyncClient, session: Session) -> None:
    p1 = PendingEvent(title="P1", start_time=datetime(2026, 1, 1, tzinfo=UTC), country_code="GR")
    p2 = PendingEvent(title="P2", start_time=datetime(2026, 1, 1, tzinfo=UTC), country_code="GR")
    session.add(p1)
    session.add(p2)
    session.commit()

    payload = {"event_ids": [str(p1.id), str(p2.id)]}
    response = await client.post("/api/v1/moderation/pending-events/approve-batch", json=payload)
    assert response.status_code == 200
    assert response.json()["approved_count"] == 2


@pytest.mark.asyncio
async def test_clean_json_ld_various_branches(session: Session) -> None:
    from app.services.harvester.cleanser import CleansingService

    # 1. Location as list
    data1 = {
        "@type": "Event",
        "name": "L1",
        "location": [{"name": "V1"}],
        "startDate": "2026-01-01",
    }
    # 2. Image as list of strings
    data2 = {
        "@type": "Event",
        "name": "I1",
        "image": ["https://img.com/1.jpg"],
        "location": {"name": "V2"},
        "startDate": "2026-01-01",
    }
    # 3. Geo coordinates in location
    data3 = {
        "@type": "Event",
        "name": "G1",
        "location": {"name": "V3", "geo": {"latitude": "37.5", "longitude": "23.5"}},
        "startDate": "2026-01-01",
    }
    # 4. Invalid geo
    data4 = {
        "@type": "Event",
        "name": "G2",
        "location": {"name": "V4", "geo": {"latitude": "invalid", "longitude": "23.5"}},
        "startDate": "2026-01-01",
    }

    with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            with patch(
                "app.services.harvester.location.geocoder.GeocoderService.get_coordinates",
                return_value=None,
            ):
                r1 = await CleansingService.clean_json_ld(data1)
                assert r1.location_name == "V1"

                r2 = await CleansingService.clean_json_ld(data2)
                # We STOP collecting images
                assert "image" not in r2.event_metadata
                r3 = await CleansingService.clean_json_ld(data3)
                assert r3.lat == 37.5

                r4 = await CleansingService.clean_json_ld(data4)
                assert r4.lat is None


@pytest.mark.asyncio
async def test_scraper_engine_ensure_string_list_non_str() -> None:
    from app.services.harvester.providers.more_com import MoreComProvider

    provider = MoreComProvider()
    html = (
        '<html><script type="application/ld+json">{"@type": "Event", '
        '"name": [null], "startDate": "2026"}</script></html>'
    )
    mock_resp = MagicMock(status_code=200, text=html)
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        result = await provider.fetch_event("http://test.com")
        assert result.title is None
