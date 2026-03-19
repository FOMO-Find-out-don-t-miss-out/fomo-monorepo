from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlmodel import SQLModel, Field


class HypeLedger(SQLModel, table=True):
    __tablename__ = "hype_ledger"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    event_id: UUID = Field(foreign_key="events.id")
    amount: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
