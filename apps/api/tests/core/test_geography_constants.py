from app.core.geography_constants import COUNTRY_DEFAULTS, DEFAULT_COUNTRY_CODE, get_country_config


def test_get_country_config_success():
    config = get_country_config("GR")
    assert config.code == "GR"
    assert config.name == "Greece"
    assert config.default_city == "Athens"
    assert config.char_map is not None  # Greek should have char_map


def test_get_country_config_fallback():
    # Should fallback to DEFAULT_COUNTRY_CODE (GR) if country not found
    config = get_country_config("ZZ")
    assert config.code == "ZZ"  # Code is kept from input
    assert config.name == COUNTRY_DEFAULTS[DEFAULT_COUNTRY_CODE]["name"]


def test_get_country_config_no_char_map():
    config = get_country_config("DE")
    assert config.code == "DE"
    assert config.char_map is None  # Germany shouldn't have Greek char_map
