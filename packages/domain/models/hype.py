from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Field, SQLModel


class HypeLedger(SQLModel, table=True):
    __tablename__ = "hype_ledger"
    id: int | None = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    event_id: UUID = Field(foreign_key="events.id")
    amount: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
