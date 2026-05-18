from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy.dialects import postgresql
from sqlmodel import Column, Field, Index, SQLModel

from packages.domain.models.base import TimestampMixin


class OrganizerVerificationStatus(StrEnum):
    unverified = "unverified"
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class Organizer(TimestampMixin, SQLModel, table=True):
    __tablename__ = "organizers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    display_name: str
    slug: str | None = Field(default=None)
    website_url: str | None = Field(default=None)
    instagram_handle: str | None = Field(default=None)
    contact_email: str | None = Field(default=None)
    verification_status: OrganizerVerificationStatus = Field(
        default=OrganizerVerificationStatus.unverified,
        sa_column=Column(
            postgresql.ENUM(
                OrganizerVerificationStatus,
                name="organizer_verification_status",
                create_type=False,
            ),
            nullable=False,
            server_default=OrganizerVerificationStatus.unverified.value,
        ),
    )

    __table_args__ = (
        Index("ix_organizers_display_name", "display_name"),
        Index("ix_organizers_slug", "slug", unique=True),
        Index("ix_organizers_verification_status", "verification_status"),
        Index("ix_organizers_instagram_handle", "instagram_handle"),
    )
