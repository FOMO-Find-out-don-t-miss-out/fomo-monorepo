from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from app.core.geography_constants import DEFAULT_COUNTRY_CODE, get_country_config
from app.infrastructure.external.mapbox_client import MapboxClient, MapboxFeature, MapboxResponse
from app.services.harvester.location.geocoder import GeocoderService, GeocodingPolicy
from sqlmodel import Session, select

from packages.domain.models import PendingEvent, Venue


def test_enrich_query() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    assert (
        GeocodingPolicy.enrich_query("Block 33", config, "Thessaloniki") == "Block 33, Thessaloniki"
    )
    # City already in location name
    assert (
        GeocodingPolicy.enrich_query("Block 33 Thessaloniki", config, "Thessaloniki")
        == "Block 33 Thessaloniki"
    )
    assert GeocodingPolicy.enrich_query("Venue in Athens", config, "Athens") == "Venue in Athens"
    assert GeocodingPolicy.enrich_query("Only Venue", config, None) == "Only Venue"


def test_create_fuzzy_query() -> None:
    assert GeocodingPolicy.create_fuzzy_query("Venue Name Live 2024") == "Venue Name"
    assert GeocodingPolicy.create_fuzzy_query("Venue Name - Tickets") == "Venue Name"
    assert GeocodingPolicy.create_fuzzy_query("Venue @!# Name") == "Venue Name"
    assert GeocodingPolicy.create_fuzzy_query("Ab") == "Ab"  # Too short for fuzzy


def test_determine_status_poi() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)

    def make_feat(
        name: str,
        feature_type: str,
        relevance: float,
        country: str = DEFAULT_COUNTRY_CODE,
        city: str = "Athens",
    ) -> MapboxFeature:
        return MapboxFeature(
            id="poi.1",
            type="Feature",
            geometry={"type": "Point", "coordinates": [23.7, 37.9]},
            properties={
                "name": name,
                "feature_type": feature_type,
                "context": {
                    "country": {"country_code": country},
                    "place": {"name": city},
                },
            },
            relevance=relevance,
        )

    # High relevance POI
    feat = make_feat("Venue", "poi", 0.9)
    assert GeocodingPolicy.determine_status(feat, config, "Venue") == "verified"

    # Low relevance but good similarity
    feat = make_feat("Venue", "poi", 0.65)
    assert GeocodingPolicy.determine_status(feat, config, "Venue") == "verified"

    # Wrong country
    feat = make_feat("Venue", "poi", 1.0, country="DE")
    assert GeocodingPolicy.determine_status(feat, config, "Venue") == "failed"


def test_determine_status_address() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)

    def make_feat(name: str, feature_type: str, relevance: float) -> MapboxFeature:
        return MapboxFeature(
            id="1",
            type="Feature",
            geometry={"type": "Point", "coordinates": [23.7, 37.9]},
            properties={
                "name": name,
                "feature_type": feature_type,
                "full_address": name,
                "context": {"country": {"country_code": DEFAULT_COUNTRY_CODE}},
            },
            relevance=relevance,
        )

    feat = make_feat("Street 1", "address", 0.9)
    assert GeocodingPolicy.determine_status(feat, config, "Street 1") == "verified"

    feat = make_feat("Street 1", "address", 0.7)
    assert GeocodingPolicy.determine_status(feat, config, "Street 1") == "ambiguous"


def test_determine_status_place() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)

    def make_feat(
        name: str, feature_type: str, relevance: float, city: str = "Athens"
    ) -> MapboxFeature:
        return MapboxFeature(
            id="1",
            type="Feature",
            geometry={"type": "Point", "coordinates": [23.7, 37.9]},
            properties={
                "name": name,
                "feature_type": feature_type,
                "context": {
                    "country": {"country_code": DEFAULT_COUNTRY_CODE},
                    "place": {"name": city},
                },
            },
            relevance=relevance,
        )

    # Place match for a venue should be rejected
    feat = make_feat("Athens", "place", 1.0)
    assert GeocodingPolicy.determine_status(feat, config, "My Club") == "failed"

    # Good place match
    feat = make_feat("Athens", "place", 0.9)
    assert GeocodingPolicy.determine_status(feat, config, "Athens") == "verified"


