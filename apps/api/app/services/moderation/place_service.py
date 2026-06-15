import logging
from typing import Any
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlmodel import Session, and_, select

from packages.domain.models import Event, PendingEvent, Place, PlaceVerificationStatus

logger = logging.getLogger(__name__)


class PlaceModerationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def update_place(self, place_id: UUID, **kwargs: Any) -> Place | None:
        """Updates a place and syncs linked events if critical fields change."""
        place = self.session.get(Place, place_id)
        if not place:
            return None

        old_name = place.name.strip()
        new_name = kwargs.get("name", old_name).strip()
        city = kwargs.get("city", place.city)
        country_code = kwargs.get("country_code", place.country_code)

        if new_name != old_name or city != place.city:
            existing = self.session.exec(
                select(Place).where(
                    and_(
                        Place.name == new_name,
                        Place.city == city,
                        Place.country_code == country_code,
                        Place.id != place_id,
                    )
                )
            ).first()
            if existing:
                return None

        for k, v in kwargs.items():
            setattr(place, k, v)
        if "name" in kwargs:
            place.normalized_name = new_name.lower()

        self.session.add(place)

        if any(k in kwargs for k in ["lat", "lng", "name", "full_address", "verification_status"]):
            lat = kwargs.get("lat", place.lat)
            lng = kwargs.get("lng", place.lng)

            if lat is not None and lng is not None:
                status = (
                    "verified"
                    if place.verification_status == PlaceVerificationStatus.manually_verified
                    else "ambiguous"
                )
                wkt_str = f"POINT({lng} {lat})"
                place.location = WKTElement(wkt_str, srid=4326)

                statement_pending = select(PendingEvent).where(
                    PendingEvent.location_name == old_name
                )
                for ev in self.session.exec(statement_pending).all():
                    ev.location_name = new_name
                    ev.location = WKTElement(wkt_str, srid=4326)
                    ev.geocoding_status = status
                    ev.geocoding_metadata = {
                        "source": "manual_sync",
                        "full_address": kwargs.get("full_address", place.full_address),
                        "city": kwargs.get("city", place.city),
                    }
                    self.session.add(ev)

                statement_events = select(Event).where(Event.location_name == old_name)
                for ev in self.session.exec(statement_events).all():
                    ev.location_name = new_name
                    ev.location = WKTElement(wkt_str, srid=4326)
                    self.session.add(ev)
            elif "name" in kwargs:
                statement_pending = select(PendingEvent).where(
                    PendingEvent.location_name == old_name
                )
                for ev in self.session.exec(statement_pending).all():
                    ev.location_name = new_name
                    self.session.add(ev)

                statement_events = select(Event).where(Event.location_name == old_name)
                for ev in self.session.exec(statement_events).all():
                    ev.location_name = new_name
                    self.session.add(ev)

        self.session.commit()
        self.session.refresh(place)
        return place

    def get_places(
        self,
        search_query: str | None = None,
        only_unverified: bool = False,
    ) -> list[Place]:
        """Fetches places with optional filtering."""
        statement = select(Place).order_by(Place.name)
        if search_query:
            statement = statement.where(Place.name.ilike(f"%{search_query}%"))
        if only_unverified:
            statement = statement.where(
                Place.verification_status != PlaceVerificationStatus.manually_verified
            )
        return list(self.session.exec(statement).all())

    def merge_places(self, source_place_id: UUID, target_place_id: UUID) -> bool:
        """Merges source place into target, updating all linked events."""
        source = self.session.get(Place, source_place_id)
        target = self.session.get(Place, target_place_id)

        if not source or not target:
            return False

        source_name = source.name.strip()
        target_name = target.name.strip()
        has_coords = target.lat is not None and target.lng is not None
        target_wkt = f"POINT({target.lng} {target.lat})" if has_coords else None
        geocoding_status = (
            "verified"
            if target.verification_status == PlaceVerificationStatus.manually_verified
            else "ambiguous"
        ) if has_coords else "failed"

        for ev in self.session.exec(
            select(PendingEvent).where(PendingEvent.location_name == source_name)
        ).all():
            ev.location_name = target_name
            if target_wkt:
                ev.location = WKTElement(target_wkt, srid=4326)
            ev.geocoding_status = geocoding_status
            self.session.add(ev)

        for ev in self.session.exec(select(Event).where(Event.location_name == source_name)).all():
            ev.location_name = target_name
            if target_wkt:
                ev.location = WKTElement(target_wkt, srid=4326)
            self.session.add(ev)

        self.session.delete(source)
        self.session.commit()
        return True

    def delete_place_and_unlink_events(self, place_id: UUID) -> bool:
        """Deletes a place and unlinks (sets location to NULL) all related events."""
        place = self.session.get(Place, place_id)
        if not place:
            return False

        place_name = place.name.strip()

        for ev in self.session.exec(
            select(PendingEvent).where(PendingEvent.location_name == place_name)
        ).all():
            ev.location = None
            ev.geocoding_status = "failed"
            ev.confidence_score = None
            ev.geocoding_metadata = {}
            self.session.add(ev)

        for ev in self.session.exec(select(Event).where(Event.location_name == place_name)).all():
            ev.location = None
            self.session.add(ev)

        self.session.delete(place)
        self.session.commit()
        return True

    # Backward-compat method aliases — use canonical names for new code
    update_venue_record = update_place
    get_venues = get_places
    merge_venues = merge_places
    delete_venue_and_unlink_events = delete_place_and_unlink_events
