"""extend_pending_events_workflow_fields

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-05-18 20:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a0b1c2d3e4f5"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    submission_type = postgresql.ENUM(
        "harvested",
        "community_submission",
        "organizer_submission",
        "claim_conversion",
        name="submission_type",
        create_type=False,
    )
    dedupe_status = postgresql.ENUM(
        "not_checked",
        "no_match",
        "possible_match",
        "merged",
        "duplicate_confirmed",
        name="dedupe_status",
        create_type=False,
    )

    op.add_column(
        "pending_events",
        sa.Column("submission_type", submission_type, server_default="harvested", nullable=False),
    )
    op.add_column(
        "pending_events",
        sa.Column(
            "dedupe_status",
            dedupe_status,
            server_default="not_checked",
            nullable=False,
        ),
    )
    op.add_column("pending_events", sa.Column("candidate_event_id", sa.Uuid(), nullable=True))
    op.add_column("pending_events", sa.Column("place_candidate_id", sa.Uuid(), nullable=True))
    op.add_column("pending_events", sa.Column("reviewed_by", sa.Uuid(), nullable=True))
    op.add_column(
        "pending_events",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("pending_events", sa.Column("review_notes", sa.Text(), nullable=True))

    op.create_foreign_key(
        "fk_pending_events_candidate_event_id_events",
        "pending_events",
        "events",
        ["candidate_event_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_pending_events_place_candidate_id_places",
        "pending_events",
        "places",
        ["place_candidate_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_pending_events_reviewed_by_users",
        "pending_events",
        "users",
        ["reviewed_by"],
        ["id"],
    )
    op.create_index(
        op.f("ix_pending_events_submission_type"),
        "pending_events",
        ["submission_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pending_events_dedupe_status"),
        "pending_events",
        ["dedupe_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pending_events_candidate_event_id"),
        "pending_events",
        ["candidate_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pending_events_place_candidate_id"),
        "pending_events",
        ["place_candidate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pending_events_reviewed_by"),
        "pending_events",
        ["reviewed_by"],
        unique=False,
    )
    op.create_index(
        "ix_pending_events_status_dedupe_status",
        "pending_events",
        ["status", "dedupe_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pending_events_status_dedupe_status", table_name="pending_events")
    op.drop_index(op.f("ix_pending_events_reviewed_by"), table_name="pending_events")
    op.drop_index(op.f("ix_pending_events_place_candidate_id"), table_name="pending_events")
    op.drop_index(op.f("ix_pending_events_candidate_event_id"), table_name="pending_events")
    op.drop_index(op.f("ix_pending_events_dedupe_status"), table_name="pending_events")
    op.drop_index(op.f("ix_pending_events_submission_type"), table_name="pending_events")
    op.drop_constraint(
        "fk_pending_events_reviewed_by_users",
        "pending_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_pending_events_place_candidate_id_places",
        "pending_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_pending_events_candidate_event_id_events",
        "pending_events",
        type_="foreignkey",
    )
    op.drop_column("pending_events", "review_notes")
    op.drop_column("pending_events", "reviewed_at")
    op.drop_column("pending_events", "reviewed_by")
    op.drop_column("pending_events", "place_candidate_id")
    op.drop_column("pending_events", "candidate_event_id")
    op.drop_column("pending_events", "dedupe_status")
    op.drop_column("pending_events", "submission_type")
