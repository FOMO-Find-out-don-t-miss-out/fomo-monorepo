import logging
import math
from datetime import UTC, datetime
from pathlib import Path

import yaml

from packages.domain.schemas.extracted_event import ExtractedEvent

logger = logging.getLogger(__name__)


class TrustEngine:
    """Business logic for automated event validation, trust levels, and junk filtering."""

    def __init__(self, country_code: str = "GR") -> None:
        self.country_code = country_code.upper()
        self.city_centers: dict[str, tuple[float, float]] = {}
        self.junk_keywords: list[str] = []
        self._load_config()

    def _load_config(self) -> None:
        """Loads regional configuration from YAML file."""
        config_path = (
            Path(__file__).parent.parent / "resources" / "regions" / f"{self.country_code}.yaml"
        )

        if not config_path.exists():
            logger.warning(
                f"[TRUST] Regional config for {self.country_code} not found at {config_path}. "
                "Falling back to default (GR)."
            )
            config_path = Path(__file__).parent.parent / "resources" / "regions" / "GR.yaml"

        try:
            with config_path.open(encoding="utf-8") as f:
                config = yaml.safe_load(f)
                self.city_centers = {
                    k: (v[0], v[1]) for k, v in config.get("city_centers", {}).items()
                }
                self.junk_keywords = config.get("junk_keywords", [])
                logger.info(f"[TRUST] Loaded config for {self.country_code} from {config_path}")
        except Exception as e:
            logger.error(f"[TRUST] Error loading regional config: {e}")
            # Ensure some defaults if loading fails completely
            self.city_centers = {}
            self.junk_keywords = []

    def is_junk(self, event_data: ExtractedEvent) -> bool:
        """Determines if an event is low-quality or junk based on keywords and AI category."""
        if event_data.category == "Junk":
            return True

        title_lower = event_data.title.lower()
        if any(kw in title_lower for kw in self.junk_keywords) and len(event_data.title) < 100:
            return True

        return False

    def is_trusted_for_autopublish(self, event_data: ExtractedEvent) -> bool:
        """Gate logic for automated publishing."""
        # 1. Source Gate
        if event_data.ingestion_method != "json_ld":
            return False

        # 2. Geocoding Gate
        if event_data.geocoding_status != "verified" or (event_data.confidence_score or 0) < 0.9:
            return False

        # 3. Future Gate
        start_time = event_data.start_time
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)
        if start_time <= datetime.now(UTC):
            return False

        # 4. Distance Guard (15km radius check)
        city_hint = event_data.event_metadata.get("city") or event_data.event_metadata.get(
            "addressLocality"
        )
        if city_hint and isinstance(city_hint, str):
            city_hint_lower = city_hint.lower().strip()
            # Normalize common names and check against city_centers
            city_key = None
            for key in self.city_centers:
                if key in city_hint_lower:
                    city_key = key
                    break

            # Special cases for normalization if needed
            if not city_key:
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
                elif "λευκωσία" in city_hint_lower or "nicosia" in city_hint_lower:
                    city_key = "nicosia"
                elif "λεμεσός" in city_hint_lower or "limassol" in city_hint_lower:
                    city_key = "limassol"
                elif "λάρνακα" in city_hint_lower or "larnaca" in city_hint_lower:
                    city_key = "larnaca"
                elif "πάφος" in city_hint_lower or "paphos" in city_hint_lower:
                    city_key = "paphos"

            if city_key and city_key in self.city_centers and event_data.lat and event_data.lng:
                center_lat, center_lng = self.city_centers[city_key]
                distance = self._haversine(center_lat, center_lng, event_data.lat, event_data.lng)
                if distance > 15:
                    logger.warning(
                        f"[TRUST] Event '{event_data.title}' in {city_hint} is {distance:.2f}km "
                        "away. Failing trust gate."
                    )
                    return False

        return True

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates distance between two points in km."""
        r = 6371  # Earth radius
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))
