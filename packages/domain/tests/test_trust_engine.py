from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from packages.domain.schemas.extracted_event import ExtractedEvent
from packages.domain.services.trust_engine import TrustEngine


@pytest.fixture
def gr_trust_engine() -> TrustEngine:
    return TrustEngine(country_code="GR")


@pytest.fixture
def cy_trust_engine() -> TrustEngine:
    return TrustEngine(country_code="CY")


def test_gr_city_centers(gr_trust_engine: TrustEngine) -> None:
    assert "athens" in gr_trust_engine.city_centers
    assert gr_trust_engine.city_centers["athens"] == (37.9838, 23.7275)
    assert "nicosia" not in gr_trust_engine.city_centers


def test_cy_city_centers(cy_trust_engine: TrustEngine) -> None:
    assert "nicosia" in cy_trust_engine.city_centers
    assert cy_trust_engine.city_centers["nicosia"] == (35.1856, 33.3823)
    assert "athens" not in cy_trust_engine.city_centers


def test_config_fallback_to_gr() -> None:
    # Use a non-existent country code
    engine = TrustEngine(country_code="ZZ")
    assert engine.country_code == "ZZ"
    assert "athens" in engine.city_centers  # Fell back to GR


def test_load_config_exception() -> None:
    with patch("yaml.safe_load", side_effect=Exception("YAML Error")):
        engine = TrustEngine(country_code="GR")
        assert engine.city_centers == {}
        assert engine.junk_keywords == []


def test_is_junk_category(gr_trust_engine: TrustEngine) -> None:
    event = ExtractedEvent(
        title="Regular Title",
        description="Check this out",
        start_time=datetime.now(UTC) + timedelta(days=1),
        location_name="Some Place",
        country_code="GR",
        category="Junk",
        ingestion_method="json_ld",
    )
    assert gr_trust_engine.is_junk(event) is True


def test_is_junk_keywords(gr_trust_engine: TrustEngine) -> None:
    event = ExtractedEvent(
        title="Προσφορά για εισιτήρια",
        description="Check this out",
        start_time=datetime.now(UTC) + timedelta(days=1),
        location_name="Some Place",
        country_code="GR",
        category="Music",
        ingestion_method="json_ld",
    )
    assert gr_trust_engine.is_junk(event) is True


def test_is_not_junk(gr_trust_engine: TrustEngine) -> None:
    event = ExtractedEvent(
        title="Συναυλία στην Αθήνα",
        description="Great concert",
        start_time=datetime.now(UTC) + timedelta(days=1),
        location_name="Technopolis",
        country_code="GR",
        category="Music",
        ingestion_method="json_ld",
    )
    assert gr_trust_engine.is_junk(event) is False


def test_is_trusted_source_gate(gr_trust_engine: TrustEngine) -> None:
    event = ExtractedEvent(
        title="Syntagma Event",
        description="Great event",
        start_time=datetime.now(UTC) + timedelta(days=1),
        location_name="Syntagma",
        lat=37.9755,
        lng=23.7348,
        country_code="GR",
        category="Culture",
        ingestion_method="manual",  # Not json_ld
    )
    assert gr_trust_engine.is_trusted_for_autopublish(event) is False


def test_is_trusted_geocoding_gate(gr_trust_engine: TrustEngine) -> None:
    event = ExtractedEvent(
        title="Syntagma Event",
        description="Great event",
        start_time=datetime.now(UTC) + timedelta(days=1),
        location_name="Syntagma",
        lat=37.9755,
        lng=23.7348,
        country_code="GR",
        category="Culture",
        ingestion_method="json_ld",
        geocoding_status="pending",  # Not verified
    )
    assert gr_trust_engine.is_trusted_for_autopublish(event) is False


def test_is_trusted_confidence_gate(gr_trust_engine: TrustEngine) -> None:
    event = ExtractedEvent(
        title="Syntagma Event",
        description="Great event",
        start_time=datetime.now(UTC) + timedelta(days=1),
        location_name="Syntagma",
        lat=37.9755,
        lng=23.7348,
        country_code="GR",
        category="Culture",
        ingestion_method="json_ld",
        geocoding_status="verified",
        confidence_score=0.5,  # Too low
    )
    assert gr_trust_engine.is_trusted_for_autopublish(event) is False


def test_is_trusted_future_gate(gr_trust_engine: TrustEngine) -> None:
    event = ExtractedEvent(
        title="Syntagma Event",
        description="Great event",
        start_time=datetime.now(UTC) - timedelta(days=1),  # In the past
        location_name="Syntagma",
        lat=37.9755,
        lng=23.7348,
        country_code="GR",
        category="Culture",
        ingestion_method="json_ld",
        geocoding_status="verified",
        confidence_score=0.95,
    )
    assert gr_trust_engine.is_trusted_for_autopublish(event) is False


