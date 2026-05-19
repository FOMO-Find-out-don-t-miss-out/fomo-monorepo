from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.services.wallet_service import WalletService
from sqlmodel import Session, select

from packages.domain.models import (
    Event,
    EventProvenance,
    EventStatus,
    EventVisibility,
    HypeLedger,
    User,
    WalletAccount,
    WalletTransaction,
)
from packages.domain.models.wallet import WalletTransactionType


def create_user(session: Session, email: str = "wallet@example.com") -> User:
    user = User(external_id=str(uuid4()), email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_event(
    session: Session,
    title: str,
    *,
    status: EventStatus = EventStatus.live,
    provenance: EventProvenance = EventProvenance.aggregated,
    visibility: EventVisibility = EventVisibility.public,
) -> Event:
    event = Event(
        title=title,
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 7, 1, 20, 0, tzinfo=UTC),
        category="Music",
        status=status,
        provenance=provenance,
        visibility=visibility,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def tx_count(session: Session) -> int:
    return len(session.exec(select(WalletTransaction)).all())


def hype_count(session: Session) -> int:
    return len(session.exec(select(HypeLedger)).all())


# --- get_or_create_wallet ---


def test_get_or_create_wallet_creates_with_zero_balance(session: Session) -> None:
    user = create_user(session)
    service = WalletService(session)

    wallet = service.get_or_create_wallet(user_id=user.id)

    assert wallet is not None
    assert wallet.user_id == user.id
    assert wallet.balance == 0


def test_get_or_create_wallet_returns_existing_wallet(session: Session) -> None:
    user = create_user(session, "w2@example.com")
    service = WalletService(session)

    first = service.get_or_create_wallet(user_id=user.id)
    second = service.get_or_create_wallet(user_id=user.id)

    assert first.user_id == second.user_id
    # Only one wallet_accounts row
    assert len(session.exec(select(WalletAccount)).all()) == 1


def test_get_balance_returns_correct_balance(session: Session) -> None:
    user = create_user(session, "w3@example.com")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=50)

    assert service.get_balance(user_id=user.id) == 50


# --- credit_wallet ---


def test_credit_wallet_creates_positive_transaction(session: Session) -> None:
    user = create_user(session, "w4@example.com")
    service = WalletService(session)

    tx = service.credit_wallet(user_id=user.id, amount=100)

    assert tx is not None
    assert tx.user_id == user.id
    assert tx.amount == 100
    assert tx.transaction_type == WalletTransactionType.grant


def test_credit_wallet_increments_balance(session: Session) -> None:
    user = create_user(session, "w5@example.com")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=200)
    service.credit_wallet(user_id=user.id, amount=50)

    assert service.get_balance(user_id=user.id) == 250


def test_credit_wallet_rejects_non_positive_amount(session: Session) -> None:
    user = create_user(session, "w6@example.com")
    service = WalletService(session)

    with pytest.raises(ValueError):
        service.credit_wallet(user_id=user.id, amount=0)

    with pytest.raises(ValueError):
        service.credit_wallet(user_id=user.id, amount=-10)


def test_credit_wallet_accepts_custom_transaction_type(session: Session) -> None:
    user = create_user(session, "w6b@example.com")
    service = WalletService(session)

    tx = service.credit_wallet(
        user_id=user.id,
        amount=30,
        transaction_type=WalletTransactionType.refund,
        source="refund_test",
    )

    assert tx.transaction_type == WalletTransactionType.refund
    assert tx.source == "refund_test"


# --- debit_wallet ---


def test_debit_wallet_creates_negative_transaction(session: Session) -> None:
    user = create_user(session, "w7@example.com")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=100)
    tx = service.debit_wallet(user_id=user.id, amount=40)

    assert tx is not None
    assert tx.amount == -40
    assert tx.transaction_type == WalletTransactionType.spend


def test_debit_wallet_decrements_balance(session: Session) -> None:
    user = create_user(session, "w8@example.com")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=100)
    service.debit_wallet(user_id=user.id, amount=30)

    assert service.get_balance(user_id=user.id) == 70


def test_debit_wallet_rejects_non_positive_amount(session: Session) -> None:
    user = create_user(session, "w9@example.com")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=100)

    with pytest.raises(ValueError):
        service.debit_wallet(user_id=user.id, amount=0)

    with pytest.raises(ValueError):
        service.debit_wallet(user_id=user.id, amount=-5)


def test_debit_wallet_returns_none_on_insufficient_balance(session: Session) -> None:
    user = create_user(session, "w10@example.com")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=10)
    result = service.debit_wallet(user_id=user.id, amount=50)

    assert result is None


