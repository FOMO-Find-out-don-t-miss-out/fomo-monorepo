from uuid import uuid4

from app.services.social_service import SocialService
from sqlmodel import Session

from packages.domain.models import Organizer, OrganizerFollower, User, UserConnection
from packages.domain.models.social import ConnectionStatus


def create_user(session: Session, email: str = "user@example.com") -> User:
    user = User(external_id=str(uuid4()), email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_organizer(session: Session, name: str = "Test Organizer") -> Organizer:
    org = Organizer(display_name=name)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


def connection_count(session: Session) -> int:
    return len(session.exec(__import__("sqlmodel").select(UserConnection)).all())


def follower_count(session: Session) -> int:
    return len(session.exec(__import__("sqlmodel").select(OrganizerFollower)).all())


# --- request_connection ---


def test_request_connection_creates_pending_connection(session: Session) -> None:
    alice = create_user(session, "alice@example.com")
    bob = create_user(session, "bob@example.com")
    service = SocialService(session)

    conn = service.request_connection(
        requester_user_id=alice.id,
        addressee_user_id=bob.id,
    )

    assert conn is not None
    assert conn.requester_user_id == alice.id
    assert conn.addressee_user_id == bob.id
    assert conn.status == ConnectionStatus.pending
    assert connection_count(session) == 1


def test_request_connection_is_idempotent(session: Session) -> None:
    alice = create_user(session, "alice2@example.com")
    bob = create_user(session, "bob2@example.com")
    service = SocialService(session)

    first = service.request_connection(requester_user_id=alice.id, addressee_user_id=bob.id)
    second = service.request_connection(requester_user_id=alice.id, addressee_user_id=bob.id)

    assert first is not None
    assert second is not None
    assert first.requester_user_id == second.requester_user_id
    assert first.addressee_user_id == second.addressee_user_id
    assert connection_count(session) == 1


def test_request_connection_prevents_self_connection(session: Session) -> None:
    alice = create_user(session, "alice3@example.com")
    service = SocialService(session)

    conn = service.request_connection(
        requester_user_id=alice.id,
        addressee_user_id=alice.id,
    )

    assert conn is None
    assert connection_count(session) == 0


def test_request_connection_auto_accepts_reverse_pending(session: Session) -> None:
    alice = create_user(session, "alice4@example.com")
    bob = create_user(session, "bob4@example.com")
    service = SocialService(session)

    # Bob requests Alice first
    bob_req = service.request_connection(requester_user_id=bob.id, addressee_user_id=alice.id)
    assert bob_req is not None
    assert bob_req.status == ConnectionStatus.pending

    # Now Alice requests Bob — both parties want to connect, should auto-accept
    result = service.request_connection(requester_user_id=alice.id, addressee_user_id=bob.id)

    assert result is not None
    assert result.status == ConnectionStatus.accepted
    # Still only one row (the original Bob→Alice, now accepted)
    assert connection_count(session) == 1


def test_request_connection_returns_existing_if_already_accepted(session: Session) -> None:
    alice = create_user(session, "alice5@example.com")
    bob = create_user(session, "bob5@example.com")
    service = SocialService(session)

    service.request_connection(requester_user_id=bob.id, addressee_user_id=alice.id)
    service.accept_connection(requester_user_id=bob.id, addressee_user_id=alice.id)

    # Alice tries to request Bob — should return the existing accepted row
    result = service.request_connection(requester_user_id=alice.id, addressee_user_id=bob.id)

    assert result is not None
    assert result.status == ConnectionStatus.accepted
    assert connection_count(session) == 1


def test_request_connection_blocked_by_reverse_block(session: Session) -> None:
    alice = create_user(session, "alice6@example.com")
    bob = create_user(session, "bob6@example.com")
    service = SocialService(session)

    # Bob blocks Alice
    service.block_connection(blocker_user_id=bob.id, blocked_user_id=alice.id)

    # Alice tries to request Bob — should be blocked
    result = service.request_connection(requester_user_id=alice.id, addressee_user_id=bob.id)

    assert result is None


def test_request_connection_allowed_after_reverse_rejection(session: Session) -> None:
    alice = create_user(session, "alice7@example.com")
    bob = create_user(session, "bob7@example.com")
    service = SocialService(session)

    # Bob requests Alice, Alice rejects it
    service.request_connection(requester_user_id=bob.id, addressee_user_id=alice.id)
    service.reject_connection(requester_user_id=bob.id, addressee_user_id=alice.id)

    # Now Alice requests Bob — should succeed (create new pending row)
    result = service.request_connection(requester_user_id=alice.id, addressee_user_id=bob.id)

    assert result is not None
    assert result.requester_user_id == alice.id
    assert result.addressee_user_id == bob.id
    assert result.status == ConnectionStatus.pending
    # Two rows: (bob→alice rejected) + (alice→bob pending)
    assert connection_count(session) == 2


# --- accept_connection ---


def test_accept_connection_moves_pending_to_accepted(session: Session) -> None:
    alice = create_user(session, "alice8@example.com")
    bob = create_user(session, "bob8@example.com")
    service = SocialService(session)

    service.request_connection(requester_user_id=alice.id, addressee_user_id=bob.id)
    accepted = service.accept_connection(requester_user_id=alice.id, addressee_user_id=bob.id)

    assert accepted is not None
    assert accepted.status == ConnectionStatus.accepted
    assert accepted.requester_user_id == alice.id
    assert accepted.addressee_user_id == bob.id


def test_accept_connection_returns_none_if_not_found(session: Session) -> None:
    service = SocialService(session)

    result = service.accept_connection(
        requester_user_id=uuid4(),
        addressee_user_id=uuid4(),
    )

    assert result is None


def test_accept_connection_returns_none_if_not_pending(session: Session) -> None:
    alice = create_user(session, "alice9@example.com")
    bob = create_user(session, "bob9@example.com")
    service = SocialService(session)

    service.request_connection(requester_user_id=alice.id, addressee_user_id=bob.id)
    service.accept_connection(requester_user_id=alice.id, addressee_user_id=bob.id)

    # Calling accept again on an already-accepted connection returns None
    result = service.accept_connection(requester_user_id=alice.id, addressee_user_id=bob.id)

    assert result is None


# --- reject_connection ---


def test_reject_connection_moves_pending_to_rejected(session: Session) -> None:
    alice = create_user(session, "alice10@example.com")
    bob = create_user(session, "bob10@example.com")
    service = SocialService(session)

    service.request_connection(requester_user_id=alice.id, addressee_user_id=bob.id)
    rejected = service.reject_connection(requester_user_id=alice.id, addressee_user_id=bob.id)

    assert rejected is not None
    assert rejected.status == ConnectionStatus.rejected


def test_reject_connection_returns_none_if_not_found(session: Session) -> None:
    service = SocialService(session)

    result = service.reject_connection(
        requester_user_id=uuid4(),
        addressee_user_id=uuid4(),
    )

    assert result is None


# --- block_connection ---


def test_block_connection_creates_blocked_row(session: Session) -> None:
    alice = create_user(session, "alice11@example.com")
    bob = create_user(session, "bob11@example.com")
    service = SocialService(session)

    blocked = service.block_connection(blocker_user_id=alice.id, blocked_user_id=bob.id)

    assert blocked is not None
    assert blocked.requester_user_id == alice.id
    assert blocked.addressee_user_id == bob.id
    assert blocked.status == ConnectionStatus.blocked


def test_block_connection_prevents_self_block(session: Session) -> None:
    alice = create_user(session, "alice12@example.com")
    service = SocialService(session)

    result = service.block_connection(blocker_user_id=alice.id, blocked_user_id=alice.id)

    assert result is None
    assert connection_count(session) == 0


def test_block_connection_updates_existing_row(session: Session) -> None:
    alice = create_user(session, "alice13@example.com")
    bob = create_user(session, "bob13@example.com")
    service = SocialService(session)

    service.request_connection(requester_user_id=alice.id, addressee_user_id=bob.id)
    blocked = service.block_connection(blocker_user_id=alice.id, blocked_user_id=bob.id)

    assert blocked is not None
    assert blocked.status == ConnectionStatus.blocked
    assert connection_count(session) == 1


def test_block_connection_removes_reverse_and_creates_canonical_row(session: Session) -> None:
    alice = create_user(session, "alice14@example.com")
    bob = create_user(session, "bob14@example.com")
    service = SocialService(session)

    # Bob requested Alice first
    service.request_connection(requester_user_id=bob.id, addressee_user_id=alice.id)

    # Alice now blocks Bob — should remove (bob→alice) and create (alice→bob) as blocked
    blocked = service.block_connection(blocker_user_id=alice.id, blocked_user_id=bob.id)

    assert blocked is not None
    assert blocked.requester_user_id == alice.id
    assert blocked.addressee_user_id == bob.id
    assert blocked.status == ConnectionStatus.blocked
    assert connection_count(session) == 1


# --- list_connections ---


def test_list_connections_returns_accepted_as_requester_and_addressee(
    session: Session,
) -> None:
    alice = create_user(session, "alice15@example.com")
    bob = create_user(session, "bob15@example.com")
    carol = create_user(session, "carol15@example.com")
    service = SocialService(session)

    # Alice → Bob accepted
    service.request_connection(requester_user_id=alice.id, addressee_user_id=bob.id)
    service.accept_connection(requester_user_id=alice.id, addressee_user_id=bob.id)

    # Carol → Alice accepted
    service.request_connection(requester_user_id=carol.id, addressee_user_id=alice.id)
    service.accept_connection(requester_user_id=carol.id, addressee_user_id=alice.id)

    connections = service.list_connections(user_id=alice.id)

    assert len(connections) == 2


def test_list_connections_excludes_non_accepted_statuses(session: Session) -> None:
    alice = create_user(session, "alice16@example.com")
    bob = create_user(session, "bob16@example.com")
    carol = create_user(session, "carol16@example.com")
    dave = create_user(session, "dave16@example.com")
    service = SocialService(session)

    # pending
    service.request_connection(requester_user_id=alice.id, addressee_user_id=bob.id)
    # rejected
    service.request_connection(requester_user_id=alice.id, addressee_user_id=carol.id)
    service.reject_connection(requester_user_id=alice.id, addressee_user_id=carol.id)
    # blocked
    service.block_connection(blocker_user_id=alice.id, blocked_user_id=dave.id)

    connections = service.list_connections(user_id=alice.id)

    assert connections == []


def test_list_pending_requests_returns_only_incoming_pending(session: Session) -> None:
    alice = create_user(session, "alice17@example.com")
    bob = create_user(session, "bob17@example.com")
    carol = create_user(session, "carol17@example.com")
    service = SocialService(session)

    # Bob → Alice (incoming to Alice)
    service.request_connection(requester_user_id=bob.id, addressee_user_id=alice.id)
    # Carol → Alice (incoming to Alice)
    service.request_connection(requester_user_id=carol.id, addressee_user_id=alice.id)
    # Alice → Bob would auto-accept since Bob→Alice is pending.
    # Use a separate user to test outgoing without side-effects:
    dave = create_user(session, "dave17@example.com")
    service.request_connection(requester_user_id=alice.id, addressee_user_id=dave.id)

    pending = service.list_pending_requests_for_user(user_id=alice.id)

    assert len(pending) == 2
    addressees = {p.requester_user_id for p in pending}
    assert bob.id in addressees
    assert carol.id in addressees


# --- follow_organizer ---


def test_follow_organizer_creates_follower_row(session: Session) -> None:
    user = create_user(session)
    org = create_organizer(session)
    service = SocialService(session)

    follower = service.follow_organizer(user_id=user.id, organizer_id=org.id)

    assert follower is not None
    assert follower.user_id == user.id
    assert follower.organizer_id == org.id
    assert follower_count(session) == 1


def test_follow_organizer_is_idempotent(session: Session) -> None:
    user = create_user(session, "f2@example.com")
    org = create_organizer(session, "Org 2")
    service = SocialService(session)

    first = service.follow_organizer(user_id=user.id, organizer_id=org.id)
    second = service.follow_organizer(user_id=user.id, organizer_id=org.id)

    assert first is not None
    assert second is not None
    assert first.user_id == second.user_id
    assert first.organizer_id == second.organizer_id
    assert follower_count(session) == 1


def test_follow_nonexistent_organizer_returns_none(session: Session) -> None:
    user = create_user(session, "f3@example.com")
    service = SocialService(session)

    result = service.follow_organizer(user_id=user.id, organizer_id=uuid4())

    assert result is None
    assert follower_count(session) == 0


def test_unfollow_organizer_removes_row(session: Session) -> None:
    user = create_user(session, "f4@example.com")
    org = create_organizer(session, "Org 4")
    service = SocialService(session)

    service.follow_organizer(user_id=user.id, organizer_id=org.id)
    result = service.unfollow_organizer(user_id=user.id, organizer_id=org.id)

    assert result is True
    assert follower_count(session) == 0


def test_unfollow_organizer_is_idempotent(session: Session) -> None:
    user = create_user(session, "f5@example.com")
    org = create_organizer(session, "Org 5")
    service = SocialService(session)

    # Unfollow without ever following
    result = service.unfollow_organizer(user_id=user.id, organizer_id=org.id)

    assert result is True


def test_list_followed_organizers_returns_only_that_users_follows(session: Session) -> None:
    alice = create_user(session, "f6a@example.com")
    bob = create_user(session, "f6b@example.com")
    org_a = create_organizer(session, "Org A")
    org_b = create_organizer(session, "Org B")
    service = SocialService(session)

    service.follow_organizer(user_id=alice.id, organizer_id=org_a.id)
    service.follow_organizer(user_id=alice.id, organizer_id=org_b.id)
    service.follow_organizer(user_id=bob.id, organizer_id=org_a.id)

    alice_follows = service.list_followed_organizers(user_id=alice.id)

    assert len(alice_follows) == 2
    assert all(f.user_id == alice.id for f in alice_follows)


def test_list_organizer_followers_returns_only_that_organizers_followers(
    session: Session,
) -> None:
    user_a = create_user(session, "f7a@example.com")
    user_b = create_user(session, "f7b@example.com")
    user_c = create_user(session, "f7c@example.com")
    org_x = create_organizer(session, "Org X")
    org_y = create_organizer(session, "Org Y")
    service = SocialService(session)

    service.follow_organizer(user_id=user_a.id, organizer_id=org_x.id)
    service.follow_organizer(user_id=user_b.id, organizer_id=org_x.id)
    service.follow_organizer(user_id=user_c.id, organizer_id=org_y.id)

    x_followers = service.list_organizer_followers(organizer_id=org_x.id)

    assert len(x_followers) == 2
    assert all(f.organizer_id == org_x.id for f in x_followers)
