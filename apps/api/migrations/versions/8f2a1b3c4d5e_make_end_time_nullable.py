"""make_end_time_nullable

Revision ID: 8f2a1b3c4d5e
Revises: 62be54ada7f4
Create Date: 2026-03-20 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8f2a1b3c4d5e"
down_revision = "62be54ada7f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make end_time nullable in events table
    op.alter_column("events", "end_time", existing_type=sa.DateTime(), nullable=True)

    # Make end_time nullable in pending_events table
    op.alter_column("pending_events", "end_time", existing_type=sa.DateTime(), nullable=True)


def downgrade() -> None:
    # Note: downgrading might fail if there are already NULL values
    op.alter_column("pending_events", "end_time", existing_type=sa.DateTime(), nullable=False)

    op.alter_column("events", "end_time", existing_type=sa.DateTime(), nullable=False)
