"""add_photo_url_to_pending_events

photo_url is declared in EventBase (shared by Event and PendingEvent) but the
earlier placeholder migration a4dd20041efb_add_photo_url_to_events.py has an
empty upgrade body and never materialised the column in pending_events.

The column is required by the ORM when the scraper pipeline inserts harvested
events into pending_events (FOMO-141).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-08 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE pending_events ADD COLUMN IF NOT EXISTS photo_url VARCHAR")


def downgrade() -> None:
    op.execute("ALTER TABLE pending_events DROP COLUMN IF EXISTS photo_url")
