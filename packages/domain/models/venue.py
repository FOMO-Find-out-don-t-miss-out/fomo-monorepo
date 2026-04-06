from uuid import UUID, uuid4

from sqlmodel import Field, Index, SQLModel

from packages.domain.models.base import TimestampMixin


class Venue(TimestampMixin, SQLModel, table=True):
    __tablename__ = "venues"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    country_code: str = Field(index=True)
    city: str | None = Field(default=None, index=True)
    lat: float
    lng: float
    full_address: str
    relevance: float
    is_manually_verified: bool = Field(default=False)

    __table_args__ = (Index("ix_venues_name_country", "name", "country_code"),)
