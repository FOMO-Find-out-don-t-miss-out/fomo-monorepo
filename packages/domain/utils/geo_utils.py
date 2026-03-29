import binascii
from typing import Any

from geoalchemy2.shape import to_shape
from shapely.wkb import loads as wkb_loads


def parse_wkb_to_geojson(location: Any) -> dict[str, Any] | None:  # noqa: ANN401
    """Parses a WKB location (either WKBElement or hex string) to GeoJSON Point."""
    if location is None:
        return None

    if isinstance(location, dict):
        return location

    try:
        # Try to_shape first (for WKBElement)
        shape = to_shape(location)
        return {"type": "Point", "coordinates": [shape.x, shape.y]}
    except Exception:
        try:
            # Try parsing as hex WKB string if it's a string
            if isinstance(location, str):
                shape = wkb_loads(binascii.unhexlify(location))
                return {"type": "Point", "coordinates": [shape.x, shape.y]}
            return None
        except Exception:
            return None
