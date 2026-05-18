from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.dialects import postgresql
from sqlmodel import Column, DateTime, Field, Index, SQLModel, Text, UniqueConstraint

from packages.domain.models.base import TimestampMixin


class GpsValidationStatus(StrEnum):
    not_checked = "not_checked"
    valid = "valid"
    invalid = "invalid"
    not_available = "not_available"


class ReportStatus(StrEnum):
    open = "open"
    under_review = "under_review"
    resolved = "resolved"
    dismissed = "dismissed"


class ReportResolution(StrEnum):
    event_removed = "event_removed"
    event_kept = "event_kept"
    merged = "merged"
    needs_monitoring = "needs_monitoring"
    report_rejected = "report_rejected"


class EventReport(TimestampMixin, SQLModel, table=True):
    __tablename__ = "event_reports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(
        sa_column=Column(
            ForeignKey("events.id", name="fk_event_reports_event_id_events"),
            nullable=False,
        ),
    )
    reporter_user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", name="fk_event_reports_reporter_user_id_users"),
            nullable=False,
        ),
    )
    reason: str
    details: str | None = Field(default=None, sa_column=Column(Text))
    gps_validation_status: GpsValidationStatus = Field(
        default=GpsValidationStatus.not_checked,
        sa_column=Column(
            postgresql.ENUM(
                GpsValidationStatus,
                name="gps_validation_status",
                create_type=False,
            ),
            nullable=False,
            server_default=GpsValidationStatus.not_checked.value,
        ),
    )
    status: ReportStatus = Field(
        default=ReportStatus.open,
        sa_column=Column(
            postgresql.ENUM(ReportStatus, name="report_status", create_type=False),
            nullable=False,
            server_default=ReportStatus.open.value,
        ),
    )
    resolution: ReportResolution | None = Field(
        default=None,
        sa_column=Column(
            postgresql.ENUM(ReportResolution, name="report_resolution", create_type=False),
            nullable=True,
        ),
    )
    reviewed_by: UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("users.id", name="fk_event_reports_reviewed_by_users"),
            nullable=True,
        ),
    )
    reviewed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "reporter_user_id",
            "reason",
            name="uq_event_reports_event_reporter_reason",
        ),
        Index("ix_event_reports_event_id", "event_id"),
        Index("ix_event_reports_reporter_user_id", "reporter_user_id"),
        Index("ix_event_reports_status", "status"),
        Index("ix_event_reports_gps_validation_status", "gps_validation_status"),
        Index("ix_event_reports_reviewed_by", "reviewed_by"),
        Index("ix_event_reports_event_id_status", "event_id", "status"),
        Index("ix_event_reports_status_created_at", "status", "created_at"),
    )
