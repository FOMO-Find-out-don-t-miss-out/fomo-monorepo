from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from packages.domain.models import Event, HypeLedger, WalletAccount, WalletTransaction
from packages.domain.models.event import EventStatus, EventVisibility
from packages.domain.models.wallet import WalletTransactionType


class WalletService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _get_public_event(self, event_id: UUID) -> Event | None:
        return self.session.exec(
            select(Event)
            .where(Event.id == event_id)
            .where(Event.status == EventStatus.live)
            .where(Event.visibility == EventVisibility.public)
            .where(Event.removed_at.is_(None))
        ).first()

    # Mutates wallet and stages a WalletTransaction without committing.
    # Callers must commit after any additional work (e.g. hype_ledger).
    def _stage_debit(
        self,
        wallet: WalletAccount,
        *,
        amount: int,
        transaction_type: WalletTransactionType,
        source: str | None,
        reference_id: UUID | None,
        event_id: UUID | None,
    ) -> WalletTransaction:
        wallet.balance -= amount
        wallet.updated_at = datetime.now(UTC)
        tx = WalletTransaction(
            user_id=wallet.user_id,
            amount=-amount,
            transaction_type=transaction_type,
            source=source,
            reference_id=reference_id,
            event_id=event_id,
        )
        self.session.add(wallet)
        self.session.add(tx)
        return tx

    # --- wallet account ---

    def get_or_create_wallet(self, *, user_id: UUID) -> WalletAccount:
        wallet = self.session.get(WalletAccount, user_id)
        if wallet is not None:
            return wallet

        wallet = WalletAccount(user_id=user_id, balance=0)
        self.session.add(wallet)
        self.session.commit()
        self.session.refresh(wallet)
        return wallet

    def get_balance(self, *, user_id: UUID) -> int:
        return self.get_or_create_wallet(user_id=user_id).balance

    # --- credits ---

    def credit_wallet(
        self,
        *,
        user_id: UUID,
        amount: int,
        transaction_type: WalletTransactionType = WalletTransactionType.grant,
        source: str | None = None,
        reference_id: UUID | None = None,
        event_id: UUID | None = None,
    ) -> WalletTransaction:
        if amount <= 0:
            raise ValueError(f"credit amount must be positive, got {amount}")

        wallet = self.get_or_create_wallet(user_id=user_id)
        wallet.balance += amount
        wallet.updated_at = datetime.now(UTC)

        tx = WalletTransaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            source=source,
            reference_id=reference_id,
            event_id=event_id,
        )
        self.session.add(wallet)
        self.session.add(tx)
        self.session.commit()
        self.session.refresh(tx)
        return tx

    # --- debits ---

    def debit_wallet(
        self,
        *,
        user_id: UUID,
        amount: int,
        transaction_type: WalletTransactionType = WalletTransactionType.spend,
        source: str | None = None,
        reference_id: UUID | None = None,
        event_id: UUID | None = None,
    ) -> WalletTransaction | None:
        if amount <= 0:
            raise ValueError(f"debit amount must be positive, got {amount}")

        wallet = self.get_or_create_wallet(user_id=user_id)
        if wallet.balance < amount:
            return None

        tx = self._stage_debit(
            wallet,
            amount=amount,
            transaction_type=transaction_type,
            source=source,
            reference_id=reference_id,
            event_id=event_id,
        )
        self.session.commit()
        self.session.refresh(tx)
        return tx

    # --- adjustments ---

    def adjust_wallet(
        self,
        *,
        user_id: UUID,
        signed_amount: int,
        source: str | None = None,
        reference_id: UUID | None = None,
    ) -> WalletTransaction | None:
        wallet = self.get_or_create_wallet(user_id=user_id)
        if wallet.balance + signed_amount < 0:
            return None

        wallet.balance += signed_amount
        wallet.updated_at = datetime.now(UTC)

        tx = WalletTransaction(
            user_id=user_id,
            amount=signed_amount,
            transaction_type=WalletTransactionType.adjustment,
            source=source,
            reference_id=reference_id,
        )
        self.session.add(wallet)
        self.session.add(tx)
        self.session.commit()
        self.session.refresh(tx)
        return tx

    # --- hype ---

    def hype_event(
        self,
        *,
        user_id: UUID,
        event_id: UUID,
        amount: int,
    ) -> HypeLedger | None:
        if amount <= 0:
            raise ValueError(f"hype amount must be positive, got {amount}")

        if self._get_public_event(event_id) is None:
            return None

        wallet = self.get_or_create_wallet(user_id=user_id)
        if wallet.balance < amount:
            return None

        # Stage debit and hype_ledger together — committed atomically below.
        tx = self._stage_debit(
            wallet,
            amount=amount,
            transaction_type=WalletTransactionType.spend,
            source="hype_spend",
            reference_id=None,
            event_id=event_id,
        )

        hype = HypeLedger(
            user_id=user_id,
            event_id=event_id,
            amount=amount,
            wallet_transaction_id=tx.id,
        )
        self.session.add(hype)
        self.session.commit()
        self.session.refresh(hype)
        return hype
