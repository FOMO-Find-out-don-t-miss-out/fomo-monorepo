"""create_organizers_table

Revision ID: d7e8f9a0b1c2
Revises: c6e7f8a9b0c1
Create Date: 2026-05-18 18:30:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d7e8f9a0b1c2"
down_revision = "c6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    organizer_verification_status = postgresql.ENUM(
        "unverified",
        "pending",
        "verified",
        "rejected",
        name="organizer_verification_status",
        create_type=False,
    )

    op.create_table(
        "organizers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("slug", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("website_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("instagram_handle", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("contact_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "verification_status",
            organizer_verification_status,
            server_default="unverified",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizers_display_name", "organizers", ["display_name"], unique=False)
    op.create_index("ix_organizers_slug", "organizers", ["slug"], unique=True)
    op.create_index(
        "ix_organizers_verification_status",
        "organizers",
        ["verification_status"],
        unique=False,
    )
    op.create_index(
        "ix_organizers_instagram_handle",
        "organizers",
        ["instagram_handle"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_organizers_instagram_handle", table_name="organizers")
    op.drop_index("ix_organizers_verification_status", table_name="organizers")
    op.drop_index("ix_organizers_slug", table_name="organizers")
    op.drop_index("ix_organizers_display_name", table_name="organizers")
    op.drop_table("organizers")
