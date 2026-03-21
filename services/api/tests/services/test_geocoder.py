import pytest
import httpx
from unittest.mock import MagicMock, patch
from sqlmodel import Session, select
from app.models.venue import Venue
from app.models.event import PendingEvent
from app.services.harvester.geocoder import GeocoderService, GeocodeResult, _haversine_distance
from app.core.config import settings

@pytest.mark.asyncio
async def test_haversine_distance():
    # Test distance between Athens and Thessaloniki (~300km)
    dist = _haversine_distance(37.9838, 23.7275, 40.6401, 22.9444)
    assert 290 < dist < 310

def test_extract_city_from_query():
    assert GeocoderService._extract_city_from_query("Live in Thessaloniki at Block 33", "GR") == "thessaloniki"
    assert GeocoderService._extract_city_from_query("Event in Athens", "GR") == "athens"
    assert GeocoderService._extract_city_from_query("Random event", "GR") is None
    assert GeocoderService._extract_city_from_query(None, "GR") is None

def test_enrich_query():
    assert GeocoderService._enrich_query("Block 33", "GR", "Thessaloniki") == "Block 33, Thessaloniki"
    # City already in location name
    assert GeocoderService._enrich_query("Block 33 Thessaloniki", "GR", "Thessaloniki") == "Block 33 Thessaloniki"
    assert GeocoderService._enrich_query("Venue in Athens", "GR", "Athens") == "Venue in Athens"
    assert GeocoderService._enrich_query("Only Venue", "GR", None) == "Only Venue"

def test_create_fuzzy_query():
    assert GeocoderService._create_fuzzy_query("Venue Name Live 2024") == "Venue Name"
    assert GeocoderService._create_fuzzy_query("Venue Name - Tickets") == "Venue Name"
    assert GeocoderService._create_fuzzy_query("Venue @!# Name") == "Venue Name"
    assert GeocoderService._create_fuzzy_query("Ab") == "Ab" # Too short for fuzzy

def test_determine_status_poi():
    # High relevance POI
    assert GeocoderService._determine_status(0.9, "GR", "GR", "Venue", "poi") == "verified"
    # Low relevance but good similarity
    assert GeocoderService._determine_status(0.65, "GR", "GR", "Venue", "poi", name_similarity=0.7) == "verified"
    # Low relevance, low similarity
    assert GeocoderService._determine_status(0.5, "GR", "GR", "Venue", "poi", name_similarity=0.2) == "ambiguous"
    # Wrong country
    assert GeocoderService._determine_status(1.0, "DE", "GR", "Venue", "poi") == "failed"

def test_determine_status_address_street():
    assert GeocoderService._determine_status(0.9, "GR", "GR", "Street 1", "address") == "verified"
    assert GeocoderService._determine_status(0.7, "GR", "GR", "Street 1", "address") == "ambiguous"
    assert GeocoderService._determine_status(0.95, "GR", "GR", "Main Street", "street") == "verified"
    # Street match for a venue name should fail if similarity is low
    assert GeocoderService._determine_status(0.95, "GR", "GR", "Venue Club", "street", name_similarity=0.3) == "failed"

def test_determine_status_place():
    # Place match for a venue should be rejected
    assert GeocoderService._determine_status(1.0, "GR", "GR", "My Club", "place") == "failed"
    # Good place match
    assert GeocoderService._determine_status(0.9, "GR", "GR", "Athens", "place") == "verified"
    # City hint mismatch
    assert GeocoderService._determine_status(0.9, "GR", "GR", "Thessaloniki", "place", city_hint="Athens", city="Thessaloniki") == "failed"
    # City hint match with alias
    assert GeocoderService._determine_status(0.9, "GR", "GR", "Athina", "place", city_hint="Athens", city="Athina") == "verified"

@pytest.mark.asyncio
async def test_get_coordinates_cache_hit(session: Session):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
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

@pytest.mark.asyncio
async def test_get_coordinates_mapbox_success(session: Session, respx_mock):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
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

