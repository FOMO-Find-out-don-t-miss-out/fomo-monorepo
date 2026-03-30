import logging
import math
from datetime import UTC, datetime
from typing import ClassVar

from packages.domain.schemas.extracted_event import ExtractedEvent

logger = logging.getLogger(__name__)


class TrustEngine:
    """Business logic for automated event validation, trust levels, and junk filtering."""

    # Default city centers for Athens, Thessaloniki, Patra, Heraklion, Larissa
    CITY_CENTERS: ClassVar[dict[str, tuple[float, float]]] = {
        "athens": (37.9838, 23.7275),
        "thessaloniki": (40.6401, 22.9444),
        "patra": (38.2466, 21.7346),
        "heraklion": (35.3387, 25.1442),
        "larissa": (39.639, 22.4191),
    }

    JUNK_KEYWORDS: ClassVar[list[str]] = [
        "προσφορές",
        "προσφορά",
        "εκδηλώσεις",
        "εισιτήρια",
        "tickets",
        "offers",
        "newsletter",
        "τριήμερο",
        "διήμερο",
    ]

    @staticmethod
    def is_junk(event_data: ExtractedEvent) -> bool:
        """Determines if an event is low-quality or junk based on keywords and AI category."""
        if event_data.category == "Junk":
            return True

        title_lower = event_data.title.lower()
        if (
            any(kw in title_lower for kw in TrustEngine.JUNK_KEYWORDS)
            and len(event_data.title) < 100
        ):
            return True

        return False

    @staticmethod
    def is_trusted_for_autopublish(event_data: ExtractedEvent) -> bool:
        """Gate logic for automated publishing."""
        # 1. Source Gate
        if event_data.ingestion_method != "json_ld":
            return False

        # 2. Geocoding Gate
        if event_data.geocoding_status != "verified" or (event_data.confidence_score or 0) < 0.9:
            return False

        # 3. Future Gate
        if event_data.start_time <= datetime.now(UTC):
            return False

        # 4. Distance Guard (15km radius check)
        city_hint = event_data.event_metadata.get("city") or event_data.event_metadata.get(
            "addressLocality"
        )
        if city_hint and isinstance(city_hint, str):
            city_hint_lower = city_hint.lower().strip()
            # Normalize common names
            if "αθήνα" in city_hint_lower or "athens" in city_hint_lower:
                city_key = "athens"
            elif "θεσσαλονίκη" in city_hint_lower or "thessaloniki" in city_hint_lower:
                city_key = "thessaloniki"
            elif "πάτρα" in city_hint_lower or "patra" in city_hint_lower:
                city_key = "patra"
            elif "ηράκλειο" in city_hint_lower or "heraklion" in city_hint_lower:
                city_key = "heraklion"
            elif "λάρισα" in city_hint_lower or "larissa" in city_hint_lower:
                city_key = "larissa"
            else:
                city_key = None

            if city_key and event_data.lat and event_data.lng:
                center_lat, center_lng = TrustEngine.CITY_CENTERS[city_key]
                distance = TrustEngine._haversine(
                    center_lat, center_lng, event_data.lat, event_data.lng
                )
                if distance > 15:
                    logger.warning(
                        f"[TRUST] Event '{event_data.title}' in {city_hint} is {distance:.2f}km "
                        "away. Failing trust gate."
                    )
                    return False

        return True

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates distance between two points in km."""
        r = 6371  # Earth radius
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))
