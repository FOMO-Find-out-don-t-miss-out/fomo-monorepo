import logging
import difflib
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
from app.models.venue import Venue
from app.core.geography_constants import COUNTRY_DEFAULTS

logger = logging.getLogger(__name__)

class VenueRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_name(self, name: str, country_code: str, city_hint: Optional[str] = None) -> Optional[Venue]:
        """Looks up a venue in the local database with exact/fuzzy matching and city validation."""
        country_code = country_code.upper()
        
        # 1. Try exact match first
        statement = select(Venue).where(Venue.name == name, Venue.country_code == country_code)
        venue = self.session.exec(statement).first()

        if venue:
            if self._is_city_match(venue, city_hint):
                return venue
            logger.info(f"[REPOSITORY] Exact Cache Invalidation: '{name}' in DB is in '{venue.city}', but hint is '{city_hint}'")

        # 2. Try fuzzy matching
        statement = select(Venue).where(Venue.country_code == country_code)
        all_venues = self.session.exec(statement).all()
        
        best_match = None
        best_score = 0.0
        
        name_lower = name.lower()
        for v in all_venues:
            score = difflib.SequenceMatcher(None, name_lower, v.name.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = v
        
        if best_score > 0.9:
            if self._is_city_match(best_match, city_hint):
                logger.info(f"[REPOSITORY] Fuzzy Cache Hit: '{name}' matched '{best_match.name}' with score {best_score:.2f}")
                return best_match
            logger.info(f"[REPOSITORY] Fuzzy Cache Invalidation: '{name}' matched '{best_match.name}' but city mismatch ('{best_match.city}' vs '{city_hint}')")
        
        return None

    def save_venue(self, name: str, country_code: str, lat: float, lng: float, full_address: str, relevance: float, city: Optional[str] = None) -> Venue:
        """Saves a new venue or updates an existing one if not manually verified."""
        country_code = country_code.upper()
        
        statement = select(Venue).where(Venue.name == name, Venue.country_code == country_code)
        existing = self.session.exec(statement).first()
        
        if existing:
            # Respect manual verification
            if existing.is_manually_verified:
                logger.debug(f"[REPOSITORY] Skipping update for manually verified venue: {name}")
                return existing

            existing.lat = lat
            existing.lng = lng
            existing.full_address = full_address
            existing.relevance = relevance
            existing.city = city
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing
        else:
            new_venue = Venue(
                name=name,
                country_code=country_code,
                city=city,
                lat=lat,
                lng=lng,
                full_address=full_address,
                relevance=relevance
            )
            self.session.add(new_venue)
            self.session.commit()
            self.session.refresh(new_venue)
            return new_venue

    def delete_venues(self, name: Optional[str] = None) -> int:
        """Deletes venues by name or all venues if name is None."""
        statement = select(Venue)
        if name:
            statement = statement.where(Venue.name == name)
        
        venues = self.session.exec(statement).all()
        count = len(venues)
        for v in venues:
            self.session.delete(v)
        self.session.commit()
        return count

    def _is_city_match(self, venue: Venue, city_hint: Optional[str]) -> bool:
        """Helper to validate if venue city matches the provided hint."""
        if not city_hint or not venue.city:
            return True
        
        hint_clean = city_hint.lower().strip()
        v_city_clean = venue.city.lower().strip()
        
        # Check aliases from geography constants
        country_defaults = COUNTRY_DEFAULTS.get(venue.country_code, {})
        city_aliases = country_defaults.get("city_aliases", {})
        
        hint_aliases = set(city_aliases.get(hint_clean, [hint_clean]))
        v_aliases = set(city_aliases.get(v_city_clean, [v_city_clean]))
        
        if (hint_aliases & v_aliases):
            return True
        
        # Fallback to fuzzy match for city names
        return difflib.SequenceMatcher(None, hint_clean, v_city_clean).ratio() > 0.8
