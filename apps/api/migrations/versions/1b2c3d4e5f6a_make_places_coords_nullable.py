"""make_places_coords_nullable

Allow unresolved place candidates (no coordinates) to be created when geocoding
fails during ingestion. Previously lat, lng, and full_address were NOT NULL,
preventing any Place row that doesn't yet have a confirmed location.

Revision ID: 1b2c3d4e5f6a
Revises: 0a1b2c3d4e5f
Create Date: 2026-06-16 00:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "1b2c3d4e5f6a"
down_revision = "0a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("places", "lat", existing_type=sa.Float(), nullable=True)
    op.alter_column("places", "lng", existing_type=sa.Float(), nullable=True)
    op.alter_column(
        "places",
        "full_address",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        nullable=True,
    )


def downgrade() -> None:
    # Rows with NULL coords must be removed or back-filled before downgrading.
    op.execute("DELETE FROM places WHERE lat IS NULL OR lng IS NULL OR full_address IS NULL")
    op.alter_column(
        "places",
        "full_address",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        nullable=False,
    )
    op.alter_column("places", "lng", existing_type=sa.Float(), nullable=False)
    op.alter_column("places", "lat", existing_type=sa.Float(), nullable=False)