def test_failed_debit_does_not_create_transaction(session: Session) -> None:
    user = create_user(session, "w11@example.com")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=10)
    before = tx_count(session)
    service.debit_wallet(user_id=user.id, amount=100)

    assert tx_count(session) == before


def test_failed_debit_does_not_change_balance(session: Session) -> None:
    user = create_user(session, "w11b@example.com")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=10)
    service.debit_wallet(user_id=user.id, amount=100)

    assert service.get_balance(user_id=user.id) == 10


# --- adjust_wallet ---


def test_adjust_wallet_positive_adjustment_works(session: Session) -> None:
    user = create_user(session, "w12@example.com")
    service = WalletService(session)

    tx = service.adjust_wallet(user_id=user.id, signed_amount=75)

    assert tx is not None
    assert tx.amount == 75
    assert tx.transaction_type == WalletTransactionType.adjustment
    assert service.get_balance(user_id=user.id) == 75


def test_adjust_wallet_negative_adjustment_works_when_sufficient(session: Session) -> None:
    user = create_user(session, "w13@example.com")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=100)
    tx = service.adjust_wallet(user_id=user.id, signed_amount=-40)

    assert tx is not None
    assert tx.amount == -40
    assert service.get_balance(user_id=user.id) == 60


def test_adjust_wallet_negative_adjustment_prevents_negative_balance(
    session: Session,
) -> None:
    user = create_user(session, "w14@example.com")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=20)
    result = service.adjust_wallet(user_id=user.id, signed_amount=-50)

    assert result is None
    assert service.get_balance(user_id=user.id) == 20


# --- hype_event ---


def test_hype_event_debits_wallet(session: Session) -> None:
    user = create_user(session, "h1@example.com")
    event = create_event(session, "Hype Event 1")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=500)
    service.hype_event(user_id=user.id, event_id=event.id, amount=100)

    assert service.get_balance(user_id=user.id) == 400


def test_hype_event_creates_negative_wallet_transaction(session: Session) -> None:
    user = create_user(session, "h2@example.com")
    event = create_event(session, "Hype Event 2")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=500)
    service.hype_event(user_id=user.id, event_id=event.id, amount=50)

    txs = session.exec(
        select(WalletTransaction).where(
            WalletTransaction.transaction_type == WalletTransactionType.spend
        )
    ).all()
    assert len(txs) == 1
    assert txs[0].amount == -50
    assert txs[0].source == "hype_spend"
    assert txs[0].event_id == event.id


def test_hype_event_creates_hype_ledger_with_positive_amount_linked_to_tx(
    session: Session,
) -> None:
    user = create_user(session, "h3@example.com")
    event = create_event(session, "Hype Event 3")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=500)
    hype = service.hype_event(user_id=user.id, event_id=event.id, amount=75)

    assert hype is not None
    assert hype.user_id == user.id
    assert hype.event_id == event.id
    assert hype.amount == 75
    assert hype.wallet_transaction_id is not None

    # Confirm the linked transaction has negative amount
    tx = session.get(WalletTransaction, hype.wallet_transaction_id)
    assert tx is not None
    assert tx.amount == -75


def test_hype_event_rejects_insufficient_balance(session: Session) -> None:
    user = create_user(session, "h4@example.com")
    event = create_event(session, "Hype Event 4")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=10)
    result = service.hype_event(user_id=user.id, event_id=event.id, amount=100)

    assert result is None
    assert hype_count(session) == 0
    assert service.get_balance(user_id=user.id) == 10


def test_hype_event_rejects_non_public_event(session: Session) -> None:
    user = create_user(session, "h5@example.com")
    hidden = create_event(session, "Hidden Hype", visibility=EventVisibility.hidden)
    removed = create_event(session, "Removed Hype", status=EventStatus.removed)
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=500)

    assert service.hype_event(user_id=user.id, event_id=hidden.id, amount=50) is None
    assert service.hype_event(user_id=user.id, event_id=removed.id, amount=50) is None
    assert hype_count(session) == 0
    assert service.get_balance(user_id=user.id) == 500


def test_hype_event_is_atomic_no_wallet_tx_if_hype_not_created(
    session: Session,
) -> None:
    """Insufficient balance means neither wallet_transaction nor hype_ledger is created."""
    user = create_user(session, "h6@example.com")
    event = create_event(session, "Atomic Hype")
    service = WalletService(session)

    service.credit_wallet(user_id=user.id, amount=5)
    before_tx = tx_count(session)

    service.hype_event(user_id=user.id, event_id=event.id, amount=50)

    assert tx_count(session) == before_tx
    assert hype_count(session) == 0
