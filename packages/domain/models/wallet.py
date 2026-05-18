from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.dialects import postgresql
from sqlmodel import Column, DateTime, Field, Index, SQLModel, func

from packages.domain.models.base import TimestampMixin


class WalletTransactionType(StrEnum):
    spend = "spend"
    refund = "refund"
    grant = "grant"
    adjustment = "adjustment"


class WalletAccount(TimestampMixin, SQLModel, table=True):
    __tablename__ = "wallet_accounts"

    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", name="fk_wallet_accounts_user_id_users"),
            primary_key=True,
            nullable=False,
        ),
    )
    balance: int = Field(default=0, nullable=False, sa_column_kwargs={"server_default": "0"})


class WalletTransaction(SQLModel, table=True):
    __tablename__ = "wallet_transactions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", name="fk_wallet_transactions_user_id_users"),
            nullable=False,
        ),
    )
    event_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("events.id", name="fk_wallet_transactions_event_id_events"),
            nullable=True,
        ),
    )
    transaction_type: WalletTransactionType = Field(
        sa_column=Column(
            postgresql.ENUM(
                WalletTransactionType,
                name="wallet_transaction_type",
                create_type=False,
            ),
            nullable=False,
        ),
    )
    amount: int
    source: str | None = Field(default=None)
    reference_id: UUID | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},
    )

    __table_args__ = (
        Index("ix_wallet_transactions_user_id", "user_id"),
        Index("ix_wallet_transactions_event_id", "event_id"),
        Index("ix_wallet_transactions_transaction_type", "transaction_type"),
        Index("ix_wallet_transactions_source", "source"),
        Index("ix_wallet_transactions_user_id_created_at", "user_id", "created_at"),
        Index("ix_wallet_transactions_event_id_transaction_type", "event_id", "transaction_type"),
    )
