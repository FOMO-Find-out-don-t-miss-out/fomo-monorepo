import pytest
import httpx
from unittest.mock import MagicMock, patch
from sqlmodel import Session, select
from app.models.venue import Venue
from app.models.event import PendingEvent
from app.services.harvester.geocoder import GeocoderService, GeocodeResult, GeocodingPolicy
from app.core.geography_constants import DEFAULT_COUNTRY_CODE, get_country_config
from app.utils.geo_utils import haversine_distance
from app.core.config import settings
from app.infrastructure.external.mapbox_client import MapboxClient, MapboxResponse, MapboxFeature

@pytest.mark.asyncio
async def test_haversine_distance():
    # Test distance between Athens and Thessaloniki (~300km)
    dist = haversine_distance(37.9838, 23.7275, 40.6401, 22.9444)
    assert 290 < dist < 310

def test_extract_city():
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    assert GeocoderService._extract_city("Live in Thessaloniki at Block 33", config) == "thessaloniki"
    assert GeocoderService._extract_city("Event in Athens", config) == "athens"
    assert GeocoderService._extract_city("Random event", config) is None

def test_enrich_query():
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    assert GeocodingPolicy.enrich_query("Block 33", config, "Thessaloniki") == "Block 33, Thessaloniki"
    # City already in location name
    assert GeocodingPolicy.enrich_query("Block 33 Thessaloniki", config, "Thessaloniki") == "Block 33 Thessaloniki"
    assert GeocodingPolicy.enrich_query("Venue in Athens", config, "Athens") == "Venue in Athens"
    assert GeocodingPolicy.enrich_query("Only Venue", config, None) == "Only Venue"

def test_create_fuzzy_query():
    assert GeocodingPolicy.create_fuzzy_query("Venue Name Live 2024") == "Venue Name"
    assert GeocodingPolicy.create_fuzzy_query("Venue Name - Tickets") == "Venue Name"
    assert GeocodingPolicy.create_fuzzy_query("Venue @!# Name") == "Venue Name"
    assert GeocodingPolicy.create_fuzzy_query("Ab") == "Ab" # Too short for fuzzy

def test_determine_status_poi():
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    
    def make_feat(name, feature_type, relevance, country=DEFAULT_COUNTRY_CODE, city="Athens"):
        return MapboxFeature(
            id="poi.1", type="Feature", 
            geometry={"coordinates": [23.7, 37.9]},
            properties={
                "name": name, "feature_type": feature_type,
                "context": {"country": {"country_code": country}, "place": {"name": city}}
            },
            relevance=relevance
        )

    # High relevance POI
    feat = make_feat("Venue", "poi", 0.9)
    assert GeocodingPolicy.determine_status(feat, config, "Venue") == "verified"
    
    # Low relevance but good similarity (name_similarity is calculated internally in determine_status)
    feat = make_feat("Venue", "poi", 0.65)
    assert GeocodingPolicy.determine_status(feat, config, "Venue") == "verified"
    
    # Wrong country
    feat = make_feat("Venue", "poi", 1.0, country="DE")
    assert GeocodingPolicy.determine_status(feat, config, "Venue") == "failed"

def test_determine_status_address_street():
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    
    def make_feat(name, feature_type, relevance):
        return MapboxFeature(
            id="1", type="Feature", 
            geometry={"coordinates": [23.7, 37.9]},
            properties={
                "name": name, "feature_type": feature_type,
                "context": {"country": {"country_code": DEFAULT_COUNTRY_CODE}}
            },
            relevance=relevance
        )

    feat = make_feat("Street 1", "address", 0.9)
    assert GeocodingPolicy.determine_status(feat, config, "Street 1") == "verified"
    
    feat = make_feat("Street 1", "address", 0.7)
    assert GeocodingPolicy.determine_status(feat, config, "Street 1") == "ambiguous"

