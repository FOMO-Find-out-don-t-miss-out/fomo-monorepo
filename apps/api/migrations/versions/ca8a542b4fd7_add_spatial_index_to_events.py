"""add_spatial_index_to_events

Revision ID: ca8a542b4fd7
Revises: 7ad5d76c855e
Create Date: 2026-04-07 17:46:50.910712

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "ca8a542b4fd7"
down_revision = "7ad5d76c855e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS makes this safe for fresh-reset flows where the index may already exist.
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_location ON events USING gist (location)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_events_location")
