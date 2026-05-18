"""create_wallet_tables_refactor_hype_ledger

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-05-19 15:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    wallet_transaction_type = postgresql.ENUM(
        "spend",
        "refund",
        "grant",
        "adjustment",
        name="wallet_transaction_type",
        create_type=False,
    )

    op.drop_table("hype_ledger")
    op.drop_column("profiles", "fomo_coins")

    op.create_table(
        "wallet_accounts",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("balance", sa.Integer(), server_default="0", nullable=False),
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
            ["user_id"],
            ["users.id"],
            name="fk_wallet_accounts_user_id_users",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "wallet_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("transaction_type", wallet_transaction_type, nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            name="fk_wallet_transactions_event_id_events",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_wallet_transactions_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wallet_transactions_user_id",
        "wallet_transactions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_wallet_transactions_event_id",
        "wallet_transactions",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        "ix_wallet_transactions_transaction_type",
        "wallet_transactions",
        ["transaction_type"],
        unique=False,
    )
    op.create_index(
        "ix_wallet_transactions_source",
        "wallet_transactions",
        ["source"],
        unique=False,
    )
    op.create_index(
        "ix_wallet_transactions_user_id_created_at",
        "wallet_transactions",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_wallet_transactions_event_id_transaction_type",
        "wallet_transactions",
        ["event_id", "transaction_type"],
        unique=False,
    )

    op.create_table(
        "hype_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("wallet_transaction_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            name="fk_hype_ledger_event_id_events",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_hype_ledger_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["wallet_transaction_id"],
            ["wallet_transactions.id"],
            name="fk_hype_ledger_wallet_transaction_id_wallet_transactions",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hype_ledger_user_id", "hype_ledger", ["user_id"], unique=False)
    op.create_index("ix_hype_ledger_event_id", "hype_ledger", ["event_id"], unique=False)
    op.create_index(
        "ix_hype_ledger_wallet_transaction_id",
        "hype_ledger",
        ["wallet_transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_hype_ledger_event_id_created_at",
        "hype_ledger",
        ["event_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_hype_ledger_user_id_created_at",
        "hype_ledger",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_hype_ledger_user_id_created_at", table_name="hype_ledger")
    op.drop_index("ix_hype_ledger_event_id_created_at", table_name="hype_ledger")
    op.drop_index("ix_hype_ledger_wallet_transaction_id", table_name="hype_ledger")
    op.drop_index("ix_hype_ledger_event_id", table_name="hype_ledger")
    op.drop_index("ix_hype_ledger_user_id", table_name="hype_ledger")
    op.drop_table("hype_ledger")
    op.drop_index(
        "ix_wallet_transactions_event_id_transaction_type",
        table_name="wallet_transactions",
    )
    op.drop_index("ix_wallet_transactions_user_id_created_at", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_source", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_transaction_type", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_event_id", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_user_id", table_name="wallet_transactions")
    op.drop_table("wallet_transactions")
    op.drop_table("wallet_accounts")
    op.add_column(
        "profiles",
        sa.Column("fomo_coins", sa.Integer(), server_default="100", nullable=False),
    )
    op.create_table(
        "hype_ledger",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