def test_determine_status_place():
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    
    def make_feat(name, feature_type, relevance, city="Athens"):
        return MapboxFeature(
            id="1", type="Feature", 
            geometry={"coordinates": [23.7, 37.9]},
            properties={
                "name": name, "feature_type": feature_type,
                "context": {"country": {"country_code": DEFAULT_COUNTRY_CODE}, "place": {"name": city}}
            },
            relevance=relevance
        )

    # Place match for a venue should be rejected
    feat = make_feat("Athens", "place", 1.0)
    assert GeocodingPolicy.determine_status(feat, config, "My Club") == "failed"
    
    # Good place match
    feat = make_feat("Athens", "place", 0.9)
    assert GeocodingPolicy.determine_status(feat, config, "Athens") == "verified"

@pytest.mark.asyncio
async def test_get_coordinates_cache_hit(session: Session):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
            venue = Venue(
                name="Cached Venue",
                country_code=DEFAULT_COUNTRY_CODE,
                lat=37.9838,
                lng=23.7275,
                full_address="Athens, Greece",
                relevance=1.0
            )
            session.add(venue)
            session.commit()
            
            result = await GeocoderService.get_coordinates("Cached Venue", DEFAULT_COUNTRY_CODE)
            assert result is not None
            assert result.lat == 37.9838

@pytest.mark.asyncio
async def test_get_coordinates_mapbox_success(session: Session):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
            mock_response = MapboxResponse(
                type="FeatureCollection",
                features=[MapboxFeature(
                    type="Feature",
                    id="poi.123",
                    geometry={"coordinates": [23.7275, 37.9838]},
                    properties={
                        "name": "New Venue",
                        "full_address": "Athens, Central Athens, Greece",
                        "feature_type": "poi",
                        "context": {
                            "country": {"country_code": DEFAULT_COUNTRY_CODE},
                            "place": {"name": "Athens"}
                        }
                    },
                    relevance=1.0
                )]
            )
            
            with patch.object(MapboxClient, "search_box", return_value=mock_response):
                with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake-token"):
                    result = await GeocoderService.get_coordinates("New Venue", DEFAULT_COUNTRY_CODE)
                
            assert result is not None
            assert result.lat == 37.9838
            assert result.geocoding_status == "verified"

@pytest.mark.asyncio
async def test_get_coordinates_geofence_violation(session: Session):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
            mock_response = MapboxResponse(
                type="FeatureCollection",
                features=[MapboxFeature(
                    type="Feature",
                    id="poi.456",
                    geometry={"coordinates": [-74.0060, 40.7128]},
                    properties={
                        "name": "USA Venue",
                        "context": {"country": {"country_code": DEFAULT_COUNTRY_CODE}} 
                    },
                    relevance=1.0
                )]
            )
            
            with patch.object(MapboxClient, "search_box", return_value=mock_response):
                with patch.object(MapboxClient, "geocode_v6", return_value=MapboxResponse(type="FeatureCollection", features=[])):
                    with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
                        result = await GeocoderService.get_coordinates("USA Venue", DEFAULT_COUNTRY_CODE)

            assert result is None

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
            full_address="Addr", country_code=DEFAULT_COUNTRY_CODE, geocoding_status="verified"
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
        v1 = Venue(name="V1", country_code=DEFAULT_COUNTRY_CODE, lat=1, lng=1, full_address="A", relevance=1)
        session.add(v1)
        session.commit()
        
        GeocoderService.purge_cache(venue_name="V1")
        assert session.exec(select(Venue).where(Venue.name == "V1")).first() is None

def test_purge_cache_exception():
    with patch("app.services.harvester.geocoder.Session", side_effect=Exception("DB Fail")):
        res = GeocoderService.purge_cache()
        assert "error" in res

@pytest.mark.asyncio
async def test_get_suggestions():
    mock_response = MapboxResponse(
        type="FeatureCollection",
        features=[MapboxFeature(
            type="Feature",
            id="poi.789",
            geometry={"coordinates": [23.7, 37.9]},
            properties={
                "name": "Suggested Venue",
                "full_address": "Athens",
                "context": {"country": {"country_code": DEFAULT_COUNTRY_CODE}}
            },
            relevance=0.9
        )]
    )
    
    with patch.object(MapboxClient, "search_box", return_value=mock_response):
        with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
            results = await GeocoderService.get_suggestions("Venue", DEFAULT_COUNTRY_CODE)
            assert len(results) == 1
            assert results[0].lat == 37.9

