import httpx
import logging
import asyncio
import re
import math
import difflib
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from app.db.session import engine
from app.models.event import PendingEvent
from app.models.venue import Venue
from app.core.config import settings
from geoalchemy2 import Geography, WKTElement
from app.core.geography import COUNTRY_CODE_TO_NAME, COUNTRY_DEFAULTS

logger = logging.getLogger(__name__)

DISTANCE_THRESHOLD_KM = 100



def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class GeocodeResult(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    relevance: float
    full_address: str
    country_code: str
    city: Optional[str] = None
    geocoding_status: str = "failed"
    geocoding_metadata: Dict[str, Any] = Field(default_factory=dict)


class GeocoderService:
    BASE_URL = "https://api.mapbox.com/search/geocode/v6/forward"
    SEARCH_BOX_URL = "https://api.mapbox.com/search/searchbox/v1/forward"
    MIN_LOCATION_NAME_LEN = 10
    FUZZY_SUFFIXES_TO_REMOVE = [
        "SKG Edition", "Athens Edition", "Live", "Tickets", 
        "2024", "2025", "2026", "Edition", "Final", "Day"
    ]

    @classmethod
    async def get_coordinates(
        cls, location_name: str, country_hint: str = "GR", city_hint: Optional[str] = None, search_term: Optional[str] = None
    ) -> Optional[GeocodeResult]:
        """
        Gets coordinates for a location name using Mapbox Search Box and Geocoding APIs.
        Implements PostgreSQL caching to minimize API costs.
        """
        if not location_name:
            return None

        logger.info(f"[GEOCODER] Raw location_name from scraper: '{location_name}'")

        cached_venue = cls._check_cache(location_name, country_hint)
        if cached_venue:
            logger.info(f"[GEOCODER] Cache Hit for: '{location_name}' | cached_coords: ({cached_venue.lat}, {cached_venue.lng})")
            return GeocodeResult(
                lat=cached_venue.lat,
                lng=cached_venue.lng,
                relevance=cached_venue.relevance,
                full_address=cached_venue.full_address,
                country_code=cached_venue.country_code,
                city=cached_venue.city,
                geocoding_status="verified",
                geocoding_metadata={"source": "cache", "cached_venue_id": str(cached_venue.id)}
            )

        if not settings.MAPBOX_ACCESS_TOKEN:
            logger.warning("MAPBOX_ACCESS_TOKEN not configured. Skipping live geocoding.")
            return None

        primary_query = search_term if search_term else location_name
        effective_city_hint = city_hint
        if not effective_city_hint:
            effective_city_hint = cls._extract_city_from_query(primary_query, country_hint)
        
        # If still no city hint and we are in GR, check if location_name implies Athens
        if not effective_city_hint and country_hint == "GR":
             effective_city_hint = "Athens"

        enriched_query = cls._enrich_query(primary_query, country_hint, effective_city_hint)
        
        logger.info(f"[GEOCODER] Query Enrichment: original='{location_name}' | search_term='{search_term}' | enriched='{enriched_query}'")

        # Strategy 1: Search Box API (Best for POIs/Venues)
        result = await cls._execute_search_box(enriched_query, country_hint, location_name, city_hint=effective_city_hint)
        
        # Strategy 2: Geocoding v6 (Fallback for specific addresses/streets)
        if not result or result.geocoding_status == "failed":
            logger.info(f"[GEOCODER] Search Box failed, trying Geocoding v6: '{enriched_query}'")
            result = await cls._execute_geocode(enriched_query, country_hint, location_name, city_hint=effective_city_hint)
        
        # Strategy 3: Fuzzy Fallback
        if not result or result.geocoding_status == "failed":
            fuzzy_query = cls._create_fuzzy_query(primary_query)
            if fuzzy_query != enriched_query:
                logger.info(f"[GEOCODER] Fallback: Trying fuzzy query: '{fuzzy_query}'")
                result = await cls._execute_search_box(fuzzy_query, country_hint, location_name, city_hint=effective_city_hint)
                if not result or result.geocoding_status == "failed":
                    result = await cls._execute_geocode(fuzzy_query, country_hint, location_name, city_hint=effective_city_hint)
        
        return result

    @classmethod
    async def _execute_search_box(cls, query: str, country_hint: str, original_location: str, city_hint: Optional[str] = None) -> Optional[GeocodeResult]:
        """Execute a search request to Mapbox Search Box API v1."""
        country_defaults = cls._get_country_defaults(country_hint)
        center = country_defaults.get("center", {"lat": 37.9838, "lng": 23.7275})
        
        proximity_center = center
        if city_hint:
            cities = country_defaults.get("cities", {})
            city_key = city_hint.lower().strip()
            if city_key in cities:
                proximity_center = cities[city_key]

        params = {
            "q": query,
            "access_token": settings.MAPBOX_ACCESS_TOKEN,
            "limit": 5,
            "proximity": f"{proximity_center['lng']},{proximity_center['lat']}",
            "types": "poi,address,street"
        }
        if country_hint:
            params["country"] = country_hint.lower()

        logger.info(f"[GEOCODER] Attempt: Querying Mapbox Search Box | location: '{query}' | types: {params['types']}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(cls.SEARCH_BOX_URL, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()

            if data.get("features"):
                return cls._process_geocode_features(
                    data["features"], query, country_hint, original_location,
                    city_hint=city_hint, types_filter=params["types"]
                )
        except Exception as e:
            logger.error(f"[GEOCODER] Search Box error: {e}")
        
        return None

    @classmethod
    async def _execute_geocode(cls, query: str, country_hint: str, original_location: str, city_hint: Optional[str] = None) -> Optional[GeocodeResult]:
        """Execute a single geocoding request to Mapbox Geocoding v6."""
        country_defaults = cls._get_country_defaults(country_hint)
        center = country_defaults.get("center", {"lat": 37.9838, "lng": 23.7275})
        
        proximity_center = center
        if city_hint:
            cities = country_defaults.get("cities", {})
            city_key = city_hint.lower().strip()
            if city_key in cities:
                proximity_center = cities[city_key]
        
        type_strategies = [
            ("street,address", "street/address-level"),
            ("place,locality,address", "all types (fallback)"),
        ]
        
        for types_filter, strategy_name in type_strategies:
            params = {
                "q": query,
                "access_token": settings.MAPBOX_ACCESS_TOKEN,
                "limit": 5,
                "proximity": f"{proximity_center['lng']},{proximity_center['lat']}",
                "types": types_filter
            }
            if country_hint:
                params["country"] = country_hint.lower()
            
            logger.info(f"[GEOCODER] Attempt: Querying Mapbox Geocoding v6 [{strategy_name}] | location: '{query}'")

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(cls.BASE_URL, params=params, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()

                if data.get("features"):
                    result = cls._process_geocode_features(
                        data["features"], query, country_hint, original_location,
                        city_hint=city_hint, types_filter=types_filter
                    )
                    if result and result.geocoding_status == "verified":
                        return result
                    if result and result.geocoding_status == "failed" and strategy_name != "place,locality,address":
                        continue

            except Exception as e:
                logger.error(f"[GEOCODER] Geocoding v6 error: {e}")
                if strategy_name != "place,locality,address":
                    continue

        return None

    @staticmethod
    def _parse_relevance(val: Union[float, str, None]) -> float:
        """Parse Mapbox relevance/confidence which can be a float or a string level."""
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        
        val_str = str(val).lower().strip()
        if val_str == "high": return 0.95
        if val_str == "medium": return 0.7
        if val_str == "low": return 0.4
        
        try:
            return float(val_str)
        except ValueError:
            return 0.0

    @classmethod
    async def get_suggestions(
        cls, query: str, country_hint: str = "GR"
    ) -> List[GeocodeResult]:
        """Returns a list of geocoding suggestions for a query string."""
        if not query or not settings.MAPBOX_ACCESS_TOKEN:
            return []

        country_defaults = cls._get_country_defaults(country_hint)
        center = country_defaults.get("center", {"lat": 37.9838, "lng": 23.7275})
        
        params = {
            "q": query,
            "access_token": settings.MAPBOX_ACCESS_TOKEN,
            "limit": 5,
            "proximity": f"{center['lng']},{center['lat']}",
            "types": "poi,address,street"
        }
        if country_hint:
            params["country"] = country_hint.lower()

        suggestions = []
        try:
            async with httpx.AsyncClient() as client:
                # Try Search Box first
                response = await client.get(cls.SEARCH_BOX_URL, params=params, timeout=10.0)
                data = response.json()
                
                if data.get("features"):
                    for feat in data["features"]:
                        res = cls._process_single_feature(feat, query, country_hint, query)
                        if res: suggestions.append(res)
                
                # If Search Box is empty or low confidence, fallback to Geocoding v6
                if not suggestions:
                    response = await client.get(cls.BASE_URL, params=params, timeout=10.0)
                    data = response.json()
                    if data.get("features"):
                        for feat in data["features"]:
                            res = cls._process_single_feature(feat, query, country_hint, query)
                            if res: suggestions.append(res)
                            
        except Exception as e:
            logger.error(f"[GEOCODER] Suggestions error: {e}")
        
        return suggestions

    @classmethod
    def _process_single_feature(cls, feature: Dict[str, Any], query: str, country_hint: str, original_location: str) -> Optional[GeocodeResult]:
        """Helper to process a single Mapbox feature into a GeocodeResult."""
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {}).get("coordinates")
        if not geometry: return None
        
        context = properties.get("context", {})
        result_country = context.get("country", {}).get("country_code", "").upper()
        
        return GeocodeResult(
            lng=geometry[0],
            lat=geometry[1],
            relevance=cls._parse_relevance(feature.get("relevance", 0.9)),
            full_address=properties.get("full_address", properties.get("name", "Unknown")),
            country_code=result_country or country_hint,
            city=context.get("place", {}).get("name"),
            geocoding_status="verified" if result_country == country_hint.upper() else "ambiguous",
            geocoding_metadata={
                "source": "mapbox_suggestion", 
                "feature_type": properties.get("feature_type"),
                "full_address": properties.get("full_address", properties.get("name", "Unknown")),
                "city": context.get("place", {}).get("name")
            }
        )

    @classmethod
    def _process_geocode_features(cls, features: List[Dict[str, Any]], query: str, country_hint: str, original_location: str, city_hint: Optional[str] = None, types_filter: str = "") -> Optional[GeocodeResult]:
        """Process geocoding features and select the best result."""
        if not features:
            return None

        best_result = None
        best_relevance = -1.0

        for feature in features:
            properties = feature.get("properties", {})
            result_name = properties.get("name", "")
            
            relevance = 0.0
            if "relevance" in feature:
                relevance = cls._parse_relevance(feature["relevance"])
            elif "match_code" in properties:
                relevance = cls._parse_relevance(properties["match_code"].get("confidence"))
            
            if relevance == 0.0:
                relevance = 0.9 if result_name else 0.5

            feature_type = properties.get("feature_type", "").lower()
            if not feature_type:
                feature_type = feature.get("type", "").lower()
            
            is_poi = feature_type == "poi" or "poi" in feature.get("id", "").lower()
            
            score = relevance
            if is_poi:
                score += 0.1
            
            # String similarity boost
            name_similarity = difflib.SequenceMatcher(None, original_location.lower(), result_name.lower()).ratio()
            score += (name_similarity * 0.2)

            context = properties.get("context", {})
            result_country = context.get("country", {}).get("country_code", "").upper()
            if result_country == country_hint.upper():
                score += 0.05

            logger.info(f"[GEOCODER] Feature: name='{result_name}', type={feature_type}, relevance={relevance:.2f}, similarity={name_similarity:.2f}, score={score:.2f}, country={result_country}")
            
            if score > best_relevance:
                best_relevance = score
                best_result = {
                    "feature": feature,
                    "relevance": relevance,
                    "score": score,
                    "country_code": result_country,
                    "is_poi": is_poi,
                    "feature_type": feature_type,
                    "name_similarity": name_similarity
                }

        if not best_result:
            return None

        feature = best_result["feature"]
        geometry = feature["geometry"]["coordinates"]
        properties = feature.get("properties", {})
        context = properties.get("context", {})
        
        relevance = best_result["relevance"]
        result_country = best_result["country_code"]
        feature_type = best_result.get("feature_type", "")
        result_city = context.get("place", {}).get("name")
        name_similarity = best_result["name_similarity"]
        
        geocoding_status = cls._determine_status(
            relevance, 
            result_country, 
            country_hint,
            query=original_location,
            feature_type=feature_type,
            city_hint=city_hint,
            city=result_city,
            name_similarity=name_similarity
        )
        
        country_defaults = cls._get_country_defaults(country_hint)
        
        result = GeocodeResult(
            lng=geometry[0],
            lat=geometry[1],
            relevance=relevance,
            full_address=properties.get("full_address", properties.get("name", "Unknown")),
            country_code=result_country,
            city=result_city,
            geocoding_status=geocoding_status,
            geocoding_metadata={
                "source": "mapbox",
                "query": original_location,
                "search_query": query,
                "country_hint": country_hint,
                "city_hint": city_hint,
                "selected_feature_type": feature_type,
                "name_similarity": round(name_similarity, 2),
                "types_filter": types_filter,
                "full_address": properties.get("full_address", properties.get("name", "Unknown")),
                "city": result_city
            }
        )

        lat, lng = geometry[1], geometry[0]
        bbox = country_defaults.get("bbox")
        if bbox and not (bbox["lat_min"] <= lat <= bbox["lat_max"] and bbox["lng_min"] <= lng <= bbox["lng_max"]):
            logger.warning(f"[GEOCODER] Geofence Violation for '{original_location}': ({lat}, {lng}) outside {country_hint}")
            result.geocoding_status = "failed"
            result.lat, result.lng = None, None

        if result.geocoding_status == "verified":
            cls._save_to_cache(original_location, result)
        
        logger.info(f"[GEOCODER] Decision: '{original_location}' -> status={geocoding_status} (Lat:{result.lat}, Lng:{result.lng})")
        return result

    @classmethod
    def _determine_status(cls, relevance: float, country_code: str, country_hint: str, query: str, feature_type: str = "", city_hint: Optional[str] = None, city: Optional[str] = None, name_similarity: float = 0.0) -> str:
        """Determine geocoding status with strict venue/city logic."""
        if country_code.upper() != country_hint.upper():
            return "failed"
        
        feature_type = feature_type.lower()
        
        if feature_type == "poi":
            if relevance >= 0.8 or (relevance >= 0.6 and name_similarity >= 0.5):
                return "verified"
            return "ambiguous"
        
        if feature_type == "address":
            return "verified" if relevance >= 0.85 else "ambiguous"

        if feature_type == "street":
            # If the original query had 'club', 'stage' etc, a street match is likely wrong unless similarity is very high
            venue_indicators = ["club", "stage", "theater", "theatre", "stadium", "arena", "venue", "live", "beach club"]
            if any(indicator in query.lower() for indicator in venue_indicators) and name_similarity < 0.8:
                return "failed"
            return "verified" if relevance >= 0.9 else "failed"

        if feature_type in ["place", "locality"]:
            # DANGER: City-level matches for venue names
            venue_indicators = ["club", "stage", "theater", "theatre", "stadium", "arena", "venue", "αρένα", "θέατρο", "στάδιο", "live", "beach club"]
            if any(indicator in query.lower() for indicator in venue_indicators):
                 logger.info(f"[GEOCODER] Rejected city match for potential venue: '{query}'")
                 return "failed"
            
            if relevance < 0.85:
                return "failed"
                
            if city_hint and city:
                country_defaults = COUNTRY_DEFAULTS.get(country_hint.upper(), {})
                city_aliases = country_defaults.get("city_aliases", {})
                city_hint_clean = city_hint.lower().strip()
                city_clean = city.lower().strip()
                hint_aliases = set(city_aliases.get(city_hint_clean, [city_hint_clean]))
                city_aliases_set = set(city_aliases.get(city_clean, [city_clean]))
                if not (hint_aliases & city_aliases_set) and city_hint_clean != city_clean:
                    return "failed"
            
            return "verified"
        
        return "failed"

    @classmethod
    def _enrich_query(cls, location_name: str, country_hint: str = "GR", city_hint: Optional[str] = None) -> str:
        """
        Enrich the query with city hint only (no country name - Mapbox filters by country param).
        Avoids duplicating city if location_name already contains it.
        """
        country_defaults = COUNTRY_DEFAULTS.get(country_hint.upper(), {})
        city_aliases = country_defaults.get("city_aliases", {})
        location_lower = location_name.lower() if location_name else ""
        
        parts = []
        seen = set()
        
        if location_name:
            parts.append(location_name)
            seen.add(location_lower)
        
        if city_hint:
            city_hint_lower = city_hint.lower().strip()
            alias_set = set(city_aliases.get(city_hint_lower, [city_hint_lower]))
            in_location = any(
                alias in location_lower 
                for alias in alias_set
            )
            if not in_location and city_hint_lower not in seen:
                parts.append(city_hint)
                seen.add(city_hint_lower)
        
        return ", ".join(parts)

    @classmethod
    def _boost_poi_query(cls, query: str) -> str:
        """No longer needed - venue logic is in _enrich_query."""
        return query

    @classmethod
    def _get_country_defaults(cls, country_hint: str) -> Dict[str, Any]:
        """Get country defaults including center coords and bbox."""
        return COUNTRY_DEFAULTS.get(country_hint.upper(), {
            "center": {"lat": 37.9838, "lng": 23.7275},
            "bbox": {"lat_min": 34.0, "lat_max": 42.0, "lng_min": 19.0, "lng_max": 29.0},
        })

    @classmethod
    def _extract_city_from_query(cls, query: str, country_hint: str) -> Optional[str]:
        """Extract a known city name from a query string (e.g., 'Block 33 Thessaloniki' -> 'Thessaloniki')."""
        if not query:
            return None
        country_defaults = cls._get_country_defaults(country_hint)
        known_cities = country_defaults.get("cities", {})
        city_keywords = country_defaults.get("city_keywords", [])
        query_lower = query.lower()
        for keyword in city_keywords:
            if keyword.lower() in query_lower:
                for city_name in known_cities:
                    if keyword.lower() == city_name.lower():
                        return city_name
        for city_name in known_cities:
            if city_name.lower() in query_lower:
                return city_name
        return None

    @staticmethod
    def _get_country_bbox(country_hint: str) -> Optional[Dict[str, float]]:
        """Get bounding box for a country code."""
        defaults = COUNTRY_DEFAULTS.get(country_hint.upper())
        if defaults:
            return defaults.get("bbox")
        return None

    @classmethod
    def _create_fuzzy_query(cls, location_name: str) -> str:
        """Create a fuzzy query by removing special characters and event suffixes."""
        fuzzy = location_name
        
        while True:
            changed = False
            for suffix in cls.FUZZY_SUFFIXES_TO_REMOVE:
                if fuzzy.endswith(f" {suffix}"):
                    fuzzy = fuzzy[:-(len(suffix) + 1)].strip()
                    changed = True
                    break
                elif fuzzy.endswith(f" - {suffix}"):
                    fuzzy = fuzzy[:-(len(suffix) + 3)].strip()
                    changed = True
                    break
            if not changed:
                break
        
        fuzzy = re.sub(r"[^\w\s,]", "", fuzzy)
        fuzzy = re.sub(r"\s+", " ", fuzzy).strip()
        
        if len(fuzzy) < 3:
            fuzzy = location_name
        
        return fuzzy

    @staticmethod
    def _check_cache(name: str, country_code: Optional[str]) -> Optional[Venue]:
        """Looks up a venue in the local database."""
        with Session(engine) as session:
            statement = select(Venue).where(Venue.name == name)
            if country_code:
                statement = statement.where(Venue.country_code == country_code.upper())
            
            return session.exec(statement).first()

    @staticmethod
    def _save_to_cache(name: str, result: GeocodeResult):
        """Saves a new geocoding result to the local database."""
        if result.lat is None or result.lng is None:
            logger.debug(f"[GEOCODER] Skipping cache for '{name}': lat or lng is None")
            return
        try:
            with Session(engine) as session:
                venue = Venue(
                    name=name,
                    country_code=result.country_code.upper(),
                    city=result.city,
                    lat=result.lat,
                    lng=result.lng,
                    full_address=result.full_address,
                    relevance=result.relevance
                )
                session.add(venue)
                session.commit()
        except Exception as e:
            logger.warning(f"Failed to cache venue '{name}': {e}")

    @classmethod
    async def batch_geocode_pending_events(cls, batch_size: int = 50) -> Dict[str, int]:
        """
        Batch geocode all pending_events that need geocoding.
        Updates location and geocoding fields for events with location_name.
        
        Returns dict with counts: {'updated': n, 'failed': n, 'skipped': n}
        """
        stats = {"updated": 0, "failed": 0, "skipped": 0}
        processed_ids = set()
        
        while True:
            with Session(engine) as session:
                statement = (
                    select(PendingEvent)
                    .where(PendingEvent.location_name.isnot(None))
                    .where(PendingEvent.geocoding_status == "failed") # Initial or failed state
                    .where(PendingEvent.id.not_in(processed_ids))
                    .limit(batch_size)
                )
                pending_events = session.exec(statement).all()
            
            if not pending_events:
                break
            
            for pending in pending_events:
                processed_ids.add(pending.id)
                location_name = pending.location_name
                if not location_name:
                    stats["skipped"] += 1
                    continue
                
                logger.info(f"[BATCH] Processing pending_event id={pending.id} | location_name: '{location_name}'")
                geo_result = await cls.get_coordinates(location_name, "GR")
                
                with Session(engine) as session:
                    pending_db = session.get(PendingEvent, pending.id)
                    if pending_db:
                        if geo_result and geo_result.lat is not None and geo_result.lng is not None:
                            wkt_string = f"POINT({geo_result.lng} {geo_result.lat})"
                            logger.info(f"[BATCH] DB Write: pending_event id={pending.id} | WKT: {wkt_string} | confidence: {geo_result.relevance} | status: {geo_result.geocoding_status}")
                            pending_db.confidence_score = geo_result.relevance
                            pending_db.geocoding_status = geo_result.geocoding_status
                            pending_db.geocoding_metadata = geo_result.geocoding_metadata
                            pending_db.location = WKTElement(wkt_string, srid=4326)
                            stats["updated"] += 1
                        else:
                            logger.info(f"[BATCH] DB Write: pending_event id={pending.id} | status: failed (no valid coordinates)")
                            pending_db.geocoding_status = "failed"
                            pending_db.confidence_score = None
                            pending_db.geocoding_metadata = {"reason": "geocoding_returned_none_or_invalid"}
                            stats["failed"] += 1
                        
                        session.add(pending_db)
                        session.commit()
                
                await asyncio.sleep(0.1)
        
        return stats

    @classmethod
    def purge_cache(cls, venue_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Purge venues cache. If venue_name is provided, deletes only that venue.
        Otherwise purges all venues.
        
        Returns dict with counts: {'deleted': n}
        """
        try:
            with Session(engine) as session:
                if venue_name:
                    deleted = session.exec(
                        select(Venue).where(Venue.name == venue_name)
                    ).all()
                    count = len(deleted)
                    for v in deleted:
                        session.delete(v)
                    logger.info(f"[GEOCODER] Cache purged: deleted {count} venues matching '{venue_name}'")
                else:
                    all_venues = session.exec(select(Venue)).all()
                    count = len(all_venues)
                    for v in all_venues:
                        session.delete(v)
                    logger.info(f"[GEOCODER] Cache purged: deleted all {count} venues")
                
                session.commit()
                return {"deleted": count}
        except Exception as e:
            logger.error(f"[GEOCODER] Cache purge failed: {e}")
            return {"deleted": 0, "error": str(e)}
