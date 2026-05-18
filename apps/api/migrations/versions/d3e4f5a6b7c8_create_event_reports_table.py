"""create_event_reports_table

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-05-19 14:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    gps_validation_status = postgresql.ENUM(
        "not_checked",
        "valid",
        "invalid",
        "not_available",
        name="gps_validation_status",
        create_type=False,
    )
    report_status = postgresql.ENUM(
        "open",
        "under_review",
        "resolved",
        "dismissed",
        name="report_status",
        create_type=False,
    )
    report_resolution = postgresql.ENUM(
        "event_removed",
        "event_kept",
        "merged",
        "needs_monitoring",
        "report_rejected",
        name="report_resolution",
        create_type=False,
    )

    op.create_table(
        "event_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "gps_validation_status",
            gps_validation_status,
            server_default="not_checked",
            nullable=False,
        ),
        sa.Column("status", report_status, server_default="open", nullable=False),
        sa.Column("resolution", report_resolution, nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            name="fk_event_reports_event_id_events",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_user_id"],
            ["users.id"],
            name="fk_event_reports_reporter_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_event_reports_reviewed_by_users",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id",
            "reporter_user_id",
            "reason",
            name="uq_event_reports_event_reporter_reason",
        ),
    )
    op.create_index("ix_event_reports_event_id", "event_reports", ["event_id"], unique=False)
    op.create_index(
        "ix_event_reports_reporter_user_id",
        "event_reports",
        ["reporter_user_id"],
        unique=False,
    )
    op.create_index("ix_event_reports_status", "event_reports", ["status"], unique=False)
    op.create_index(
        "ix_event_reports_gps_validation_status",
        "event_reports",
        ["gps_validation_status"],
        unique=False,
    )
    op.create_index(
        "ix_event_reports_reviewed_by",
        "event_reports",
        ["reviewed_by"],
        unique=False,
    )
    op.create_index(
        "ix_event_reports_event_id_status",
        "event_reports",
        ["event_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_event_reports_status_created_at",
        "event_reports",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_event_reports_status_created_at", table_name="event_reports")
    op.drop_index("ix_event_reports_event_id_status", table_name="event_reports")
    op.drop_index("ix_event_reports_reviewed_by", table_name="event_reports")
    op.drop_index("ix_event_reports_gps_validation_status", table_name="event_reports")
    op.drop_index("ix_event_reports_status", table_name="event_reports")
    op.drop_index("ix_event_reports_reporter_user_id", table_name="event_reports")
    op.drop_index("ix_event_reports_event_id", table_name="event_reports")
    op.drop_table("event_reports")
