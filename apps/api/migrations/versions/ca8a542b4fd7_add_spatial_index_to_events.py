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
    op.create_index(
        "idx_events_location",
        "events",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("idx_events_location", table_name="events")
