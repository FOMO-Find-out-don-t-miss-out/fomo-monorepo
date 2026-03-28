import math
import re


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    using the Haversine formula.
    """
    R = 6371  # Earth's radius in kilometers
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def normalize_string(s: str, char_map: dict[str, str] | None = None) -> str:
    """
    Normalizes a string for comparison: lowercase, stripped,
    and applies an optional character mapping (e.g., for Greek-to-Latin).
    """
    if not s:
        return ""
    s = s.lower().strip()

    if char_map:
        s = "".join(char_map.get(char, char) for char in s)

    # Remove all non-alphanumeric except spaces
    return re.sub(r"[^a-z0-9\s]", "", s)
