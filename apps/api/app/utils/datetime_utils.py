from datetime import UTC, datetime
from typing import ClassVar


class DateTimeHelper:
    """
    Utility class for robust date and time parsing across the monorepo.
    """

    COMMON_FORMATS: ClassVar[list[str]] = [
        "%d/%m/%Y %I:%M:%S %p",  # 30/3/2026 9:00:00 PM
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
    ]

    @staticmethod
    def normalize_greek_markers(date_str: str) -> str:
        """Translates Greek AM/PM markers to English for standard parsing."""
        return date_str.replace("πμ", "AM").replace("μμ", "PM")

    @classmethod
    def safe_parse(cls, value: object, default: datetime | None = None) -> datetime:
        """
        Attempts to parse a date value from various formats and types.
        Handles lists, Greek markers, and multiple string formats.
        """
        if default is None:
            default = datetime.now(UTC)

        # Handle lists (common in JSON-LD)
        if isinstance(value, list):
            value = value[0] if value else None

        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value

        if not value or not isinstance(value, str):
            return default

        clean_str = cls.normalize_greek_markers(value).strip()

        for fmt in cls.COMMON_FORMATS:
            try:
                dt = datetime.strptime(clean_str, fmt)
                # Ensure timezone awareness
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return dt
            except ValueError:
                continue

        return default
