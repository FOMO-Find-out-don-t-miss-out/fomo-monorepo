from uuid import UUID

from sqlmodel import Session, select

from packages.domain.models import Event, EventRelationship, RelationshipType
from packages.domain.models.event import EventStatus, EventVisibility


class EventRelationshipService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _get_public_event(self, event_id: UUID) -> Event | None:
        statement = (
            select(Event)
            .where(Event.id == event_id)
            .where(Event.status == EventStatus.live)
            .where(Event.visibility == EventVisibility.public)
            .where(Event.removed_at.is_(None))
        )
        return self.session.exec(statement).first()

    def mark_relationship(
        self,
        *,
        user_id: UUID,
        event_id: UUID,
        relationship_type: RelationshipType,
    ) -> EventRelationship | None:
        if self._get_public_event(event_id) is None:
            return None

        statement = select(EventRelationship).where(
            EventRelationship.user_id == user_id,
            EventRelationship.event_id == event_id,
            EventRelationship.relationship_type == relationship_type,
        )
        existing = self.session.exec(statement).first()
        if existing:
            return existing

        relationship = EventRelationship(
            user_id=user_id,
            event_id=event_id,
            relationship_type=relationship_type,
        )
        self.session.add(relationship)
        self.session.commit()
        self.session.refresh(relationship)
        return relationship

    def remove_relationship(
        self,
        *,
        user_id: UUID,
        event_id: UUID,
        relationship_type: RelationshipType,
    ) -> bool:
        if self._get_public_event(event_id) is None:
            return False

        statement = select(EventRelationship).where(
            EventRelationship.user_id == user_id,
            EventRelationship.event_id == event_id,
            EventRelationship.relationship_type == relationship_type,
        )
        relationship = self.session.exec(statement).first()
        if relationship is None:
            return True

        self.session.delete(relationship)
        self.session.commit()
        return True

    def _list_events_for_type(
        self, *, user_id: UUID, relationship_type: RelationshipType
    ) -> list[Event]:
        statement = (
            select(Event)
            .join(EventRelationship, EventRelationship.event_id == Event.id)
            .where(EventRelationship.user_id == user_id)
            .where(EventRelationship.relationship_type == relationship_type)
            .where(Event.status == EventStatus.live)
            .where(Event.visibility == EventVisibility.public)
            .where(Event.removed_at.is_(None))
            .order_by(Event.start_time)
        )
        return list(self.session.exec(statement).all())

    def list_saved_events(self, *, user_id: UUID) -> list[Event]:
        return self._list_events_for_type(user_id=user_id, relationship_type=RelationshipType.saved)

    def list_interested_events(self, *, user_id: UUID) -> list[Event]:
        return self._list_events_for_type(
            user_id=user_id, relationship_type=RelationshipType.interested
        )

    def list_going_events(self, *, user_id: UUID) -> list[Event]:
        return self._list_events_for_type(user_id=user_id, relationship_type=RelationshipType.going)
