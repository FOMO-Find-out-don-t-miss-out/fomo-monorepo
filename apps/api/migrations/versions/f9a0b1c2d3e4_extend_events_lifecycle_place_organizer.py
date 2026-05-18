"""extend_events_lifecycle_place_organizer

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-05-18 19:30:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f9a0b1c2d3e4"
down_revision = "e8f9a0b1c2d3"
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
    event_trust_level = postgresql.ENUM(
        "unverified",
        "community_validated",
        "trusted_source",
        "official",
        name="event_trust_level",
        create_type=False,
    )
    event_visibility = postgresql.ENUM(
        "public",
        "hidden",
        "shadow_hidden",
        "restricted",
        name="event_visibility",
        create_type=False,
    )

    op.add_column("events", sa.Column("place_id", sa.Uuid(), nullable=True))
    op.add_column("events", sa.Column("organizer_id", sa.Uuid(), nullable=True))
    op.add_column(
        "events",
        sa.Column("status", event_status, server_default="live", nullable=False),
    )
    op.add_column(
        "events",
        sa.Column(
            "provenance",
            event_provenance,
            server_default="aggregated",
            nullable=False,
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "trust_level",
            event_trust_level,
            server_default="unverified",
            nullable=False,
        ),
    )
    op.add_column(
        "events",
        sa.Column("visibility", event_visibility, server_default="public", nullable=False),
    )
    op.add_column("events", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_foreign_key("fk_events_place_id_places", "events", "places", ["place_id"], ["id"])
    op.create_foreign_key(
        "fk_events_organizer_id_organizers",
        "events",
        "organizers",
        ["organizer_id"],
        ["id"],
    )
    op.create_index(op.f("ix_events_place_id"), "events", ["place_id"], unique=False)
    op.create_index(op.f("ix_events_organizer_id"), "events", ["organizer_id"], unique=False)
    op.create_index(op.f("ix_events_status"), "events", ["status"], unique=False)
    op.create_index(op.f("ix_events_provenance"), "events", ["provenance"], unique=False)
    op.create_index(op.f("ix_events_trust_level"), "events", ["trust_level"], unique=False)
    op.create_index(op.f("ix_events_visibility"), "events", ["visibility"], unique=False)
    op.create_index(
        "ix_events_status_visibility_start_time",
        "events",
        ["status", "visibility", "start_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_events_status_visibility_start_time", table_name="events")
    op.drop_index(op.f("ix_events_visibility"), table_name="events")
    op.drop_index(op.f("ix_events_trust_level"), table_name="events")
    op.drop_index(op.f("ix_events_provenance"), table_name="events")
    op.drop_index(op.f("ix_events_status"), table_name="events")
    op.drop_index(op.f("ix_events_organizer_id"), table_name="events")
    op.drop_index(op.f("ix_events_place_id"), table_name="events")
    op.drop_constraint("fk_events_organizer_id_organizers", "events", type_="foreignkey")
    op.drop_constraint("fk_events_place_id_places", "events", type_="foreignkey")
    op.drop_column("events", "removed_at")
    op.drop_column("events", "expired_at")
    op.drop_column("events", "published_at")
    op.drop_column("events", "approved_at")
    op.drop_column("events", "visibility")
    op.drop_column("events", "trust_level")
    op.drop_column("events", "provenance")
    op.drop_column("events", "status")
    op.drop_column("events", "organizer_id")
    op.drop_column("events", "place_id")
