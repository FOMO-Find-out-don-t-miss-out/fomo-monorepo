import pytest
import httpx
from unittest.mock import MagicMock, patch
from sqlmodel import Session, select
from app.models.venue import Venue
from app.services.harvester.geocoder import GeocoderService, GeocodeResult
from app.core.config import settings

@pytest.mark.asyncio
async def test_get_coordinates_cache_hit(session: Session):
    # Mock engine and Session in the module
    with patch("app.services.harvester.geocoder.engine", session.bind):
        # We need to mock the Session class used in _check_cache
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
            # Setup cache
            venue = Venue(
                name="Cached Venue",
                country_code="GR",
                lat=37.9838,
                lng=23.7275,
                full_address="Athens, Greece",
                relevance=1.0
            )
            session.add(venue)
            session.commit()
            
            result = await GeocoderService.get_coordinates("Cached Venue", "GR")
            assert result is not None
            assert result.lat == 37.9838
            assert result.lng == 23.7275

@pytest.mark.asyncio
async def test_get_coordinates_mapbox_success(session: Session, respx_mock):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
            # Mock Mapbox Search Box API (First Strategy)
            search_box_url = GeocoderService.SEARCH_BOX_URL
            mock_response = {
                "features": [{
                    "type": "Feature",
                    "id": "poi.123",
                    "geometry": {"coordinates": [23.7275, 37.9838]},
                    "properties": {
                        "name": "New Venue",
                        "full_address": "Athens, Central Athens, Greece",
                        "feature_type": "poi",
                        "context": {
                            "country": {"country_code": "GR"},
                            "place": {"name": "Athens"}
                        }
                    },
                    "relevance": 1.0
                }]
            }
            respx_mock.get(url__startswith=search_box_url).mock(return_value=httpx.Response(200, json=mock_response))
            
            with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake-token"):
                result = await GeocoderService.get_coordinates("New Venue", "GR")
                
            assert result is not None
            assert result.lat == 37.9838
            assert result.geocoding_status == "verified"
            
            # Verify cached in DB
            cached = session.exec(select(Venue).where(Venue.name == "New Venue")).first()
            assert cached is not None

@pytest.mark.asyncio
async def test_get_coordinates_fallback_to_v6(session: Session, respx_mock):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
            # Mock Search Box empty
            respx_mock.get(url__startswith=GeocoderService.SEARCH_BOX_URL).mock(
                return_value=httpx.Response(200, json={"features": []})
            )
            # Mock Geocoding v6 success
            mock_v6_response = {
                "features": [{
                    "geometry": {"coordinates": [23.7275, 37.9838]},
                    "properties": {
                        "full_address": "Street Name, Athens, Greece",
                        "feature_type": "address",
                        "context": {
                            "country": {"country_code": "GR"},
                            "place": {"name": "Athens"}
                        }
                    },
                    "relevance": 0.95
                }]
            }
            respx_mock.get(url__startswith=GeocoderService.BASE_URL).mock(
                return_value=httpx.Response(200, json=mock_v6_response)
            )
            
            with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake-token"):
                result = await GeocoderService.get_coordinates("Street Name", "GR")
                
            assert result is not None
            assert result.lat == 37.9838
            assert result.geocoding_status == "verified"

@pytest.mark.asyncio
async def test_get_coordinates_no_token(session):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
            with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", None):
                result = await GeocoderService.get_coordinates("Some Place")
                assert result is None

@pytest.mark.asyncio
async def test_get_coordinates_empty_response(session, respx_mock):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
            respx_mock.get(url__startswith=GeocoderService.BASE_URL).mock(
                return_value=httpx.Response(200, json={"features": []})
            )
            with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake-token"):
                result = await GeocoderService.get_coordinates("Non Existent Place")
                assert result is None

@pytest.mark.asyncio
async def test_get_coordinates_api_error(session, respx_mock):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
            respx_mock.get(url__startswith=GeocoderService.BASE_URL).mock(
                return_value=httpx.Response(500)
            )
            with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake-token"):
                result = await GeocoderService.get_coordinates("Fail Venue")
                assert result is None

def test_save_to_cache_exception():
    invalid_result = GeocodeResult(
        lat=0, lng=0, relevance=1.0, 
        full_address="Test", country_code="GR"
    )
    with patch("app.services.harvester.geocoder.Session", side_effect=Exception("DB Fail")):
        GeocoderService._save_to_cache("fail", invalid_result)
