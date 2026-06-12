"""add_user_system_role

FOMO-149: Add system_role to the users table for backend RBAC.

Changes:
- Create PostgreSQL enum type "user_system_role" with values
  admin | manager | moderator | user | service.
- Add users.system_role column (non-nullable, default "user").

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-12 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None

_ENUM_VALUES = ("admin", "manager", "moderator", "user", "service")
_ENUM_NAME = "user_system_role"


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*_ENUM_VALUES, name=_ENUM_NAME).create(bind, checkfirst=True)

    op.add_column(
        "users",
        sa.Column(
            "system_role",
            postgresql.ENUM(*_ENUM_VALUES, name=_ENUM_NAME, create_type=False),
            nullable=False,
            server_default="user",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "system_role")
    bind = op.get_bind()
    postgresql.ENUM(name=_ENUM_NAME).drop(bind, checkfirst=True)
