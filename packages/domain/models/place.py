from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql
from sqlmodel import Column, Field, Index, SQLModel

from packages.domain.models.base import TimestampMixin


class PlaceType(StrEnum):
    venue = "venue"
    outdoor_area = "outdoor_area"
    route_start = "route_start"
    temporary_spot = "temporary_spot"
    unknown = "unknown"


class PlaceVerificationStatus(StrEnum):
    unverified = "unverified"
    system_matched = "system_matched"
    manually_verified = "manually_verified"


class Place(TimestampMixin, SQLModel, table=True):
    __tablename__ = "places"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    normalized_name: str | None = Field(default=None, index=True)
    country_code: str = Field(index=True)
    city: str | None = Field(default=None, index=True)
    lat: float | None = Field(default=None)
    lng: float | None = Field(default=None)
    full_address: str | None = Field(default=None)
    location: Any = Field(
        default=None,
        exclude=True,
        sa_column=Column(Geography(geometry_type="POINT", srid=4326, spatial_index=False)),
    )
    place_type: PlaceType = Field(
        default=PlaceType.unknown,
        sa_column=Column(
            postgresql.ENUM(PlaceType, name="place_type", create_type=False),
            nullable=False,
            server_default=PlaceType.unknown.value,
        ),
    )
    match_confidence: float
    verification_status: PlaceVerificationStatus = Field(
        default=PlaceVerificationStatus.unverified,
        sa_column=Column(
            postgresql.ENUM(
                PlaceVerificationStatus,
                name="place_verification_status",
                create_type=False,
            ),
            nullable=False,
            server_default=PlaceVerificationStatus.unverified.value,
        ),
    )
    source_provider: str | None = Field(default=None, index=True)
    external_place_id: str | None = Field(default=None, index=True)

    __table_args__ = (
        Index("ix_places_name_country", "name", "country_code"),
        Index("idx_places_location", "location", postgresql_using="gist"),
    )

    def __init__(self, **data: Any) -> None:
        relevance = data.pop("relevance", None)
        if relevance is not None and "match_confidence" not in data:
            data["match_confidence"] = relevance
        if "normalized_name" not in data and isinstance(data.get("name"), str):
            data["normalized_name"] = data["name"].lower()

        super().__init__(**data)

    @property
    def relevance(self) -> float:
        return self.match_confidence

    @relevance.setter
    def relevance(self, value: float) -> None:
        self.match_confidence = value


Venue = Place
