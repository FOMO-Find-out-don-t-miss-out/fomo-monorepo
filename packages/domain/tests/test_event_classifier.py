from typing import Any

import pytest

from packages.domain.services.event_classifier import EventClassifier


@pytest.mark.parametrize(
    "title, description, metadata, expected_category, expected_sub_category, expected_tags",
    [
        ("Techno Party", "Dance all night", {}, "Music", "Techno", ["Techno"]),
        ("Jazz Night", "Smooth jazz", {"@type": "MusicEvent"}, "Music", "Jazz", ["Jazz"]),
        ("Art Exhibition", "Contemporary art", {"@type": "ArtGallery"}, "Art", None, []),
        (
            "Theater Performance",
            "Shakespeare play",
            {"@type": "TheaterEvent"},
            "Art",
            "Theater",
            [],
        ),
        ("Generic Event", "Just a regular thing", {}, "Other", None, []),
        ("Concert", "No description", {}, "Music", None, []),
        ("Release Athens Festival", "Summer music festival", {}, "Music", None, ["Festival"]),
        ("Laiko live", "Night with laiko", {}, "Music", "Laiko", ["Laiko"]),
        ("Rebetiko evening", "Traditional music", {}, "Music", "Rebetiko", ["Rebetiko"]),
        ("Metal Gig", "Heavy metal", {}, "Music", "Metal", ["Metal"]),
        ("Rock concert", "Classic rock", {}, "Music", "Rock", ["Rock"]),
        ("Hip-Hop show", "Rap battle", {}, "Music", "Hip-Hop", ["Hip-Hop"]),
        ("DJ Set at the Beach", "Electronic vibes", {}, "Music", "Electronic", ["Electronic"]),
    ],
)
def test_event_classifier_classify(
    title: str,
    description: str,
    metadata: dict[str, Any],
    expected_category: str,
    expected_sub_category: str | None,
    expected_tags: list[str],
) -> None:
    """Tests the EventClassifier's ability to categorize events."""
    category, sub_category, tags = EventClassifier.classify(title, description, metadata)
    assert category == expected_category
    assert sub_category == expected_sub_category
    for tag in expected_tags:
        assert tag in tags


def test_event_classifier_organizer_hint() -> None:
    """Tests classification based on organizer metadata."""
    metadata = {"organizer": {"name": "Music Productions"}}
    category, _, _ = EventClassifier.classify("Event", "", metadata)
    assert category == "Music"


def test_event_classifier_source_domain_hint() -> None:
    """Tests classification based on source domain metadata."""
    metadata = {"source_domain": "more.com/music/"}
    category, _, _ = EventClassifier.classify("Event", "", metadata)
    assert category == "Music"


def test_event_classifier_greek_keywords() -> None:
    """Tests classification using Greek language keywords."""
    category, _, _ = EventClassifier.classify("Συναυλία στην Αθήνα", "", {})
    assert category == "Music"
    category, _, tags = EventClassifier.classify("Μεγάλο Φεστιβάλ", "", {})
    assert category == "Music"
    assert "Festival" in tags