@pytest.mark.asyncio
async def test_get_coordinates_geofence_violation(session: Session, respx_mock):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
            mock_response = {
                "features": [{
                    "geometry": {"coordinates": [-74.0060, 40.7128]},
                    "properties": {
                        "name": "USA Venue",
                        "context": {"country": {"country_code": "GR"}} 
                    },
                    "relevance": 1.0
                }]
            }
            respx_mock.get(url__startswith=GeocoderService.SEARCH_BOX_URL).mock(return_value=httpx.Response(200, json=mock_response))
            respx_mock.get(url__startswith=GeocoderService.BASE_URL).mock(return_value=httpx.Response(200, json={"features": []}))
            
            with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
                result = await GeocoderService.get_coordinates("USA Venue", "GR")
                
                feat = mock_response["features"]
                res = GeocoderService._process_geocode_features(feat, "USA Venue", "GR", "USA Venue")
                assert res.geocoding_status == "failed"
                assert res.lat is None

@pytest.mark.asyncio
async def test_batch_geocode_pending_events(session: Session):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        p1 = PendingEvent(title="E1", location_name="V1", category="C", status="pending")
        p2 = PendingEvent(title="E2", location_name="Unknown", category="C", status="pending")
        session.add(p1)
        session.add(p2)
        session.commit()
        
        mock_geo = GeocodeResult(
            lat=1.0, lng=2.0, relevance=1.0, 
            full_address="Addr", country_code="GR", geocoding_status="verified"
        )
        
        async def side_effect(loc, country, **kwargs):
            if loc == "V1": return mock_geo
            return None

        with patch("app.services.harvester.geocoder.GeocoderService.get_coordinates", side_effect=side_effect):
            stats = await GeocoderService.batch_geocode_pending_events(batch_size=10)
            assert stats["updated"] == 1
            assert stats["failed"] == 1

@pytest.mark.asyncio
async def test_batch_geocode_skipped(session: Session):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        p1 = PendingEvent(title="EmptyLoc", location_name="", category="C", status="pending")
        session.add(p1)
        session.commit()
        
        stats = await GeocoderService.batch_geocode_pending_events(batch_size=10)
        assert stats["skipped"] == 1

@pytest.mark.asyncio
async def test_purge_cache(session: Session):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        v1 = Venue(name="V1", country_code="GR", lat=1, lng=1, full_address="A", relevance=1)
        session.add(v1)
        session.commit()
        
        GeocoderService.purge_cache(venue_name="V1")
        assert session.exec(select(Venue).where(Venue.name == "V1")).first() is None

def test_purge_cache_exception():
    with patch("app.services.harvester.geocoder.Session", side_effect=Exception("DB Fail")):
        res = GeocoderService.purge_cache()
        assert "error" in res

@pytest.mark.asyncio
async def test_get_suggestions(respx_mock):
    mock_response = {
        "features": [{
            "geometry": {"coordinates": [23.7, 37.9]},
            "properties": {
                "name": "Suggested Venue",
                "full_address": "Athens",
                "context": {"country": {"country_code": "GR"}}
            },
            "relevance": 0.9
        }]
    }
    respx_mock.get(url__startswith=GeocoderService.SEARCH_BOX_URL).mock(return_value=httpx.Response(200, json=mock_response))
    
    with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
        results = await GeocoderService.get_suggestions("Venue", "GR")
        assert len(results) == 1
        assert results[0].lat == 37.9

@pytest.mark.asyncio
async def test_get_suggestions_fallback_v6(respx_mock):
    respx_mock.get(url__startswith=GeocoderService.SEARCH_BOX_URL).mock(return_value=httpx.Response(200, json={"features": []}))
    mock_v6 = {
        "features": [{
            "geometry": {"coordinates": [23.7, 37.9]},
            "properties": {"name": "V6 Suggestion", "context": {"country": {"country_code": "GR"}}},
            "relevance": 0.8
        }]
    }
    respx_mock.get(url__startswith=GeocoderService.BASE_URL).mock(return_value=httpx.Response(200, json=mock_v6))
    
    with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
        results = await GeocoderService.get_suggestions("Venue", "GR")
        assert len(results) == 1
        assert results[0].full_address == "V6 Suggestion"

