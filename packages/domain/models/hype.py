from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlmodel import Column, DateTime, Field, Index, SQLModel, func


class HypeLedger(SQLModel, table=True):
    __tablename__ = "hype_ledger"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", name="fk_hype_ledger_user_id_users"),
            nullable=False,
        ),
    )
    event_id: UUID = Field(
        sa_column=Column(
            ForeignKey("events.id", name="fk_hype_ledger_event_id_events"),
            nullable=False,
        ),
    )
    amount: int
    wallet_transaction_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey(
                "wallet_transactions.id",
                name="fk_hype_ledger_wallet_transaction_id_wallet_transactions",
            ),
            nullable=True,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},
    )

    __table_args__ = (
        Index("ix_hype_ledger_user_id", "user_id"),
        Index("ix_hype_ledger_event_id", "event_id"),
        Index("ix_hype_ledger_wallet_transaction_id", "wallet_transaction_id"),
        Index("ix_hype_ledger_event_id_created_at", "event_id", "created_at"),
        Index("ix_hype_ledger_user_id_created_at", "user_id", "created_at"),
    )
