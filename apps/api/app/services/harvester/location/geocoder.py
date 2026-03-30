import asyncio
import difflib
import logging
import re
from typing import Any, ClassVar

from geoalchemy2 import WKTElement
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.config import settings
from app.core.geography_constants import DEFAULT_COUNTRY_CODE, CountryConfig, get_country_config
from app.db.session import engine
from app.infrastructure.external.mapbox_client import MapboxClient, MapboxFeature
from app.repositories.venue_repository import VenueRepository
from app.utils.geo_utils import haversine_distance, normalize_string
from packages.domain.models import PendingEvent

logger = logging.getLogger(__name__)


class GeocodeResult(BaseModel):
    lat: float | None = None
    lng: float | None = None
    relevance: float
    full_address: str
    country_code: str
    city: str | None = None
    geocoding_status: str = "failed"
    geocoding_metadata: dict[str, Any] = Field(default_factory=dict)


class GeocodingPolicy:
    """Encapsulates the rules for determining geocoding status and query enrichment."""

    FUZZY_SUFFIXES_TO_REMOVE: ClassVar[list[str]] = [
        "SKG Edition",
        "Athens Edition",
        "Live",
        "Tickets",
        "2024",
        "2025",
        "2026",
        "Edition",
        "Final",
        "Day",
    ]

    @staticmethod
    def enrich_query(
        location_name: str,
        config: CountryConfig,
        city_hint: str | None = None,
        source_address: str | None = None,
    ) -> str:
        if source_address:
            if location_name.lower() in source_address.lower():
                return source_address
            return f"{location_name}, {source_address}"

        location_lower = location_name.lower()
        parts = [location_name]

        if city_hint:
            city_hint_lower = city_hint.lower().strip()
            aliases = set(config.city_aliases.get(city_hint_lower, [city_hint_lower]))
            if not any(alias in location_lower for alias in aliases):
                parts.append(city_hint)

        return ", ".join(parts)

    @classmethod
    def create_fuzzy_query(cls, location_name: str) -> str:
        fuzzy = location_name
        for suffix in cls.FUZZY_SUFFIXES_TO_REMOVE:
            esc_suffix = re.escape(suffix)
            fuzzy = re.sub(
                rf"(\s+-\s+|\s+){esc_suffix}(\s+|$)", " ", fuzzy, flags=re.IGNORECASE
            ).strip()

        fuzzy = re.sub(r"[^\w\s,]", "", fuzzy)
        fuzzy = re.sub(r"\s+", " ", fuzzy).strip()
        return fuzzy if len(fuzzy) >= 3 else location_name

    @staticmethod
    def determine_status(
        feature: MapboxFeature,
        config: CountryConfig,
        query: str,
        city_hint: str | None = None,
        source_address: str | None = None,
    ) -> str:
        properties = feature.properties
        feature_type = (properties.get("feature_type") or feature.type).lower()
        result_name = properties.get("name", "")
        result_address = properties.get("full_address", result_name)
        relevance = feature.relevance or 0.9

        context = properties.get("context", {})
        result_country = context.get("country", {}).get("country_code", "").upper()
        result_city = context.get("place", {}).get("name")

        if result_country != config.code:
            return "failed"

        name_similarity = difflib.SequenceMatcher(None, query.lower(), result_name.lower()).ratio()

        coords = feature.geometry.get("coordinates")
        if not coords:
            return "failed"

        lng, lat = coords[0], coords[1]
        bbox = config.bbox
        if not (
            bbox["lat_min"] <= lat <= bbox["lat_max"] and bbox["lng_min"] <= lng <= bbox["lng_max"]
        ):
            return "failed"

        if source_address and result_address:
            s_norm = normalize_string(source_address, config.char_map)
            r_norm = normalize_string(result_address, config.char_map)

            ratio = difflib.SequenceMatcher(None, s_norm, r_norm).ratio()
            s_tokens = set(s_norm.split())
            r_tokens = set(r_norm.split())
            intersection = s_tokens.intersection(r_tokens)
            token_ratio = len(intersection) / max(len(s_tokens), 1)

            is_address_match = (
                (ratio >= 0.6) or (token_ratio >= 0.7) or (s_norm in r_norm) or (r_norm in s_norm)
            )
            if not is_address_match and relevance < 0.95:
                return "ambiguous"

        is_verified_poi = feature_type == "poi" and name_similarity >= 0.85

        if city_hint and result_city:
            hint_clean = city_hint.lower().strip()
            city_clean = result_city.lower().strip()
            aliases = set(config.city_aliases.get(hint_clean, [hint_clean]))
            if (
                city_clean not in aliases
                and difflib.SequenceMatcher(None, hint_clean, city_clean).ratio() < 0.8
            ):
                city_coords = config.cities.get(hint_clean)
                if city_coords:
                    if haversine_distance(lat, lng, city_coords["lat"], city_coords["lng"]) > 20:
                        return "ambiguous"

        if is_verified_poi:
            return "verified"

        if feature_type == "poi":
            return (
                "verified"
                if relevance >= 0.8 or (relevance >= 0.6 and name_similarity >= 0.5)
                else "ambiguous"
            )

        if feature_type == "address":
            return "verified" if relevance >= 0.85 else "ambiguous"

        venue_indicators = [
            "club",
            "stage",
            "theater",
            "theatre",
            "stadium",
            "arena",
            "venue",
            "live",
            "megaro",
            "μέγαρο",
            "garden",
            "κήπος",
            "square",
            "πλατεία",
        ]
        is_potential_venue = any(ind in query.lower() for ind in venue_indicators)

        if feature_type == "street":
            if is_potential_venue:
                return "verified" if name_similarity >= 0.8 else "failed"
            return "verified" if (relevance >= 0.9 and name_similarity >= 0.8) else "failed"

        if feature_type in ["place", "locality"]:
            if is_potential_venue or relevance < 0.85:
                return "failed"
            return "verified"

        return "failed"