@pytest.mark.asyncio
async def test_get_suggestions_empty():
    assert await GeocoderService.get_suggestions("", "GR") == []
    with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", None):
        assert await GeocoderService.get_suggestions("query", "GR") == []

def test_process_single_feature_no_geometry():
    res = GeocoderService._process_single_feature({}, "query", "GR", "orig")
    assert res is None

@pytest.mark.asyncio
async def test_execute_geocode_error(respx_mock):
    respx_mock.get(url__startswith=GeocoderService.BASE_URL).mock(return_value=httpx.Response(500))
    with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
        res = await GeocoderService._execute_geocode("Query", "GR", "Orig")
        assert res is None

@pytest.mark.asyncio
async def test_execute_search_box_error(respx_mock):
    respx_mock.get(url__startswith=GeocoderService.SEARCH_BOX_URL).mock(return_value=httpx.Response(500))
    with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
        res = await GeocoderService._execute_search_box("Query", "GR", "Orig")
        assert res is None

@pytest.mark.asyncio
async def test_execute_geocode_empty_features(respx_mock):
    respx_mock.get(url__startswith=GeocoderService.BASE_URL).mock(return_value=httpx.Response(200, json={"features": []}))
    with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
        res = await GeocoderService._execute_geocode("Query", "GR", "Orig")
        assert res is None

@pytest.mark.asyncio
async def test_get_coordinates_fuzzy_fallback(session: Session, respx_mock):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
            
            def mapbox_side_effect(request):
                q = request.url.params.get("q", "")
                if "Live" in q:
                    return httpx.Response(200, json={"features": []})
                return httpx.Response(200, json={
                    "features": [{
                        "geometry": {"coordinates": [23.7, 37.9]},
                        "properties": {"name": "Venue", "context": {"country": {"country_code": "GR"}}},
                        "relevance": 1.0
                    }]
                })

            respx_mock.get(url__startswith=GeocoderService.SEARCH_BOX_URL).mock(side_effect=mapbox_side_effect)
            respx_mock.get(url__startswith=GeocoderService.BASE_URL).mock(return_value=httpx.Response(200, json={"features": []}))
            
            with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
                # Force _determine_status to return verified for the fuzzy result
                with patch("app.services.harvester.geocoder.GeocoderService._determine_status", return_value="verified"):
                    result = await GeocoderService.get_coordinates("Venue Live", "GR")
                    assert result is not None
                    assert result.lat == 37.9

@pytest.mark.asyncio
async def test_process_geocode_features_empty():
    assert GeocoderService._process_geocode_features([], "q", "GR", "orig") is None

def test_parse_relevance_variants():
    assert GeocoderService._parse_relevance("high") == 0.95
    assert GeocoderService._parse_relevance("medium") == 0.7
    assert GeocoderService._parse_relevance("low") == 0.4
    assert GeocoderService._parse_relevance("0.5") == 0.5
    assert GeocoderService._parse_relevance("invalid") == 0.0
    assert GeocoderService._parse_relevance(None) == 0.0

def test_determine_status_street_venue_indicator():
    # Line 682-685: rejected street match for potential venue
    assert GeocoderService._determine_status(0.95, "GR", "GR", "The Club", "street", name_similarity=0.3) == "failed"

def test_determine_status_place_venue_indicator():
    # Line 700-702: Rejected city match for potential venue
    assert GeocoderService._determine_status(0.95, "GR", "GR", "The Stage", "place") == "failed"

def test_determine_status_place_relevance_low():
    assert GeocoderService._determine_status(0.5, "GR", "GR", "Athens", "place") == "failed"

def test_determine_status_place_city_hint_mismatch():
    assert GeocoderService._determine_status(0.9, "GR", "GR", "Thessaloniki", "place", city_hint="Athens", city="Thessaloniki") == "failed"

def test_save_to_cache_exception():
    invalid_result = GeocodeResult(
        lat=0, lng=0, relevance=1.0, 
        full_address="Test", country_code="GR"
    )
    with patch("app.services.harvester.geocoder.Session", side_effect=Exception("DB Fail")):
        GeocoderService._save_to_cache("fail", invalid_result)
