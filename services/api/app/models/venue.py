from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Index


class Venue(SQLModel, table=True):
    __tablename__ = "venues"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    country_code: str = Field(index=True)
    city: Optional[str] = Field(default=None, index=True)
    lat: float
    lng: float
    full_address: str
    relevance: float
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_venues_name_country", "name", "country_code"),
    )
