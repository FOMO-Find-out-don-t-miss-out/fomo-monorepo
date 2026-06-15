import difflib
import logging

from app.core.geography_constants import COUNTRY_DEFAULTS
from geoalchemy2.elements import WKTElement
from sqlmodel import Session, select

from packages.domain.models import Place, PlaceVerificationStatus

logger = logging.getLogger(__name__)


class PlaceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_name(
        self, name: str, country_code: str, city_hint: str | None = None
    ) -> Place | None:
        """Looks up a place in the local database with exact/fuzzy matching and city validation."""
        country_code = country_code.upper()

        statement = select(Place).where(Place.name == name, Place.country_code == country_code)
        place = self.session.exec(statement).first()

        if place:
            if self._is_city_match(place, city_hint):
                return place
            logger.info(
                f"[REPOSITORY] Exact Cache Invalidation: '{name}' in DB is in '{place.city}', "
                f"but hint is '{city_hint}'"
            )

        statement = select(Place).where(Place.country_code == country_code)
        all_places = self.session.exec(statement).all()

        best_match = None
        best_score = 0.0

        name_lower = name.lower()
        for p in all_places:
            score = difflib.SequenceMatcher(None, name_lower, p.name.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = p

        if best_score > 0.9 and best_match:
            if self._is_city_match(best_match, city_hint):
                logger.info(
                    f"[REPOSITORY] Fuzzy Cache Hit: '{name}' matched '{best_match.name}' "
                    f"with score {best_score:.2f}"
                )
                return best_match
            logger.info(
                f"[REPOSITORY] Fuzzy Cache Invalidation: '{name}' matched '{best_match.name}' "
                f"but city mismatch ('{best_match.city}' vs '{city_hint}')"
            )

        return None

    def save_place(
        self,
        name: str,
        country_code: str,
        lat: float,
        lng: float,
        full_address: str,
        relevance: float,
        city: str | None = None,
    ) -> Place:
        """Saves a new place or updates an existing one if not manually verified."""
        country_code = country_code.upper()

        statement = select(Place).where(Place.name == name, Place.country_code == country_code)
        existing = self.session.exec(statement).first()

        if existing:
            if existing.verification_status == PlaceVerificationStatus.manually_verified:
                logger.debug(f"[REPOSITORY] Skipping update for manually verified place: {name}")
                return existing

            existing.lat = lat
            existing.lng = lng
            existing.full_address = full_address
            existing.relevance = relevance
            existing.normalized_name = name.lower()
            existing.location = WKTElement(f"POINT({lng} {lat})", srid=4326)
            existing.city = city
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing

        new_place = Place(
            name=name,
            country_code=country_code,
            city=city,
            lat=lat,
            lng=lng,
            full_address=full_address,
            relevance=relevance,
            location=WKTElement(f"POINT({lng} {lat})", srid=4326),
        )
        self.session.add(new_place)
        self.session.commit()
        self.session.refresh(new_place)
        return new_place

    def save_unresolved_place(
        self,
        name: str,
        country_code: str,
        source_provider: str | None = None,
    ) -> Place:
        """Creates or returns an existing unresolved place candidate.

        Used when geocoding fails: the place is recorded for moderator review
        with no coordinates.  Skips the update step so that a manually-verified
        place is never downgraded by a failed geocoding attempt.
        """
        country_code = country_code.upper()
        statement = select(Place).where(Place.name == name, Place.country_code == country_code)
        existing = self.session.exec(statement).first()
        if existing:
            return existing

        new_place = Place(
            name=name,
            country_code=country_code,
            match_confidence=0.0,
            verification_status=PlaceVerificationStatus.unverified,
            source_provider=source_provider,
        )
        self.session.add(new_place)
        self.session.commit()
        self.session.refresh(new_place)
        logger.info(
            "[REPOSITORY] Created unresolved place candidate: '%s' (%s)", name, country_code
        )
        return new_place

    def delete_places(self, name: str | None = None) -> int:
        """Deletes places by name, or all places if name is None."""
        statement = select(Place)
        if name:
            statement = statement.where(Place.name == name)

        places = self.session.exec(statement).all()
        count = len(places)
        for p in places:
            self.session.delete(p)
        self.session.commit()
        return count

    def _is_city_match(self, place: Place, city_hint: str | None) -> bool:
        if not city_hint or not place.city:
            return True

        hint_clean = city_hint.lower().strip()
        p_city_clean = place.city.lower().strip()

        country_defaults = COUNTRY_DEFAULTS.get(place.country_code, {})
        city_aliases = country_defaults.get("city_aliases", {})

        hint_aliases = set(city_aliases.get(hint_clean, [hint_clean]))
        p_aliases = set(city_aliases.get(p_city_clean, [p_city_clean]))

        if hint_aliases & p_aliases:
            return True

        return difflib.SequenceMatcher(None, hint_clean, p_city_clean).ratio() > 0.8

    # Backward-compat method aliases — use canonical names for new code
    save_venue = save_place
    delete_venues = delete_places
