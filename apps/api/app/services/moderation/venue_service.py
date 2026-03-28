import logging
from typing import Any
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlmodel import Session, and_, select

from app.models.event import Event, PendingEvent
from app.models.venue import Venue

logger = logging.getLogger(__name__)


class VenueModerationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def update_venue_record(self, venue_id: UUID, **kwargs: Any) -> Venue | None:
        """Updates a venue and syncs linked events if critical fields change."""
        venue = self.session.get(Venue, venue_id)
        if not venue:
            return None

        old_name = venue.name.strip()
        new_name = kwargs.get("name", old_name).strip()
        city = kwargs.get("city", venue.city)
        country_code = kwargs.get("country_code", venue.country_code)

        # Check for collisions: Can't have same name in same city
        if new_name != old_name or city != venue.city:
            existing = self.session.exec(
                select(Venue).where(
                    and_(
                        Venue.name == new_name,
                        Venue.city == city,
                        Venue.country_code == country_code,
                        Venue.id != venue_id,
                    )
                )
            ).first()
            if existing:
                return None

        for k, v in kwargs.items():
            setattr(venue, k, v)

        self.session.add(venue)

        # Sync to events if location or name changed
        if any(k in kwargs for k in ["lat", "lng", "name", "full_address", "is_manually_verified"]):
            lat = kwargs.get("lat", venue.lat)
            lng = kwargs.get("lng", venue.lng)
            status = (
                "verified"
                if kwargs.get("is_manually_verified", venue.is_manually_verified)
                else "ambiguous"
            )
            wkt_str = f"POINT({lng} {lat})"

            # Sync PendingEvent
            statement_pending = select(PendingEvent).where(PendingEvent.location_name == old_name)
            linked_pending = self.session.exec(statement_pending).all()
            for ev in linked_pending:
                ev.location_name = new_name
                ev.location = WKTElement(wkt_str, srid=4326)
                ev.geocoding_status = status
                ev.geocoding_metadata = {
                    "source": "manual_sync",
                    "full_address": kwargs.get("full_address", venue.full_address),
                    "city": kwargs.get("city", venue.city),
                }
                self.session.add(ev)

            # Sync published Event
            statement_events = select(Event).where(Event.location_name == old_name)
            linked_events = self.session.exec(statement_events).all()
            for ev in linked_events:
                ev.location_name = new_name
                ev.location = WKTElement(wkt_str, srid=4326)
                self.session.add(ev)

        self.session.commit()
        self.session.refresh(venue)
        return venue

    def merge_venues(self, source_venue_id: UUID, target_venue_id: UUID) -> bool:
        """Merges source venue into target venue, updating all linked events."""
        source = self.session.get(Venue, source_venue_id)
        target = self.session.get(Venue, target_venue_id)

        if not source or not target:
            return False

        source_name = source.name.strip()
        target_name = target.name.strip()
        target_wkt = f"POINT({target.lng} {target.lat})"

        statement_pending = select(PendingEvent).where(PendingEvent.location_name == source_name)
        linked_pending = self.session.exec(statement_pending).all()
        for ev in linked_pending:
            ev.location_name = target_name
            ev.location = WKTElement(target_wkt, srid=4326)
            ev.geocoding_status = "verified" if target.is_manually_verified else "ambiguous"
            self.session.add(ev)

        statement_events = select(Event).where(Event.location_name == source_name)
        linked_events = self.session.exec(statement_events).all()
        for ev in linked_events:
            ev.location_name = target_name
            ev.location = WKTElement(target_wkt, srid=4326)
            self.session.add(ev)

        self.session.delete(source)
        self.session.commit()
        return True

    def delete_venue_and_unlink_events(self, venue_id: UUID) -> bool:
        """Deletes venue and unlinks (sets location to NULL) all related events."""
        venue = self.session.get(Venue, venue_id)
        if not venue:
            return False

        venue_name = venue.name.strip()

        statement_pending = select(PendingEvent).where(PendingEvent.location_name == venue_name)
        linked_pending = self.session.exec(statement_pending).all()
        for ev in linked_pending:
            ev.location = None
            ev.geocoding_status = "failed"
            ev.confidence_score = None
            ev.geocoding_metadata = {}
            self.session.add(ev)

        statement_events = select(Event).where(Event.location_name == venue_name)
        linked_events = self.session.exec(statement_events).all()
        for ev in linked_events:
            ev.location = None
            self.session.add(ev)

        self.session.delete(venue)
        self.session.commit()
        return True
