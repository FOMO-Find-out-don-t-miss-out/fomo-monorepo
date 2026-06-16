import pytest

from packages.domain.services.category_normalizer import normalize_category


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, "Other"),
        ("", "Other"),
        ("   ", "Other"),
        ("Music", "Music"),
        ("music", "Music"),
        ("MUSIC", "Music"),
        ("Live Music", "Music"),
        ("live music", "Music"),
        ("Concert", "Music"),
        ("dj set", "Music"),
        ("Art", "Art"),
        ("arts", "Art"),
        ("Theatre", "Art"),
        ("Food & Drink", "Food"),
        ("food and drink", "Food"),
        ("Nightlife", "Nightlife"),
        ("club", "Nightlife"),
        ("Business", "Business"),
        ("Community", "Community"),
        ("Other", "Other"),
        ("Something Unrecognized", "Other"),
    ],
)
def test_normalize_category(raw: str | None, expected: str) -> None:
    assert normalize_category(raw) == expected


def test_normalize_category_preserves_junk_sentinel() -> None:
    """TrustEngine.is_junk() relies on the literal 'Junk' sentinel; it must not
    be coerced to 'Other' by the canonical mapping layer."""
    assert normalize_category("Junk") == "Junk"
