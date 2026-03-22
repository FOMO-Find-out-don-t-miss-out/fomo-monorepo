import pytest
from app.utils.geo_utils import haversine_distance, normalize_string
from app.core.geography_constants import GREEK_CHAR_MAP

def test_haversine_distance():
    # Athens to Thessaloniki (~300km)
    dist = haversine_distance(37.9838, 23.7275, 40.6401, 22.9444)
    assert 290 < dist < 310
    
    # Same point
    assert haversine_distance(37.9, 23.7, 37.9, 23.7) == 0

def test_normalize_string_basic():
    assert normalize_string("  Hello World  ") == "hello world"
    assert normalize_string("Athens 2024!") == "athens 2024"
    assert normalize_string("") == ""
    assert normalize_string(None) == ""

def test_normalize_string_with_map():
    char_map = {'ά': 'a', 'έ': 'e', 'ή': 'i'}
    assert normalize_string("άέή", char_map) == "aei"
    
    # Using real GREEK_CHAR_MAP
    assert normalize_string("Αθήνα", GREEK_CHAR_MAP) == "athina"
    assert normalize_string("Θεσσαλονίκη", GREEK_CHAR_MAP) == "thessaloniki"
