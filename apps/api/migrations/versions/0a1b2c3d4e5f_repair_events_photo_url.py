"""repair_events_photo_url

The earlier migration a4dd20041efb_add_photo_url_to_events was committed as
an empty stub (upgrade body is `pass`), so the events.photo_url column was
never created in the database.

photo_url is declared on EventBase which is shared by both Event and
PendingEvent.  The pending_events column was fixed in d4e5f6a7b8c9; this
migration closes the matching gap on events.

Revision ID: 0a1b2c3d4e5f
Revises: f6a7b8c9d0e1
Create Date: 2026-06-12 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0a1b2c3d4e5f"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE events ADD COLUMN IF NOT EXISTS photo_url VARCHAR")


def downgrade() -> None:
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS photo_url")
