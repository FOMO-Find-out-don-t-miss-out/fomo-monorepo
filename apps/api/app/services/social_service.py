from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, or_, select

from packages.domain.models import Organizer, OrganizerFollower, UserConnection
from packages.domain.models.social import ConnectionStatus


class SocialService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- internal helpers ---

    def _get_connection(
        self, requester_user_id: UUID, addressee_user_id: UUID
    ) -> UserConnection | None:
        return self.session.exec(
            select(UserConnection)
            .where(UserConnection.requester_user_id == requester_user_id)
            .where(UserConnection.addressee_user_id == addressee_user_id)
        ).first()

    def _get_organizer(self, organizer_id: UUID) -> Organizer | None:
        return self.session.get(Organizer, organizer_id)

    def _get_follower_row(
        self, user_id: UUID, organizer_id: UUID
    ) -> OrganizerFollower | None:
        return self.session.exec(
            select(OrganizerFollower)
            .where(OrganizerFollower.user_id == user_id)
            .where(OrganizerFollower.organizer_id == organizer_id)
        ).first()

    # --- user connections ---

    def request_connection(
        self,
        *,
        requester_user_id: UUID,
        addressee_user_id: UUID,
    ) -> UserConnection | None:
        if requester_user_id == addressee_user_id:
            return None

        # Idempotent: exact pair already exists
        existing = self._get_connection(requester_user_id, addressee_user_id)
        if existing:
            return existing

        # Check reverse direction
        reverse = self._get_connection(addressee_user_id, requester_user_id)
        if reverse is not None:
            if reverse.status == ConnectionStatus.blocked:
                return None
            if reverse.status == ConnectionStatus.accepted:
                return reverse
            if reverse.status == ConnectionStatus.pending:
                # Both parties want to connect — accept
                reverse.status = ConnectionStatus.accepted
                reverse.updated_at = datetime.now(UTC)
                self.session.add(reverse)
                self.session.commit()
                self.session.refresh(reverse)
                return reverse
            # rejected: allow new request to proceed

        connection = UserConnection(
            requester_user_id=requester_user_id,
            addressee_user_id=addressee_user_id,
            status=ConnectionStatus.pending,
        )
        self.session.add(connection)
        self.session.commit()
        self.session.refresh(connection)
        return connection

    def accept_connection(
        self,
        *,
        requester_user_id: UUID,
        addressee_user_id: UUID,
    ) -> UserConnection | None:
        connection = self._get_connection(requester_user_id, addressee_user_id)
        if connection is None or connection.status != ConnectionStatus.pending:
            return None

        connection.status = ConnectionStatus.accepted
        connection.updated_at = datetime.now(UTC)
        self.session.add(connection)
        self.session.commit()
        self.session.refresh(connection)
        return connection

    def reject_connection(
        self,
        *,
        requester_user_id: UUID,
        addressee_user_id: UUID,
    ) -> UserConnection | None:
        connection = self._get_connection(requester_user_id, addressee_user_id)
        if connection is None or connection.status != ConnectionStatus.pending:
            return None

        connection.status = ConnectionStatus.rejected
        connection.updated_at = datetime.now(UTC)
        self.session.add(connection)
        self.session.commit()
        self.session.refresh(connection)
        return connection

    def block_connection(
        self,
        *,
        blocker_user_id: UUID,
        blocked_user_id: UUID,
    ) -> UserConnection | None:
        if blocker_user_id == blocked_user_id:
            return None

        # Update (blocker, blocked) if it already exists
        row = self._get_connection(blocker_user_id, blocked_user_id)
        if row:
            row.status = ConnectionStatus.blocked
            row.updated_at = datetime.now(UTC)
            self.session.add(row)
            self.session.commit()
            self.session.refresh(row)
            return row

        # Remove reverse row so we can create the canonical (blocker → blocked) direction
        reverse = self._get_connection(blocked_user_id, blocker_user_id)
        if reverse:
            self.session.delete(reverse)
            self.session.flush()

        row = UserConnection(
            requester_user_id=blocker_user_id,
            addressee_user_id=blocked_user_id,
            status=ConnectionStatus.blocked,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def list_connections(self, *, user_id: UUID) -> list[UserConnection]:
        statement = (
            select(UserConnection)
            .where(
                or_(
                    UserConnection.requester_user_id == user_id,
                    UserConnection.addressee_user_id == user_id,
                )
            )
            .where(UserConnection.status == ConnectionStatus.accepted)
        )
        return list(self.session.exec(statement).all())

    def list_pending_requests_for_user(self, *, user_id: UUID) -> list[UserConnection]:
        statement = (
            select(UserConnection)
            .where(UserConnection.addressee_user_id == user_id)
            .where(UserConnection.status == ConnectionStatus.pending)
        )
        return list(self.session.exec(statement).all())

    # --- organizer follows ---

    def follow_organizer(
        self,
        *,
        user_id: UUID,
        organizer_id: UUID,
    ) -> OrganizerFollower | None:
        if self._get_organizer(organizer_id) is None:
            return None

        existing = self._get_follower_row(user_id, organizer_id)
        if existing:
            return existing

        follower = OrganizerFollower(user_id=user_id, organizer_id=organizer_id)
        self.session.add(follower)
        self.session.commit()
        self.session.refresh(follower)
        return follower

    def unfollow_organizer(
        self,
        *,
        user_id: UUID,
        organizer_id: UUID,
    ) -> bool:
        row = self._get_follower_row(user_id, organizer_id)
        if row is None:
            return True

        self.session.delete(row)
        self.session.commit()
        return True

    def list_followed_organizers(self, *, user_id: UUID) -> list[OrganizerFollower]:
        statement = (
            select(OrganizerFollower)
            .where(OrganizerFollower.user_id == user_id)
            .order_by(OrganizerFollower.created_at)
        )
        return list(self.session.exec(statement).all())

    def list_organizer_followers(self, *, organizer_id: UUID) -> list[OrganizerFollower]:
        statement = (
            select(OrganizerFollower)
            .where(OrganizerFollower.organizer_id == organizer_id)
            .order_by(OrganizerFollower.created_at)
        )
        return list(self.session.exec(statement).all())
