"""update_users_keycloak_sync

FOMO-148: Prepare the users table for Keycloak identity sync.

Changes:
- users.email: DROP NOT NULL constraint so users without an email claim
  in their JWT token can still be created.  The UNIQUE index is kept.
- users.phone_number: nullable VARCHAR, reserved for future OTP flow.
- users.phone_verified: non-nullable BOOLEAN, default false.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-11 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(), nullable=True)
    op.add_column("users", sa.Column("phone_number", sa.String(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "phone_verified",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "phone_verified")
    op.drop_column("users", "phone_number")
    # Restore NOT NULL — will fail if any row has email=NULL in production.
    op.alter_column("users", "email", existing_type=sa.String(), nullable=False)
