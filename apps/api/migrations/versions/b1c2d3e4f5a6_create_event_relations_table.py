"""create_event_relations_table

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-05-19 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    event_relation_type = postgresql.ENUM(
        "series",
        "occurrence",
        "bundle",
        "child_event",
        name="event_relation_type",
        create_type=False,
    )

    op.create_table(
        "event_relations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_event_id", sa.Uuid(), nullable=False),
        sa.Column("child_event_id", sa.Uuid(), nullable=False),
        sa.Column("relation_type", event_relation_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "parent_event_id <> child_event_id",
            name="ck_event_relations_no_self_relation",
        ),
        sa.ForeignKeyConstraint(
            ["child_event_id"],
            ["events.id"],
            name="fk_event_relations_child_event_id_events",
        ),
        sa.ForeignKeyConstraint(
            ["parent_event_id"],
            ["events.id"],
            name="fk_event_relations_parent_event_id_events",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "parent_event_id",
            "child_event_id",
            "relation_type",
            name="uq_event_relations_parent_child_type",
        ),
    )
    op.create_index(
        "ix_event_relations_parent_event_id",
        "event_relations",
        ["parent_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_relations_child_event_id",
        "event_relations",
        ["child_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_relations_relation_type",
        "event_relations",
        ["relation_type"],
        unique=False,
    )
    op.create_index(
        "ix_event_relations_parent_event_id_relation_type",
        "event_relations",
        ["parent_event_id", "relation_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_event_relations_parent_event_id_relation_type", table_name="event_relations")
    op.drop_index("ix_event_relations_relation_type", table_name="event_relations")
    op.drop_index("ix_event_relations_child_event_id", table_name="event_relations")
    op.drop_index("ix_event_relations_parent_event_id", table_name="event_relations")
    op.drop_table("event_relations")
