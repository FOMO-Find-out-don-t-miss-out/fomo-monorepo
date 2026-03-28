"""add_source_provider_and_ingestion_method

Revision ID: 3a2b1c0d4e5f
Revises: 10301ff1b1a9
Create Date: 2026-03-29 12:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "3a2b1c0d4e5f"
down_revision = "9a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns to events
    op.add_column(
        "events",
        sa.Column(
            "source_provider",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "ingestion_method",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.create_index(op.f("ix_events_source_provider"), "events", ["source_provider"], unique=False)
    op.create_index(
        op.f("ix_events_ingestion_method"), "events", ["ingestion_method"], unique=False
    )

    # Add columns to pending_events
    op.add_column(
        "pending_events",
        sa.Column(
            "source_provider",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "pending_events",
        sa.Column(
            "ingestion_method",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.create_index(
        op.f("ix_pending_events_source_provider"),
        "pending_events",
        ["source_provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pending_events_ingestion_method"),
        "pending_events",
        ["ingestion_method"],
        unique=False,
    )

    # Data Migration: Update existing records for more.com
    # Note: Using execute() to run raw SQL for data migration
    op.execute(
        "UPDATE events SET source_provider = 'more.com', ingestion_method = 'registry' "
        "WHERE source_url LIKE '%more.com%'"
    )
    op.execute(
        "UPDATE pending_events SET source_provider = 'more.com', ingestion_method = 'registry' "
        "WHERE source_url LIKE '%more.com%'"
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_pending_events_ingestion_method"), table_name="pending_events")
    op.drop_index(op.f("ix_pending_events_source_provider"), table_name="pending_events")
    op.drop_column("pending_events", "ingestion_method")
    op.drop_column("pending_events", "source_provider")
    op.drop_index(op.f("ix_events_ingestion_method"), table_name="events")
    op.drop_index(op.f("ix_events_source_provider"), table_name="events")
    op.drop_column("events", "ingestion_method")
    op.drop_column("events", "source_provider")
