import pytest
from app.services.harvester.utils.text_sanitizer import TextSanitizer


@pytest.mark.parametrize(
    "input_title, expected_title",
    [
        ("CONCERT NAME | MORE.COM", "Concert Name"),
        ("LOWERCASE EVENT - VIVA.GR", "Lowercase Event"),
        ("Already Correct Title", "Already Correct Title"),
        ("MIXED case EVENT | TICKETMASTER", "Mixed Case Event"),
        ("Event &amp; More", "Event & More"),
        ("  Too   Many    Spaces  ", "Too Many Spaces"),
        ("Title with\ttabs and\nnewlines", "Title with tabs and newlines"),
        ("ΤΙΤΛΟΣ ΣΤΑ ΕΛΛΗΝΙΚΑ | MORE.COM", "Τιτλος Στα Ελληνικα"),
    ],
)
def test_clean_title(input_title: str, expected_title: str) -> None:
    assert TextSanitizer.clean_title(input_title) == expected_title


@pytest.mark.parametrize(
    "input_text, expected_text",
    [
        ("Double  space", "Double space"),
        ("Tab\tspace", "Tab space"),
        ("Newline\nspace", "Newline space"),
        ("Multiple\n\nnewlines and  spaces", "Multiple newlines and spaces"),
        ("  Leading and trailing  ", "Leading and trailing"),
    ],
)
def test_normalize_whitespace(input_text: str, expected_text: str) -> None:
    assert TextSanitizer.normalize_whitespace(input_text) == expected_text
