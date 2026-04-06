from unittest.mock import patch

import pytest
from app.services.harvester.cleanser import CleansingService
from sqlmodel import Session


@pytest.mark.asyncio
async def test_clean_json_ld_location_string(session: Session) -> None:
    data = {
        "@type": "Event",
        "name": "Loc Test",
        "startDate": "2026-03-20T21:00:00Z",
        "location": "Technopolis, Athens",
    }
    with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            result = await CleansingService.clean_json_ld(data)
            assert result.location_name == "Technopolis, Athens"


@pytest.mark.asyncio
async def test_clean_json_ld_no_event_type() -> None:
    data = {"@type": "Person", "name": "John"}
    assert await CleansingService.clean_json_ld(data) is None


@pytest.mark.asyncio
async def test_clean_json_ld_complex_image(session: Session) -> None:
    data = {
        "@type": "Event",
        "name": "Image Test",
        "startDate": "2026-03-20T21:00:00Z",
        "image": [{"url": "https://example.com/1.jpg"}, "https://example.com/2.jpg"],
        "location": {"name": "Venue"},
    }
    with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
        with patch("app.repositories.venue_repository.Session", return_value=session):
            result = await CleansingService.clean_json_ld(data)
            # We STOP collecting images
            assert "image" not in result.event_metadata