@pytest.mark.asyncio
async def test_get_coordinates_cached(session: Session) -> None:
    # Pre-populate venue
    v = Venue(
        name="Cached Venue",
        country_code="GR",
        lat=37.9838,
        lng=23.7275,
        full_address="Athens, GR",
        relevance=1.0,
    )
    session.add(v)
    session.commit()

    with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
        with patch("app.services.harvester.location.geocoder.Session", return_value=session):
            result = await GeocoderService.get_coordinates("Cached Venue", DEFAULT_COUNTRY_CODE)
            assert result is not None
            assert result.lat == 37.9838


@pytest.mark.asyncio
async def test_get_coordinates_mapbox_success(session: Session) -> None:
    mock_feat = MapboxFeature(
        id="1",
        type="Feature",
        geometry={"type": "Point", "coordinates": [23.7275, 37.9838]},
        properties={
            "name": "Mapbox Venue",
            "feature_type": "poi",
            "context": {"country": {"country_code": "GR"}},
        },
        relevance=0.95,
    )
    mock_resp = MapboxResponse(type="FeatureCollection", features=[mock_feat])

    # Correct AsyncMock patch for class method that calls instance method
    with patch.object(MapboxClient, "search_box", new_callable=AsyncMock) as mock_sb:
        mock_sb.return_value = mock_resp
        with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
            with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
                # Ensure VenueRepository uses our session
                with patch(
                    "app.services.harvester.location.geocoder.Session", return_value=session
                ):
                    result = await GeocoderService.get_coordinates(
                        "Mapbox Venue", DEFAULT_COUNTRY_CODE
                    )

            assert result is not None
            assert result.lat == 37.9838
            assert result.geocoding_status == "verified"


@pytest.mark.asyncio
async def test_get_coordinates_fuzzy_fallback(session: Session) -> None:
    # 1. First call fails
    # 2. Fuzzy call succeeds
    mock_feat = MapboxFeature(
        id="1",
        type="Feature",
        geometry={"type": "Point", "coordinates": [23.7, 37.9]},
        properties={
            "name": "Real Venue",
            "feature_type": "poi",
            "context": {"country": {"country_code": "GR"}},
        },
        relevance=0.9,
    )
    mock_resp_success = MapboxResponse(type="FeatureCollection", features=[mock_feat])
    mock_resp_fail = MapboxResponse(type="FeatureCollection", features=[])

    async def side_effect(query: str, country_code: str, proximity: str) -> MapboxResponse | None:
        if "Live" in query:
            return mock_resp_fail
        return mock_resp_success

    with patch.object(MapboxClient, "search_box", side_effect=side_effect):
        with patch.object(MapboxClient, "geocode_v6", side_effect=side_effect):
            with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
                with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
                    with patch(
                        "app.services.harvester.location.geocoder.Session", return_value=session
                    ):
                        result = await GeocoderService.get_coordinates(
                            "Real Venue Live", DEFAULT_COUNTRY_CODE
                        )

                assert result is not None
                assert result.geocoding_status == "verified"


@pytest.mark.asyncio
async def test_get_coordinates_failed_all(session: Session) -> None:
    mock_resp = MapboxResponse(type="FeatureCollection", features=[])

    with patch.object(MapboxClient, "search_box", new_callable=AsyncMock) as mock_sb:
        with patch.object(MapboxClient, "geocode_v6", new_callable=AsyncMock) as mock_v6:
            mock_sb.return_value = mock_resp
            mock_v6.return_value = mock_resp
            with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
                with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
                    with patch(
                        "app.services.harvester.location.geocoder.Session", return_value=session
                    ):
                        result = await GeocoderService.get_coordinates(
                            "Unknown Place", DEFAULT_COUNTRY_CODE
                        )

                assert result is None


