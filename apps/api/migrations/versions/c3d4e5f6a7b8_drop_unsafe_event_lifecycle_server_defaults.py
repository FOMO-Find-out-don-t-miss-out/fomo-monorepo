"""drop_unsafe_event_lifecycle_server_defaults

Remove server_default from events.status and events.provenance.
These columns must be set explicitly by service logic — relying on
the DB to silently classify new rows as live/aggregated is unsafe.
trust_level (unverified) and visibility (public) server defaults are
kept because they represent safe conservative values.

Revision ID: c3d4e5f6a7b8
Revises: b7c8d9e0f1a2
Create Date: 2026-05-19 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    event_status = postgresql.ENUM(
        "approved",
        "live",
        "expired",
        "archived",
        "under_investigation",
        "removed",
        name="event_status",
        create_type=False,
    )
    event_provenance = postgresql.ENUM(
        "aggregated",
        "community_submitted",
        "claimed_official",
        "verified_organizer",
        name="event_provenance",
        create_type=False,
    )

    op.alter_column(
        "events",
        "status",
        existing_type=event_status,
        server_default=None,
        existing_nullable=False,
    )
    op.alter_column(
        "events",
        "provenance",
        existing_type=event_provenance,
        server_default=None,
        existing_nullable=False,
    )


def downgrade() -> None:
    event_status = postgresql.ENUM(
        "approved",
        "live",
        "expired",
        "archived",
        "under_investigation",
        "removed",
        name="event_status",
        create_type=False,
    )
    event_provenance = postgresql.ENUM(
        "aggregated",
        "community_submitted",
        "claimed_official",
        "verified_organizer",
        name="event_provenance",
        create_type=False,
    )

    op.alter_column(
        "events",
        "status",
        existing_type=event_status,
        server_default=sa.text("'live'"),
        existing_nullable=False,
    )
    op.alter_column(
        "events",
        "provenance",
        existing_type=event_provenance,
        server_default=sa.text("'aggregated'"),
        existing_nullable=False,
    )
