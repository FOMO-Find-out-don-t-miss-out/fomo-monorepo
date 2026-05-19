"""replace_social_connections

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-05-19 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection_status = postgresql.ENUM(
        "pending",
        "accepted",
        "rejected",
        "blocked",
        name="connection_status",
        create_type=False,
    )

    op.drop_table("social_connections")

    op.create_table(
        "user_connections",
        sa.Column("requester_user_id", sa.Uuid(), nullable=False),
        sa.Column("addressee_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", connection_status, server_default="pending", nullable=False),
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
        sa.CheckConstraint(
            "requester_user_id <> addressee_user_id",
            name="ck_user_connections_no_self_connection",
        ),
        sa.ForeignKeyConstraint(
            ["addressee_user_id"],
            ["users.id"],
            name="fk_user_connections_addressee_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["requester_user_id"],
            ["users.id"],
            name="fk_user_connections_requester_user_id_users",
        ),
        sa.PrimaryKeyConstraint("requester_user_id", "addressee_user_id"),
    )
    op.create_index(
        "ix_user_connections_requester_user_id",
        "user_connections",
        ["requester_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_connections_addressee_user_id",
        "user_connections",
        ["addressee_user_id"],
        unique=False,
    )
    op.create_index("ix_user_connections_status", "user_connections", ["status"], unique=False)
    op.create_index(
        "ix_user_connections_requester_user_id_status",
        "user_connections",
        ["requester_user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_user_connections_addressee_user_id_status",
        "user_connections",
        ["addressee_user_id", "status"],
        unique=False,
    )

    op.create_table(
        "organizer_followers",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organizer_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["organizer_id"],
            ["organizers.id"],
            name="fk_organizer_followers_organizer_id_organizers",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_organizer_followers_user_id_users",
        ),
        sa.PrimaryKeyConstraint("user_id", "organizer_id"),
    )
    op.create_index(
        "ix_organizer_followers_user_id",
        "organizer_followers",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_organizer_followers_organizer_id",
        "organizer_followers",
        ["organizer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_organizer_followers_organizer_id", table_name="organizer_followers")
    op.drop_index("ix_organizer_followers_user_id", table_name="organizer_followers")
    op.drop_table("organizer_followers")
    op.drop_index("ix_user_connections_addressee_user_id_status", table_name="user_connections")
    op.drop_index("ix_user_connections_requester_user_id_status", table_name="user_connections")
    op.drop_index("ix_user_connections_status", table_name="user_connections")
    op.drop_index("ix_user_connections_addressee_user_id", table_name="user_connections")
    op.drop_index("ix_user_connections_requester_user_id", table_name="user_connections")
    op.drop_table("user_connections")
    op.create_table(
        "social_connections",
        sa.Column("follower_id", sa.Uuid(), nullable=False),
        sa.Column("following_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["following_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("follower_id", "following_id"),
        sa.UniqueConstraint("follower_id", "following_id", name="unique_follow"),
    )
