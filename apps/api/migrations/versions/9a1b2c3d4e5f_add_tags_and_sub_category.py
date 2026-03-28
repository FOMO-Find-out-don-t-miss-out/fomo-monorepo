"""add tags and sub_category to events

Revision ID: 9a1b2c3d4e5f
Revises: 10301ff1b1a9
Create Date: 2026-03-22 04:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9a1b2c3d4e5f"
down_revision = "10301ff1b1a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add sub_category and tags to events table
    op.add_column("events", sa.Column("sub_category", sa.String(), nullable=True))
    op.add_column(
        "events", sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )
    op.create_index(op.f("ix_events_sub_category"), "events", ["sub_category"], unique=False)

    # Add sub_category and tags to pending_events table
    op.add_column("pending_events", sa.Column("sub_category", sa.String(), nullable=True))
    op.add_column(
        "pending_events", sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )
    op.create_index(
        op.f("ix_pending_events_sub_category"), "pending_events", ["sub_category"], unique=False
    )

    # Add is_manually_verified to venues table
    op.add_column(
        "venues",
        sa.Column("is_manually_verified", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    # Remove from venues
    op.drop_column("venues", "is_manually_verified")

    # Remove from pending_events
    op.drop_index(op.f("ix_pending_events_sub_category"), table_name="pending_events")
    op.drop_column("pending_events", "tags")
    op.drop_column("pending_events", "sub_category")

    # Remove from events
    op.drop_index(op.f("ix_events_sub_category"), table_name="events")
    op.drop_column("events", "tags")
    op.drop_column("events", "sub_category")
