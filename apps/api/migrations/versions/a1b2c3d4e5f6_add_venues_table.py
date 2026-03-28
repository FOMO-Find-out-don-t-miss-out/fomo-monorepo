"""add_venues_table

Revision ID: a1b2c3d4e5f6
Revises: 8f2a1b3c4d5e
Create Date: 2026-03-20 17:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "8f2a1b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "venues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("country_code", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("city", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("full_address", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("relevance", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_venues_city"), "venues", ["city"], unique=False)
    op.create_index(op.f("ix_venues_country_code"), "venues", ["country_code"], unique=False)
    op.create_index(op.f("ix_venues_name"), "venues", ["name"], unique=False)
    op.create_index("ix_venues_name_country", "venues", ["name", "country_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_venues_name_country", table_name="venues")
    op.drop_index(op.f("ix_venues_name"), table_name="venues")
    op.drop_index(op.f("ix_venues_country_code"), table_name="venues")
    op.drop_index(op.f("ix_venues_city"), table_name="venues")
    op.drop_table("venues")