def test_is_trusted_distance_ok(gr_trust_engine: TrustEngine) -> None:
    # Athens center is (37.9838, 23.7275)
    # Syntagma is very close
    event = ExtractedEvent(
        title="Syntagma Event",
        description="Great event",
        start_time=datetime.now(UTC) + timedelta(days=1),
        location_name="Syntagma",
        lat=37.9755,
        lng=23.7348,
        country_code="GR",
        category="Culture",
        ingestion_method="json_ld",
        geocoding_status="verified",
        confidence_score=0.95,
        event_metadata={"city": "Athens"},
    )
    assert gr_trust_engine.is_trusted_for_autopublish(event) is True


def test_is_not_trusted_distance_fail(gr_trust_engine: TrustEngine) -> None:
    # Athens center is (37.9838, 23.7275)
    # Sunio is > 15km away (~60km)
    event = ExtractedEvent(
        title="Sunio Event",
        description="Too far",
        start_time=datetime.now(UTC) + timedelta(days=1),
        location_name="Sunio",
        lat=37.6500,
        lng=24.0200,
        country_code="GR",
        category="Culture",
        ingestion_method="json_ld",
        geocoding_status="verified",
        confidence_score=0.95,
        event_metadata={"city": "Athens"},
    )
    assert gr_trust_engine.is_trusted_for_autopublish(event) is False


def test_is_trusted_normalization_greek_cities(gr_trust_engine: TrustEngine) -> None:
    cities = [
        ("Αθήνα", 37.9838, 23.7275),
        ("Θεσσαλονίκη", 40.6401, 22.9444),
        ("Πάτρα", 38.2466, 21.7346),
        ("Ηράκλειο", 35.3387, 25.1442),
        ("Λάρισα", 39.639, 22.4191),
    ]
    for city_name, lat, lng in cities:
        event = ExtractedEvent(
            title=f"{city_name} Event",
            description="Testing normalization",
            start_time=datetime.now(UTC) + timedelta(days=1),
            location_name="Center",
            lat=lat,
            lng=lng,
            country_code="GR",
            category="Culture",
            ingestion_method="json_ld",
            geocoding_status="verified",
            confidence_score=0.95,
            event_metadata={"city": city_name},
        )
        assert gr_trust_engine.is_trusted_for_autopublish(event) is True


def test_cy_trusted_distance_ok(cy_trust_engine: TrustEngine) -> None:
    # Nicosia center is (35.1856, 33.3823)
    event = ExtractedEvent(
        title="Nicosia Event",
        description="Great event",
        start_time=datetime.now(UTC) + timedelta(days=1),
        location_name="Ledra Street",
        lat=35.1744,
        lng=33.3613,
        country_code="CY",
        category="Culture",
        ingestion_method="json_ld",
        geocoding_status="verified",
        confidence_score=0.95,
        event_metadata={"city": "Nicosia"},
    )
    assert cy_trust_engine.is_trusted_for_autopublish(event) is True


def test_cy_normalization_cities(cy_trust_engine: TrustEngine) -> None:
    cities = [
        ("Λευκωσία", 35.1856, 33.3823),
        ("Λεμεσός", 34.6786, 33.0413),
        ("Λάρνακα", 34.9175, 33.6300),
        ("Πάφος", 34.7721, 32.4231),
    ]
    for city_name, lat, lng in cities:
        event = ExtractedEvent(
            title=f"{city_name} Event",
            description="Testing normalization",
            start_time=datetime.now(UTC) + timedelta(days=1),
            location_name="Center",
            lat=lat,
            lng=lng,
            country_code="CY",
            category="Culture",
            ingestion_method="json_ld",
            geocoding_status="verified",
            confidence_score=0.95,
            event_metadata={"city": city_name},
        )
        assert cy_trust_engine.is_trusted_for_autopublish(event) is True


def test_is_trusted_no_city_hint(gr_trust_engine: TrustEngine) -> None:
    event = ExtractedEvent(
        title="No City Hint",
        description="Great event",
        start_time=datetime.now(UTC) + timedelta(days=1),
        location_name="Some Place",
        lat=37.9755,
        lng=23.7348,
        country_code="GR",
        category="Culture",
        ingestion_method="json_ld",
        geocoding_status="verified",
        confidence_score=0.95,
        event_metadata={},
    )
    # Should pass because no distance check is performed if no city hint
    assert gr_trust_engine.is_trusted_for_autopublish(event) is True
