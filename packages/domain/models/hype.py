from uuid import UUID

from sqlmodel import Field, SQLModel

from packages.domain.models.base import TimestampMixin


class HypeLedger(TimestampMixin, SQLModel, table=True):
    __tablename__ = "hype_ledger"
    id: int | None = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    event_id: UUID = Field(foreign_key="events.id")
    amount: int