@pytest.mark.asyncio
async def test_get_suggestions_fallback_v6():
    mock_v6 = MapboxResponse(
        type="FeatureCollection",
        features=[MapboxFeature(
            type="Feature",
            id="poi.012",
            geometry={"coordinates": [23.7, 37.9]},
            properties={"name": "V6 Suggestion", "context": {"country": {"country_code": DEFAULT_COUNTRY_CODE}}},
            relevance=0.8
        )]
    )
    
    with patch.object(MapboxClient, "search_box", return_value=MapboxResponse(type="FeatureCollection", features=[])):
        with patch.object(MapboxClient, "geocode_v6", return_value=mock_v6):
            with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
                results = await GeocoderService.get_suggestions("Venue", DEFAULT_COUNTRY_CODE)
                assert len(results) == 1
                assert results[0].full_address == "V6 Suggestion"

@pytest.mark.asyncio
async def test_get_suggestions_empty():
    with patch.object(MapboxClient, "search_box", return_value=MapboxResponse(type="FeatureCollection", features=[])):
        with patch.object(MapboxClient, "geocode_v6", return_value=MapboxResponse(type="FeatureCollection", features=[])):
            assert await GeocoderService.get_suggestions("", DEFAULT_COUNTRY_CODE) == []

def test_determine_status_street_venue_indicator():
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    feat = MapboxFeature(
        id="street.1", type="Feature", 
        geometry={"coordinates": [23.7, 37.9]},
        properties={
            "name": "The Club", "feature_type": "street",
            "context": {"country": {"country_code": DEFAULT_COUNTRY_CODE}}
        },
        relevance=0.95
    )
    # rejected street match for potential venue (name_similarity will be low internally)
    # query includes 'Club' indicator, but name is just 'The Street'
    feat.properties["name"] = "The Street"
    assert GeocodingPolicy.determine_status(feat, config, "The Great Club") == "failed"

def test_determine_status_place_venue_indicator():
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    feat = MapboxFeature(
        id="place.1", type="Feature", 
        geometry={"coordinates": [23.7, 37.9]},
        properties={
            "name": "Athens", "feature_type": "place",
            "context": {"country": {"country_code": DEFAULT_COUNTRY_CODE}}
        },
        relevance=0.95
    )
    # Rejected city match for potential venue
    assert GeocodingPolicy.determine_status(feat, config, "The Stage") == "failed"

@pytest.mark.asyncio
async def test_get_coordinates_fuzzy_fallback(session: Session):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        mock_session_obj = MagicMock()
        mock_session_obj.__enter__.return_value = session
        with patch("app.services.harvester.geocoder.Session", return_value=mock_session_obj):
            
            async def side_effect(query, country_code, proximity, **kwargs):
                if "Live" in query:
                    return MapboxResponse(type="FeatureCollection", features=[])
                return MapboxResponse(
                    type="FeatureCollection",
                    features=[MapboxFeature(
                        type="Feature",
                        id="poi.345",
                        geometry={"coordinates": [23.7, 37.9]},
                        properties={"name": "Venue", "context": {"country": {"country_code": DEFAULT_COUNTRY_CODE}}},
                        relevance=1.0
                    )]
                )

            with patch.object(MapboxClient, "search_box", side_effect=side_effect):
                with patch.object(MapboxClient, "geocode_v6", return_value=MapboxResponse(type="FeatureCollection", features=[])):
                    with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
                        # Force _determine_status to return verified for the fuzzy result
                        with patch("app.services.harvester.geocoder.GeocodingPolicy.determine_status", return_value="verified"):
                            result = await GeocoderService.get_coordinates("Venue Live", DEFAULT_COUNTRY_CODE)
                            assert result is not None
                            assert result.lat == 37.9

def test_geocoding_policy_enrich_source_address():
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    # Case where address contains name
    assert GeocodingPolicy.enrich_query("Venue", config, source_address="Venue Street 1") == "Venue Street 1"
    # Case where it doesn't
    assert GeocodingPolicy.enrich_query("Venue", config, source_address="Street 1") == "Venue, Street 1"

