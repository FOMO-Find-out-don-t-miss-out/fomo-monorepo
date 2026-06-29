"""enforce_single_intent_per_user_event

Merge the cleanup branch (c1d2e3f4a5b6) into the main chain and add a
partial unique index that makes the product invariant DB-enforceable:

  A user may have at most ONE intent row (interested OR going) per event.
  The 'saved' type is intentionally excluded from this constraint.

upgrade:
  1. Re-runs the interested-wins-over-going cleanup (idempotent; the branch
     migration may not have been applied on all environments).
  2. Creates a partial unique index on (user_id, event_id) filtered to
     relationship_type IN ('interested', 'going').

downgrade:
  Drops the partial unique index only. The deleted rows are not restored.

Revision ID: 2c3d4e5f6a7b
Revises:     1b2c3d4e5f6a  (main chain head)
             c1d2e3f4a5b6  (cleanup branch — merges it into the main chain)
Create Date: 2026-06-29 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "2c3d4e5f6a7b"
down_revision = ("1b2c3d4e5f6a", "c1d2e3f4a5b6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1 — idempotent cleanup: if going wins, delete any remaining
    # interested rows that coexist with going for the same (user, event).
    # This catches environments where the branch migration was not applied.
    op.execute(
        sa.text(
            """
            DELETE FROM event_relationships
            WHERE relationship_type = 'interested'
              AND (user_id, event_id) IN (
                  SELECT user_id, event_id
                  FROM event_relationships
                  WHERE relationship_type = 'going'
              )
            """
        )
    )

    # Step 2 — DB-level guard: partial unique index prevents any future
    # concurrent INSERT from creating a second intent row.
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_event_relationships_single_intent
            ON event_relationships (user_id, event_id)
            WHERE relationship_type::text IN ('interested', 'going')
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DROP INDEX IF EXISTS uq_event_relationships_single_intent")
    )