@pytest.mark.asyncio
async def test_batch_geocode_pending_events(session: Session) -> None:
    # Create a pending event that needs geocoding
    ev = PendingEvent(
        title="Event 1",
        location_name="V1",
        start_time=datetime.now(UTC),
        category="T",
        geocoding_status="failed",
    )
    ev2 = PendingEvent(
        title="Event 2",
        location_name="V2",
        start_time=datetime.now(UTC),
        category="T",
        geocoding_status="failed",
    )
    session.add(ev)
    session.add(ev2)
    session.commit()

    from app.services.harvester.location.geocoder import GeocodeResult

    mock_geo = GeocodeResult(
        lat=37.9,
        lng=23.7,
        relevance=1.0,
        full_address="A",
        country_code="GR",
        geocoding_status="verified",
    )

    async def side_effect(loc: str, country: str, **kwargs: Any) -> GeocodeResult | None:
        if loc == "V1":
            return mock_geo
        return None

    with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
        with patch.object(
            GeocoderService, "get_coordinates", new_callable=AsyncMock, side_effect=side_effect
        ):
            # Also patch Session in batch_geocode_pending_events
            with patch("app.services.harvester.location.geocoder.Session", return_value=session):
                stats = await GeocoderService.batch_geocode_pending_events(batch_size=10)
                assert stats["updated"] == 1
                assert stats["failed"] == 1


@pytest.mark.asyncio
async def test_batch_geocode_skipped(session: Session) -> None:
    ev = PendingEvent(
        title="No Loc",
        location_name=None,
        start_time=datetime.now(UTC),
        category="T",
        geocoding_status="failed",
    )
    session.add(ev)
    session.commit()

    with patch("app.services.harvester.location.geocoder.Session", return_value=session):
        stats = await GeocoderService.batch_geocode_pending_events(batch_size=10)
        assert stats["skipped"] == 1


@pytest.mark.asyncio
async def test_purge_cache(session: Session) -> None:
    v = Venue(name="V1", country_code="GR", lat=0, lng=0, full_address="A", relevance=1.0)
    session.add(v)
    session.commit()

    with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
        with patch("app.services.harvester.location.geocoder.Session", return_value=session):
            GeocoderService.purge_cache(venue_name="V1")
            assert session.exec(select(Venue).where(Venue.name == "V1")).first() is None


@pytest.mark.asyncio
async def test_purge_cache_db_fail() -> None:
    with patch(
        "app.services.harvester.location.geocoder.Session", side_effect=Exception("DB Fail")
    ):
        res = GeocoderService.purge_cache()
        assert "error" in res


@pytest.mark.asyncio
async def test_get_suggestions_success() -> None:
    # Use real MapboxFeature objects to satisfy Pydantic validation
    mock_feat = MapboxFeature(
        id="1",
        type="Feature",
        geometry={"type": "Point", "coordinates": [23.7, 37.9]},
        properties={"name": "Venue", "full_address": "Addr", "context": {}},
        relevance=0.9,
    )
    mock_resp = MapboxResponse(type="FeatureCollection", features=[mock_feat])

    with patch.object(MapboxClient, "search_box", new_callable=AsyncMock) as mock_sb:
        mock_sb.return_value = mock_resp
        with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
            results = await GeocoderService.get_suggestions("Venue", DEFAULT_COUNTRY_CODE)
            assert len(results) == 1
            assert results[0].lat == 37.9


