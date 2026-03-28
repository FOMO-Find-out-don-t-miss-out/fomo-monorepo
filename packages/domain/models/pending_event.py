from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, UniqueConstraint

from packages.domain.models.event import EventBase


class PendingEvent(EventBase, table=True):
    __tablename__ = "pending_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    status: str = Field(default="pending", index=True)
    raw_content: Optional[str] = Field(
        default=None,
        serialization_alias="rawContent",
    )
    rejection_reason: Optional[str] = Field(
        default=None,
        serialization_alias="rejectionReason",
    )

    confidence_score: Optional[float] = Field(
        default=None,
        serialization_alias="confidenceScore",
    )

    __table_args__ = (UniqueConstraint("title", "start_time", name="unique_pending_event"),)