class GeocoderService:
    _mapbox: MapboxClient = MapboxClient()
    _policy: GeocodingPolicy = GeocodingPolicy()

    @classmethod
    async def get_coordinates(
        cls,
        location_name: str,
        country_hint: str = DEFAULT_COUNTRY_CODE,
        city_hint: str | None = None,
        search_term: str | None = None,
        source_address: str | None = None,
    ) -> GeocodeResult | None:
        if not location_name:
            return None

        config = get_country_config(country_hint)

        with Session(engine) as session:
            cached = VenueRepository(session).get_by_name(location_name, config.code, city_hint)
            if cached:
                return GeocodeResult(
                    lat=cached.lat,
                    lng=cached.lng,
                    relevance=cached.relevance,
                    full_address=cached.full_address,
                    country_code=cached.country_code,
                    city=cached.city,
                    geocoding_status="verified",
                    geocoding_metadata={"source": "cache"},
                )

        if not settings.MAPBOX_ACCESS_TOKEN:
            return None

        primary_query = search_term or location_name
        effective_city = (
            city_hint or cls._extract_city(primary_query, config) or config.default_city
        )
        enriched = cls._policy.enrich_query(primary_query, config, effective_city, source_address)

        result = await cls._try_geocode(
            enriched, config, location_name, effective_city, source_address
        )

        if not result or result.geocoding_status == "failed":
            fuzzy = cls._policy.create_fuzzy_query(primary_query)
            if fuzzy != primary_query:
                result = await cls._try_geocode(
                    fuzzy, config, location_name, effective_city, source_address
                )

        if result and result.geocoding_status == "failed":
            return None

        return result

    @classmethod
    async def get_suggestions(
        cls, query: str, country_hint: str = DEFAULT_COUNTRY_CODE
    ) -> list[GeocodeResult]:
        if not query or not settings.MAPBOX_ACCESS_TOKEN:
            return []

        config = get_country_config(country_hint)
        proximity = f"{config.center['lng']},{config.center['lat']}"

        suggestions: list[GeocodeResult] = []
        try:
            resp = await cls._mapbox.search_box(query, config.code, proximity)
            if not resp or not resp.features:
                resp = await cls._mapbox.geocode_v6(query, config.code, proximity)

            if resp and resp.features:
                for feat in resp.features:
                    coords = feat.geometry.get("coordinates")
                    if not coords:
                        continue

                    suggestions.append(
                        GeocodeResult(
                            lng=coords[0],
                            lat=coords[1],
                            relevance=feat.relevance or 0.9,
                            full_address=feat.properties.get(
                                "full_address", feat.properties.get("name", "Unknown")
                            ),
                            country_code=config.code,
                            city=feat.properties.get("context", {}).get("place", {}).get("name"),
                            geocoding_status="verified",
                            geocoding_metadata={
                                "source": "suggestion",
                                "full_address": feat.properties.get(
                                    "full_address", feat.properties.get("name", "Unknown")
                                ),
                            },
                        )
                    )
        except Exception as e:
            logger.error(f"[GEOCODER] Suggestions error: {e}")

        return suggestions

    @classmethod
    async def _try_geocode(
        cls, query: str, config: CountryConfig, original: str, city_hint: str, addr: str | None
    ) -> GeocodeResult | None:
        proximity = f"{config.center['lng']},{config.center['lat']}"
        resp = await cls._mapbox.search_box(query, config.code, proximity)
        if not resp or not resp.features:
            resp = await cls._mapbox.geocode_v6(query, config.code, proximity)

        if not resp or not resp.features:
            return None

        best_feat = resp.features[0]
        status = cls._policy.determine_status(best_feat, config, original, city_hint, addr)

        coords = best_feat.geometry.get("coordinates")
        if not coords:
            return None

        res = GeocodeResult(
            lat=coords[1],
            lng=coords[0],
            relevance=best_feat.relevance or 0.9,
            full_address=best_feat.properties.get(
                "full_address", best_feat.properties.get("name", "")
            ),
            country_code=config.code,
            city=best_feat.properties.get("context", {}).get("place", {}).get("name"),
            geocoding_status=status,
            geocoding_metadata={
                "source": "mapbox",
                "feature_type": best_feat.properties.get("feature_type"),
                "full_address": best_feat.properties.get(
                    "full_address", best_feat.properties.get("name", "")
                ),
            },
        )

        if status in ["verified", "ambiguous"]:
            if status == "verified" or res.relevance >= 0.6:
                with Session(engine) as session:
                    VenueRepository(session).save_venue(
                        original,
                        config.code,
                        res.lat,
                        res.lng,
                        res.full_address,
                        res.relevance,
                        res.city,
                    )

        return res

    @staticmethod
    def _extract_city(query: str, config: CountryConfig) -> str | None:
        query_norm = normalize_string(query, config.char_map)
        for kw in config.city_keywords:
            if kw.lower() in query_norm:
                for city in config.cities:
                    if kw.lower() == city.lower():
                        return city
        return None

    @classmethod
    def purge_cache(cls, venue_name: str | None = None) -> dict[str, Any]:
        try:
            with Session(engine) as session:
                count = VenueRepository(session).delete_venues(venue_name)
                return {"deleted": count}
        except Exception as e:
            logger.error(f"[GEOCODER] Cache purge failed: {e}")
            return {"deleted": 0, "error": str(e)}

    @classmethod
    async def batch_geocode_pending_events(cls, batch_size: int = 50) -> dict[str, int]:
        stats = {"updated": 0, "failed": 0, "skipped": 0}
        processed: set[Any] = set()
        try:
            while True:
                with Session(engine) as session:
                    events = session.exec(
                        select(PendingEvent)
                        .where(
                            PendingEvent.geocoding_status == "failed",
                            PendingEvent.id.not_in(processed),
                        )
                        .limit(batch_size)
                    ).all()
                if not events:
                    break
                for ev in events:
                    processed.add(ev.id)
                    if not ev.location_name:
                        stats["skipped"] += 1
                        continue

                    meta = ev.event_metadata or {}
                    addr = meta.get("address") or meta.get("street_address")
                    city = meta.get("city") or meta.get("addressLocality")

                    loc = meta.get("location")
                    if isinstance(loc, dict):
                        loc_addr = loc.get("address")
                        if isinstance(loc_addr, dict):
                            addr = addr or loc_addr.get("streetAddress")
                            city = city or loc_addr.get("addressLocality")
                    elif isinstance(loc, str) and not addr:
                        addr = loc

                    res = await cls.get_coordinates(
                        ev.location_name, DEFAULT_COUNTRY_CODE, city_hint=city, source_address=addr
                    )
                    with Session(engine) as session:
                        db_ev = session.get(PendingEvent, ev.id)
                        if db_ev and res and res.lat:
                            db_ev.confidence_score, db_ev.geocoding_status = (
                                res.relevance,
                                res.geocoding_status,
                            )
                            db_ev.location = WKTElement(f"POINT({res.lng} {res.lat})", srid=4326)
                            stats["updated"] += 1
                        else:
                            stats["failed"] += 1
                        session.add(db_ev)
                        session.commit()
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in batch geocoding: {e}")
        return stats