@pytest.mark.asyncio
async def test_get_suggestions_v6_fallback() -> None:
    mock_feat = MapboxFeature(
        id="1",
        type="Feature",
        geometry={"type": "Point", "coordinates": [23.7, 37.9]},
        properties={"name": "Venue", "full_address": "V6 Suggestion", "context": {}},
        relevance=0.9,
    )
    mock_resp = MapboxResponse(type="FeatureCollection", features=[mock_feat])

    with patch.object(MapboxClient, "search_box", new_callable=AsyncMock) as mock_sb:
        mock_sb.return_value = None
        with patch.object(MapboxClient, "geocode_v6", new_callable=AsyncMock) as mock_geo:
            mock_geo.return_value = mock_resp
            with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
                results = await GeocoderService.get_suggestions("Venue", DEFAULT_COUNTRY_CODE)
                assert len(results) == 1
                assert results[0].full_address == "V6 Suggestion"


@pytest.mark.asyncio
async def test_get_suggestions_empty() -> None:
    with patch.object(
        MapboxClient,
        "search_box",
        new_callable=AsyncMock,
        return_value=MapboxResponse(type="FeatureCollection", features=[]),
    ):
        assert await GeocoderService.get_suggestions("", DEFAULT_COUNTRY_CODE) == []


def test_determine_status_potential_venue_mismatch() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    feat = MapboxFeature(
        id="1",
        type="Feature",
        geometry={"type": "Point", "coordinates": [23.7, 37.9]},
        properties={
            "name": "The Street",
            "feature_type": "street",
            "context": {"country": {"country_code": "GR"}},
        },
        relevance=1.0,
    )
    # query includes 'Club' indicator, but name is just 'The Street'
    feat.properties["name"] = "The Street"
    assert GeocodingPolicy.determine_status(feat, config, "The Great Club") == "failed"


def test_determine_status_rejected_city_match() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    feat = MapboxFeature(
        id="1",
        type="Feature",
        geometry={"type": "Point", "coordinates": [23.7, 37.9]},
        properties={
            "name": "The Stage",
            "feature_type": "poi",
            "context": {
                "country": {"country_code": "GR"},
                "place": {"name": "Thessaloniki"},
            },
        },
        relevance=0.9,
    )
    # Distance is small (< 20km from Athens), so it should be verified even if label is different
    assert (
        GeocodingPolicy.determine_status(feat, config, "The Stage", city_hint="Athens")
        == "verified"
    )


@pytest.mark.asyncio
async def test_get_coordinates_failed_all_with_fuzzy(session: Session) -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    with patch("app.services.harvester.location.geocoder.get_country_config", return_value=config):
        with patch(
            "app.repositories.venue_repository.VenueRepository.get_by_name", return_value=None
        ):
            with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):

                async def side_effect(
                    query: str, country_code: str, proximity: str, **kwargs: Any
                ) -> MapboxResponse | None:
                    return MapboxResponse(type="FeatureCollection", features=[])

                with patch.object(MapboxClient, "search_box", side_effect=side_effect):
                    with patch.object(MapboxClient, "geocode_v6", side_effect=side_effect):
                        with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", "fake"):
                            result = await GeocoderService.get_coordinates(
                                "Venue Live", DEFAULT_COUNTRY_CODE
                            )
                            assert result is None


def test_enrich_query_address_contains_name() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    # Case where address contains name
    assert (
        GeocodingPolicy.enrich_query("Venue", config, source_address="Venue Street 1")
        == "Venue Street 1"
    )


def test_enrich_query_address_no_name() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    # Case where it doesn't
    assert (
        GeocodingPolicy.enrich_query("Venue", config, source_address="Street 1")
        == "Venue, Street 1"
    )


def test_determine_status_wrong_bbox() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    feat = MapboxFeature(
        id="1",
        type="Feature",
        geometry={"type": "Point", "coordinates": [0, 0]},  # Way outside Greece
        properties={
            "name": "V",
            "context": {"country": {"country_code": "GR"}},
        },
        relevance=1.0,
    )
    assert GeocodingPolicy.determine_status(feat, config, "Venue") == "failed"


