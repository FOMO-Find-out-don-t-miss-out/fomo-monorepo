"""cleanup_exclusive_intent_relationships

Remove 'interested' rows where the same (user_id, event_id) also has a 'going'
row. Product rule: going is the stronger intent and wins. This is a one-time
cleanup for any legacy data created before the mutual-exclusivity rule was
enforced at the service layer.

Revision ID: c1d2e3f4a5b6
Revises: fd52b6852189
Create Date: 2026-06-24 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c1d2e3f4a5b6"
down_revision = "fd52b6852189"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    # Deleted rows cannot be restored; no-op is intentional.
    pass
