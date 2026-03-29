import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from sqlmodel import Session, and_, select

from packages.domain.models import Event, PendingEvent, Venue

logger = logging.getLogger(__name__)


class ModerationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def approve_events(self, event_ids: list[UUID]) -> int:
        """Approves a list of pending events, publishing them and syncing venues."""
        count = 0
        for eid in event_ids:
            pending = self.session.get(PendingEvent, eid)
            if pending and pending.status == "pending":
                # 1. Create the primary live event
                primary_id = uuid4()
                live_event = Event(
                    id=primary_id,
                    title=pending.title,
                    location=pending.location,
                    start_time=pending.start_time,
                    end_time=pending.end_time,
                    category=pending.category,
                    sub_category=pending.sub_category,
                    hype_score=pending.hype_score,
                    ticket_url=pending.ticket_url,
                    source_url=pending.source_url,
                    source_provider=pending.source_provider,
                    ingestion_method=pending.ingestion_method,
                    event_metadata=pending.event_metadata,
                    location_name=pending.location_name,
                    country_code=pending.country_code,
                    parent_id=pending.parent_id or primary_id,
                    tags=pending.tags,
                    geocoding_status=pending.geocoding_status,
                    geocoding_metadata=pending.geocoding_metadata,
                )
                self.session.add(live_event)

                # 2. Handle Venue sync on approval if geocoded
                if (
                    pending.location_name
                    and pending.geocoding_status == "verified"
                    and pending.location
                ):
                    shape = to_shape(pending.location)
                    city = pending.geocoding_metadata.get("city")
                    venue = self.session.exec(
                        select(Venue).where(
                            and_(
                                Venue.name == pending.location_name.strip(),
                                Venue.city == city,
                                Venue.country_code == pending.country_code,
                            )
                        )
                    ).first()

                    if not venue:
                        new_venue = Venue(
                            name=pending.location_name.strip(),
                            country_code=pending.country_code or "GR",
                            city=city,
                            lat=shape.y,
                            lng=shape.x,
                            full_address=pending.geocoding_metadata.get("full_address")
                            or pending.location_name,
                            relevance=pending.confidence_score or 1.0,
                        )
                        self.session.add(new_venue)

                pending.status = "published"
                self.session.add(pending)
                count += 1

        self.session.commit()
        return count

    def reject_events(self, event_ids: list[UUID]) -> int:
        """Rejects a list of pending events by deleting them."""
        count = 0
        for eid in event_ids:
            pending = self.session.get(PendingEvent, eid)
            if pending:
                self.session.delete(pending)
                count += 1
        self.session.commit()
        return count

    def update_pending_event(self, event_id: UUID, **kwargs: Any) -> PendingEvent | None:
        """Updates a pending event and optionally syncs venue/other events."""
        pending = self.session.get(PendingEvent, event_id)
        if not pending:
            return None

        # Logic from dashboard: sync location_name across events and venues
        old_name = pending.location_name
        new_name = kwargs.get("location_name")

        if new_name is not None:
            new_name = new_name.strip()
            kwargs["location_name"] = new_name

        for k, v in kwargs.items():
            setattr(pending, k, v)

        if new_name and old_name and new_name != old_name.strip():
            old_name_clean = old_name.strip()

            # Update Venue table if a venue with old_name exists
            venue = self.session.exec(
                select(Venue).where(
                    and_(Venue.name == old_name_clean, Venue.country_code == pending.country_code)
                )
            ).first()
            if venue:
                venue.name = new_name
                self.session.add(venue)

            # Update all other pending events that had the exact same old location name
            statement = select(PendingEvent).where(
                PendingEvent.location_name == old_name_clean, PendingEvent.id != pending.id
            )
            linked_pending = self.session.exec(statement).all()
            for p in linked_pending:
                p.location_name = new_name
                self.session.add(p)

        self.session.add(pending)
        self.session.commit()
        self.session.refresh(pending)
        return pending

    def batch_update_location_by_name(
        self,
        target_name: str,
        location_wkt: str,
        status: str,
        confidence: float,
        metadata: dict[str, Any],
    ) -> None:
        """Syncs location to all events and pending events with the same location name."""
        target_clean = target_name.strip()

        # Sync PendingEvent
        statement_pending = select(PendingEvent).where(PendingEvent.location_name == target_clean)
        all_pending = self.session.exec(statement_pending).all()
        for p in all_pending:
            p.location = WKTElement(location_wkt, srid=4326)
            p.geocoding_status = status
            p.confidence_score = confidence
            p.geocoding_metadata = metadata
            self.session.add(p)

        # Sync published Event
        statement_events = select(Event).where(Event.location_name == target_clean)
        all_events = self.session.exec(statement_events).all()
        for e in all_events:
            e.location = WKTElement(location_wkt, srid=4326)
            self.session.add(e)

        self.session.commit()

    def add_occurrence(self, event_id: UUID, start_time: datetime) -> PendingEvent | None:
        """Creates a new PendingEvent as an occurrence of an existing one."""
        curr = self.session.get(PendingEvent, event_id)
        if not curr:
            return None

        parent_id = curr.parent_id or curr.id

        # Ensure parent has its parent_id set
        if not curr.parent_id:
            curr.parent_id = parent_id
            self.session.add(curr)

        new_pending = PendingEvent(
            title=curr.title,
            location=curr.location,
            location_name=curr.location_name,
            country_code=curr.country_code,
            start_time=start_time,
            category=curr.category,
            hype_score=curr.hype_score,
            ticket_url=curr.ticket_url,
            source_url=curr.source_url,
            event_metadata=curr.event_metadata,
            confidence_score=curr.confidence_score,
            geocoding_status=curr.geocoding_status,
            geocoding_metadata=curr.geocoding_metadata,
            status="pending",
            parent_id=parent_id,
            tags=curr.tags,
        )
        self.session.add(new_pending)
        self.session.commit()
        self.session.refresh(new_pending)
        return new_pending

    def get_published_events(self, location_name: str | None = None) -> list[Event]:
        """Fetches published events from the events table."""
        statement = select(Event)
        if location_name:
            statement = statement.where(Event.location_name == location_name)
        statement = statement.order_by(Event.start_time.desc())
        return list(self.session.exec(statement).all())

    def unpublish_event(self, event_id: UUID) -> bool:
        """Unpublishes an event by updating its status in pending_events."""
        event = self.session.get(Event, event_id)
        if not event:
            return False

        # 1. Update status in pending_events (if exists, matching by title and start_time)
        statement = select(PendingEvent).where(
            PendingEvent.title == event.title, PendingEvent.start_time == event.start_time
        )
        pending = self.session.exec(statement).first()
        if pending:
            pending.status = "pending"
            self.session.add(pending)

        # 2. Delete from events table
        self.session.delete(event)
        self.session.commit()
        return True

    def update_published_event(self, event_id: UUID, **kwargs: Any) -> Event | None:
        """Updates a published event and optionally syncs with its pending counterpart."""
        event = self.session.get(Event, event_id)
        if not event:
            return None

        # Logic: update event and also update its matching pending_event if it exists
        old_title = event.title
        old_start = event.start_time

        for k, v in kwargs.items():
            setattr(event, k, v)

        # Sync to pending_events if title/start_time changed or just update other fields
        statement = select(PendingEvent).where(
            PendingEvent.title == old_title, PendingEvent.start_time == old_start
        )
        pending = self.session.exec(statement).first()
        if pending:
            for k, v in kwargs.items():
                setattr(pending, k, v)
            self.session.add(pending)

        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event
