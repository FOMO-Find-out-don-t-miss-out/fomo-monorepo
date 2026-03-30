from datetime import UTC, datetime

from packages.domain.utils.datetime_utils import DateTimeHelper


def test_safe_parse_valid_iso():
    dt_str = "2026-03-20T21:00:00Z"
    result = DateTimeHelper.safe_parse(dt_str)
    assert result.year == 2026
    assert result.month == 3
    assert result.day == 20
    assert result.hour == 21
    assert result.tzinfo == UTC


def test_safe_parse_greek_markers():
    # 30/3/2026 9:00:00 μμ
    dt_str = "30/03/2026 09:00:00 μμ"
    result = DateTimeHelper.safe_parse(dt_str)
    assert result.day == 30
    assert result.month == 3
    assert result.year == 2026
    assert result.hour == 21  # 9 PM
    assert result.tzinfo == UTC


def test_safe_parse_list():
    dt_list = ["2026-03-20T21:00:00Z"]
    result = DateTimeHelper.safe_parse(dt_list)
    assert result.year == 2026


def test_safe_parse_invalid():
    # Should return default (now)
    result = DateTimeHelper.safe_parse("invalid date")
    assert isinstance(result, datetime)
    assert result.tzinfo == UTC


def test_normalize_greek_markers():
    assert DateTimeHelper.normalize_greek_markers("9:00 πμ") == "9:00 AM"
    assert DateTimeHelper.normalize_greek_markers("9:00 μμ") == "9:00 PM"