def test_determine_status_poi_token_match() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    feat = MapboxFeature(
        id="1",
        type="Feature",
        geometry={"type": "Point", "coordinates": [23.7, 37.9]},
        properties={
            "name": "My Great Venue",
            "feature_type": "address",
            "full_address": "Street 10, Athens",
            "context": {"country": {"country_code": "GR"}},
        },
        relevance=0.9,
    )
    # Very different addresses
    assert (
        GeocodingPolicy.determine_status(feat, config, "Venue", source_address="Source Road 99")
        == "ambiguous"
    )


def test_determine_status_city_distance_match() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    feat = MapboxFeature(
        id="1",
        type="Feature",
        geometry={"type": "Point", "coordinates": [23.64, 37.94]},  # Piraeus
        properties={
            "name": "Venue",
            "feature_type": "poi",
            "context": {
                "country": {"country_code": "GR"},
                "place": {"name": "Piraeus"},
            },
        },
        relevance=0.9,
    )
    # City hint is Athens, result is Piraeus, but distance is < 20km
    assert GeocodingPolicy.determine_status(feat, config, "Venue", city_hint="Athens") == "verified"


def test_determine_status_city_distance_mismatch() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    feat = MapboxFeature(
        id="1",
        type="Feature",
        geometry={"type": "Point", "coordinates": [22.94, 40.64]},  # Thessaloniki
        properties={
            "name": "Venue",
            "feature_type": "poi",
            "context": {
                "country": {"country_code": "GR"},
                "place": {"name": "Thessaloniki"},
            },
        },
        relevance=0.9,
    )
    # City hint is Athens, result is Thessaloniki, distance > 20km
    assert (
        GeocodingPolicy.determine_status(feat, config, "Venue", city_hint="Athens") == "ambiguous"
    )


@pytest.mark.asyncio
async def test_get_coordinates_no_token() -> None:
    with patch("app.services.harvester.location.geocoder.Session"):
        with patch(
            "app.repositories.venue_repository.VenueRepository.get_by_name", return_value=None
        ):
            with patch("app.core.config.settings.MAPBOX_ACCESS_TOKEN", None):
                result = await GeocoderService.get_coordinates("Venue", DEFAULT_COUNTRY_CODE)
                assert result is None


@pytest.mark.asyncio
async def test_purge_cache_all(session: Session) -> None:
    v = Venue(name="V1", country_code="GR", lat=0, lng=0, full_address="A", relevance=1.0)
    session.add(v)
    session.commit()

    with patch("app.services.harvester.location.geocoder.engine", session.get_bind()):
        with patch("app.services.harvester.location.geocoder.Session", return_value=session):
            # Purge all (no venue_name)
            GeocoderService.purge_cache()
            assert session.exec(select(Venue)).all() == []


@pytest.mark.asyncio
async def test_batch_geocode_no_loc(session: Session) -> None:
    ev = PendingEvent(
        title="No Loc",
        location_name=None,
        start_time=datetime.now(UTC),
        category="T",
        geocoding_status="failed",
    )
    session.add(ev)
    session.commit()

    with patch("app.services.harvester.location.geocoder.Session", return_value=session):
        stats = await GeocoderService.batch_geocode_pending_events(batch_size=10)
        assert stats["skipped"] == 1


@pytest.mark.asyncio
async def test_try_geocode_empty_features() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    mock_resp = MapboxResponse(type="FeatureCollection", features=[])
    with patch.object(MapboxClient, "search_box", new_callable=AsyncMock) as mock_sb:
        mock_sb.return_value = mock_resp
        res = await GeocoderService._try_geocode("Query", config, "Orig", "Athens", None)
        assert res is None


def test_extract_city() -> None:
    config = get_country_config(DEFAULT_COUNTRY_CODE)
    # Both Athens and Thessaloniki in query - should pick the first found in city_keywords order
    assert GeocoderService._extract_city("Athens Thessaloniki", config) in [
        "athens",
        "thessaloniki",
    ]
