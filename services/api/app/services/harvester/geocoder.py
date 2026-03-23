import logging
import asyncio
import re
import difflib
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from app.db.session import engine
from app.models.event import PendingEvent
from app.models.venue import Venue
from app.core.config import settings
from geoalchemy2 import Geography, WKTElement
from app.core.geography_constants import (
    DEFAULT_COUNTRY_CODE,
    get_country_config,
    CountryConfig
)
from app.utils.geo_utils import haversine_distance, normalize_string
from app.infrastructure.external.mapbox_client import MapboxClient, MapboxFeature
from app.repositories.venue_repository import VenueRepository

logger = logging.getLogger(__name__)

class GeocodeResult(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    relevance: float
    full_address: str
    country_code: str
    city: Optional[str] = None
    geocoding_status: str = "failed"
    geocoding_metadata: Dict[str, Any] = Field(default_factory=dict)

class GeocodingPolicy:
    """Encapsulates the rules for determining geocoding status and query enrichment."""
    
    FUZZY_SUFFIXES_TO_REMOVE = [
        "SKG Edition", "Athens Edition", "Live", "Tickets", 
        "2024", "2025", "2026", "Edition", "Final", "Day"
    ]

    @staticmethod
    def enrich_query(location_name: str, config: CountryConfig, city_hint: Optional[str] = None, source_address: Optional[str] = None) -> str:
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
            # Escape suffix for regex and handle optional separators like " - " or " "
            esc_suffix = re.escape(suffix)
            fuzzy = re.sub(rf"(\s+-\s+|\s+){esc_suffix}(\s+|$)", " ", fuzzy, flags=re.IGNORECASE).strip()
        
        fuzzy = re.sub(r"[^\w\s,]", "", fuzzy)
        fuzzy = re.sub(r"\s+", " ", fuzzy).strip()
        return fuzzy if len(fuzzy) >= 3 else location_name

    @staticmethod
    def determine_status(
        feature: MapboxFeature,
        config: CountryConfig,
        query: str,
        city_hint: Optional[str] = None,
        source_address: Optional[str] = None
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

        # 1. Geofence & BBox check
        coords = feature.geometry.get("coordinates")
        if not coords:
            return "failed"
            
        lng, lat = coords[0], coords[1]
        bbox = config.bbox
        if not (bbox["lat_min"] <= lat <= bbox["lat_max"] and bbox["lng_min"] <= lng <= bbox["lng_max"]):
            return "failed"

        # 2. Address Guard
        if source_address and result_address:
            s_norm = normalize_string(source_address, config.char_map)
            r_norm = normalize_string(result_address, config.char_map)
            
            # Use both SequenceMatcher and token-based intersection
            ratio = difflib.SequenceMatcher(None, s_norm, r_norm).ratio()
            
            s_tokens = set(s_norm.split())
            r_tokens = set(r_norm.split())
            intersection = s_tokens.intersection(r_tokens)
            token_ratio = len(intersection) / max(len(s_tokens), 1)

            # If token match is very high (subset/superset), or overall ratio is decent
            is_address_match = (ratio >= 0.6) or (token_ratio >= 0.7) or (s_norm in r_norm) or (r_norm in s_norm)
            
            if not is_address_match and relevance < 0.95:
                return "ambiguous"

        # 3. Validation Rules
        if feature_type == "poi" and name_similarity >= 0.85:
            return "verified"

        if city_hint and result_city:
            hint_clean = city_hint.lower().strip()
            city_clean = result_city.lower().strip()
            aliases = set(config.city_aliases.get(hint_clean, [hint_clean]))
            if city_clean not in aliases and difflib.SequenceMatcher(None, hint_clean, city_clean).ratio() < 0.8:
                # Check distance from city center if no match
                city_coords = config.cities.get(hint_clean)
                if city_coords:
                    if haversine_distance(lat, lng, city_coords["lat"], city_coords["lng"]) > 20:
                        return "ambiguous"
                    else:
                        # Close enough to city center, promote back only if it's a POI or very high relevance address
                        if feature_type == "poi" and relevance >= 0.8:
                            return "verified"
                        if feature_type == "address" and relevance >= 0.95:
                            return "verified"
                        return "ambiguous"

        if feature_type == "poi":
            return "verified" if relevance >= 0.8 or (relevance >= 0.6 and name_similarity >= 0.5) else "ambiguous"
        
        if feature_type == "address":
            return "verified" if relevance >= 0.85 else "ambiguous"

        venue_indicators = ["club", "stage", "theater", "theatre", "stadium", "arena", "venue", "live", "megaro", "μέγαρο", "garden", "κήπος", "square", "πλατεία"]
        is_potential_venue = any(ind in query.lower() for ind in venue_indicators)

        if feature_type == "street":
            # If query looks like a venue name, a street match is weak unless it's very similar
            if is_potential_venue:
                return "verified" if name_similarity >= 0.8 else "failed"
            # Even for non-venues, a street match should have high name similarity if relevance is not perfect
            return "verified" if (relevance >= 0.9 and name_similarity >= 0.8) else "failed"

        if feature_type in ["place", "locality"]:
            if is_potential_venue or relevance < 0.85: return "failed"
            return "verified"

        return "failed"

class GeocoderService:
    _mapbox = MapboxClient()
    _policy = GeocodingPolicy()

    @classmethod
    async def get_coordinates(
        cls, 
        location_name: str, 
        country_hint: str = DEFAULT_COUNTRY_CODE, 
        city_hint: Optional[str] = None, 
        search_term: Optional[str] = None,
        source_address: Optional[str] = None
    ) -> Optional[GeocodeResult]:
        if not location_name: return None
        
        config = get_country_config(country_hint)
        
        # 1. Cache Check
        with Session(engine) as session:
            cached = VenueRepository(session).get_by_name(location_name, config.code, city_hint)
            if cached:
                return GeocodeResult(
                    lat=cached.lat, lng=cached.lng, relevance=cached.relevance,
                    full_address=cached.full_address, country_code=cached.country_code,
                    city=cached.city, geocoding_status="verified",
                    geocoding_metadata={"source": "cache"}
                )

        if not settings.MAPBOX_ACCESS_TOKEN: return None

        # 2. Preparation
        primary_query = search_term or location_name
        effective_city = city_hint or cls._extract_city(primary_query, config) or config.default_city
        enriched = cls._policy.enrich_query(primary_query, config, effective_city, source_address)

        # 3. API Cycle
        result = await cls._try_geocode(enriched, config, location_name, effective_city, source_address)
        
        if (not result or result.geocoding_status == "failed"):
            fuzzy = cls._policy.create_fuzzy_query(primary_query)
            if fuzzy != primary_query: # Only retry if fuzzy actually changed something
                result = await cls._try_geocode(fuzzy, config, location_name, effective_city, source_address)

        # Test expectation: return None if status is failed
        if result and result.geocoding_status == "failed":
            return None

        return result

    @classmethod
    async def get_suggestions(
        cls, query: str, country_hint: str = DEFAULT_COUNTRY_CODE
    ) -> List[GeocodeResult]:
        """Returns a list of geocoding suggestions for a query string."""
        if not query or not settings.MAPBOX_ACCESS_TOKEN:
            return []

        config = get_country_config(country_hint)
        proximity = f"{config.center['lng']},{config.center['lat']}"

        suggestions = []
        try:
            # Try Search Box first
            resp = await cls._mapbox.search_box(query, config.code, proximity)
            if not resp or not resp.features:
                resp = await cls._mapbox.geocode_v6(query, config.code, proximity)
            
            if resp and resp.features:
                for feat in resp.features:
                    coords = feat.geometry.get("coordinates")
                    if not coords: continue
                    
                    suggestions.append(GeocodeResult(
                        lng=coords[0],
                        lat=coords[1],
                        relevance=feat.relevance or 0.9,
                        full_address=feat.properties.get("full_address", feat.properties.get("name", "Unknown")),
                        country_code=config.code,
                        city=feat.properties.get("context", {}).get("place", {}).get("name"),
                        geocoding_status="verified", # Suggestions are 'verified' by default for UI selection
                        geocoding_metadata={"source": "suggestion"}
                    ))
        except Exception as e:
            logger.error(f"[GEOCODER] Suggestions error: {e}")
        
        return suggestions

    @classmethod
    async def _try_geocode(cls, query: str, config: CountryConfig, original: str, city_hint: str, addr: Optional[str]) -> Optional[GeocodeResult]:
        # Try Search Box
        resp = await cls._mapbox.search_box(query, config.code, f"{config.center['lng']},{config.center['lat']}")
        if not resp or not resp.features:
            # Fallback to Geocoding V6
            resp = await cls._mapbox.geocode_v6(query, config.code, f"{config.center['lng']},{config.center['lat']}")
        
        if not resp or not resp.features: return None

        # Pick best feature
        best_feat = resp.features[0] 
        status = cls._policy.determine_status(best_feat, config, original, city_hint, addr)
        
        coords = best_feat.geometry.get("coordinates")
        if not coords: return None

        res = GeocodeResult(
            lat=coords[1],
            lng=coords[0],
            relevance=best_feat.relevance or 0.9,
            full_address=best_feat.properties.get("full_address", best_feat.properties.get("name", "")),
            country_code=config.code,
            city=best_feat.properties.get("context", {}).get("place", {}).get("name"),
            geocoding_status=status,
            geocoding_metadata={"source": "mapbox", "feature_type": best_feat.properties.get("feature_type")}
        )

        if status in ["verified", "ambiguous"]:
            # Only save ambiguous if it has some decent relevance
            if status == "verified" or res.relevance >= 0.6:
                with Session(engine) as session:
                    VenueRepository(session).save_venue(
                        original, config.code, res.lat, res.lng, res.full_address, res.relevance, res.city
                    )
        
        return res

    @staticmethod
    def _extract_city(query: str, config: CountryConfig) -> Optional[str]:
        # Use normalization to match Greek city names/inflections correctly
        query_norm = normalize_string(query, config.char_map)
        for kw in config.city_keywords:
            if kw.lower() in query_norm:
                for city in config.cities:
                    if kw.lower() == city.lower(): return city
        return None

    @classmethod
    def purge_cache(cls, venue_name: Optional[str] = None) -> Dict[str, Any]:
        try:
            with Session(engine) as session:
                count = VenueRepository(session).delete_venues(venue_name)
                return {"deleted": count}
        except Exception as e:
            logger.error(f"[GEOCODER] Cache purge failed: {e}")
            return {"deleted": 0, "error": str(e)}

    @classmethod
    async def batch_geocode_pending_events(cls, batch_size: int = 50) -> Dict[str, int]:
        stats = {"updated": 0, "failed": 0, "skipped": 0}
        processed = set()
        while True:
            with Session(engine) as session:
                events = session.exec(select(PendingEvent).where(PendingEvent.geocoding_status == "failed", PendingEvent.id.not_in(processed)).limit(batch_size)).all()
            if not events: break
            for ev in events:
                processed.add(ev.id)
                if not ev.location_name:
                    stats["skipped"] += 1
                    continue

                # Extract context from metadata
                meta = ev.event_metadata or {}
                addr = meta.get("address") or meta.get("street_address")
                city = meta.get("city") or meta.get("addressLocality")
                
                # Check for explicit address data from location field if metadata is string
                loc = meta.get("location")
                if isinstance(loc, dict):
                    loc_addr = loc.get("address")
                    if isinstance(loc_addr, dict):
                        addr = addr or loc_addr.get("streetAddress")
                        city = city or loc_addr.get("addressLocality")
                elif isinstance(loc, str) and not addr:
                    addr = loc # Use location string as address if no other address found

                res = await cls.get_coordinates(
                    ev.location_name, 
                    DEFAULT_COUNTRY_CODE, 
                    city_hint=city, 
                    source_address=addr
                )
                with Session(engine) as session:
                    db_ev = session.get(PendingEvent, ev.id)
                    if db_ev and res and res.lat:
                        db_ev.confidence_score, db_ev.geocoding_status = res.relevance, res.geocoding_status
                        db_ev.location = WKTElement(f"POINT({res.lng} {res.lat})", srid=4326)
                        stats["updated"] += 1
                    else:
                        stats["failed"] += 1
                    session.add(db_ev); session.commit()
            await asyncio.sleep(0.1)
        return stats
