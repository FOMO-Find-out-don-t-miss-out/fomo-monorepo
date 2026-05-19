"""remove_legacy_parent_ids

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-05-19 17:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a6b7c8d9e0f1"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO event_relations (
            id,
            parent_event_id,
            child_event_id,
            relation_type,
            created_at
        )
        SELECT
            gen_random_uuid(),
            child.parent_id,
            child.id,
            'child_event'::event_relation_type,
            now()
        FROM events AS child
        JOIN events AS parent ON parent.id = child.parent_id
        WHERE child.parent_id IS NOT NULL
          AND child.parent_id <> child.id
        ON CONFLICT (parent_event_id, child_event_id, relation_type) DO NOTHING
        """
    )

    op.execute("DROP INDEX IF EXISTS ix_pending_events_parent_id")
    op.execute("DROP INDEX IF EXISTS ix_events_parent_id")
    op.drop_column("pending_events", "parent_id")
    op.drop_column("events", "parent_id")


def downgrade() -> None:
    op.add_column("events", sa.Column("parent_id", sa.Uuid(), nullable=True))
    op.add_column("pending_events", sa.Column("parent_id", sa.Uuid(), nullable=True))
    op.create_index("ix_events_parent_id", "events", ["parent_id"], unique=False)
    op.create_index("ix_pending_events_parent_id", "pending_events", ["parent_id"], unique=False)

    # Best effort only: pending_events.parent_id cannot be reconstructed from event_relations,
    # and historical self-parent rows are intentionally not recreated.
    op.execute(
        """
        UPDATE events AS child
        SET parent_id = relation.parent_event_id
        FROM event_relations AS relation
        WHERE relation.child_event_id = child.id
          AND relation.relation_type = 'child_event'::event_relation_type
        """
    )
