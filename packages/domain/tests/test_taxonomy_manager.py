import pytest

from packages.domain.services.taxonomy_manager import TaxonomyManager


@pytest.fixture
def taxonomy_manager() -> TaxonomyManager:
    return TaxonomyManager()


def test_taxonomy_manager_init(taxonomy_manager: TaxonomyManager) -> None:
    assert taxonomy_manager.data is not None
    assert "categories" in taxonomy_manager.data


def test_taxonomy_manager_find_match_music_sub_category(taxonomy_manager: TaxonomyManager) -> None:
    category, sub_category, tags = taxonomy_manager.find_match("Awesome Techno Party")
    assert category == "Music"
    assert sub_category == "Techno"
    assert "Techno" in tags


def test_taxonomy_manager_find_match_music_category_only(taxonomy_manager: TaxonomyManager) -> None:
    category, sub_category, _tags = taxonomy_manager.find_match("Great Live Concert")
    assert category == "Music"
    assert sub_category is None


def test_taxonomy_manager_find_match_arts(taxonomy_manager: TaxonomyManager) -> None:
    category, sub_category, _tags = taxonomy_manager.find_match("Theater Performance")
    assert category == "Arts"
    assert sub_category == "Theater"


def test_taxonomy_manager_find_match_tech(taxonomy_manager: TaxonomyManager) -> None:
    category, sub_category, _tags = taxonomy_manager.find_match("AI Workshop for Developers")
    assert category == "Tech"
    assert sub_category == "Workshop"


def test_taxonomy_manager_find_match_greek_keywords(taxonomy_manager: TaxonomyManager) -> None:
    category, sub_category, _tags = taxonomy_manager.find_match("Βραδιά με ρεμπέτικο")
    assert category == "Music"
    assert sub_category == "Rebetiko"


def test_taxonomy_manager_no_match(taxonomy_manager: TaxonomyManager) -> None:
    category, sub_category, tags = taxonomy_manager.find_match("Something completely unrelated")
    assert category == "Other"
    assert sub_category is None
    assert tags == []