def test_geocoding_policy_determine_status_bbox_violation():
    config = get_country_config(DEFAULT_COUNTRY_CODE) # GR bbox: lat 34-42, lng 19-29
    feat = MapboxFeature(
        id="poi.1", type="Feature", 
        geometry={"coordinates": [0, 0]}, # Middle of ocean
        properties={"name": "Venue", "context": {"country": {"country_code": DEFAULT_COUNTRY_CODE}}},
        relevance=1.0
    )
    assert GeocodingPolicy.determine_status(feat, config, "Venue") == "failed"

def test_geocoding_policy_determine_status_address_guard_fail():
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    feat = MapboxFeature(
        id="poi.1", type="Feature", 
        geometry={"coordinates": [23.7, 37.9]},
        properties={
            "name": "Venue", "full_address": "Result Street 10",
            "context": {"country": {"country_code": DEFAULT_COUNTRY_CODE}}
        },
        relevance=0.8
    )
    # Very different addresses
    assert GeocodingPolicy.determine_status(feat, config, "Venue", source_address="Source Road 99") == "ambiguous"

def test_geocoding_policy_determine_status_city_mismatch_distance_ok():
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    # Athens coords: 37.9838, 23.7275
    feat = MapboxFeature(
        id="poi.1", type="Feature", 
        geometry={"coordinates": [23.73, 37.99]}, # Close to Athens
        properties={
            "name": "Venue", "feature_type": "poi",
            "context": {"country": {"country_code": DEFAULT_COUNTRY_CODE}, "place": {"name": "Piraeus"}}
        },
        relevance=0.9
    )
    # City hint is Athens, result is Piraeus, but distance is < 20km
    assert GeocodingPolicy.determine_status(feat, config, "Venue", city_hint="Athens") == "verified"

def test_geocoding_policy_determine_status_city_mismatch_distance_fail():
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    # Athens coords: 37.9838, 23.7275
    # Thessaloniki coords: 40.6401, 22.9444 (~300km away)
    feat = MapboxFeature(
        id="poi.1", type="Feature", 
        geometry={"coordinates": [22.94, 40.64]}, 
        properties={
            "name": "Venue", "context": {"country": {"country_code": DEFAULT_COUNTRY_CODE}, "place": {"name": "Thessaloniki"}}
        },
        relevance=0.9
    )
    # City hint is Athens, result is Thessaloniki, distance > 20km
    assert GeocodingPolicy.determine_status(feat, config, "Venue", city_hint="Athens") == "ambiguous"

@pytest.mark.asyncio
async def test_get_coordinates_no_token(session: Session):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", None):
            result = await GeocoderService.get_coordinates("Venue", DEFAULT_COUNTRY_CODE)
            assert result is None

@pytest.mark.asyncio
async def test_purge_cache_full(session: Session):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        v1 = Venue(name="V1", country_code=DEFAULT_COUNTRY_CODE, lat=1, lng=1, full_address="A", relevance=1)
        session.add(v1)
        session.commit()
        
        # Purge all (no venue_name)
        GeocoderService.purge_cache()
        assert session.exec(select(Venue)).all() == []

@pytest.mark.asyncio
async def test_batch_geocode_no_loc(session: Session):
    with patch("app.services.harvester.geocoder.engine", session.bind):
        p1 = PendingEvent(title="NoLoc", location_name=None, category="C", status="pending")
        session.add(p1)
        session.commit()
        stats = await GeocoderService.batch_geocode_pending_events(batch_size=10)
        assert stats["skipped"] == 1

@pytest.mark.asyncio
async def test_try_geocode_no_coords():
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    mock_resp = MapboxResponse(
        type="FeatureCollection",
        features=[MapboxFeature(
            id="1", type="Feature", geometry={}, # No coordinates
            properties={"name": "NoCoords"}, relevance=1.0
        )]
    )
    with patch.object(MapboxClient, "search_box", return_value=mock_resp):
        res = await GeocoderService._try_geocode("Query", config, "Orig", "Athens", None)
        assert res is None

def test_extract_city_multiple():
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    # Both Athens and Thessaloniki in query - should pick the first found in city_keywords order
    assert GeocoderService._extract_city("Athens Thessaloniki", config) in ["athens", "thessaloniki"]
