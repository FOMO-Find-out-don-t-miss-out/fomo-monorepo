"""create_event_relationships_table

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-05-19 13:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    relationship_type = postgresql.ENUM(
        "interested",
        "saved",
        "going",
        name="relationship_type",
        create_type=False,
    )

    op.create_table(
        "event_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", relationship_type, nullable=False),
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
            name="fk_event_relationships_event_id_events",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_event_relationships_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "event_id",
            "relationship_type",
            name="uq_event_relationships_user_event_type",
        ),
    )
    op.create_index(
        "ix_event_relationships_user_id",
        "event_relationships",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_relationships_event_id",
        "event_relationships",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_relationships_relationship_type",
        "event_relationships",
        ["relationship_type"],
        unique=False,
    )
    op.create_index(
        "ix_event_relationships_user_id_relationship_type",
        "event_relationships",
        ["user_id", "relationship_type"],
        unique=False,
    )
    op.create_index(
        "ix_event_relationships_event_id_relationship_type",
        "event_relationships",
        ["event_id", "relationship_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_relationships_event_id_relationship_type",
        table_name="event_relationships",
    )
    op.drop_index(
        "ix_event_relationships_user_id_relationship_type",
        table_name="event_relationships",
    )
    op.drop_index("ix_event_relationships_relationship_type", table_name="event_relationships")
    op.drop_index("ix_event_relationships_event_id", table_name="event_relationships")
    op.drop_index("ix_event_relationships_user_id", table_name="event_relationships")
    op.drop_table("event_relationships")
