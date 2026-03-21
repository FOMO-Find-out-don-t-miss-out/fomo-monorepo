"""add_country_code_to_pending_events

Revision ID: eea2caf92ee6
Revises: b2c3d4e5f6a1
Create Date: 2026-03-20 23:09:36.471257

"""
from alembic import op
import sqlalchemy as sa

revision = 'eea2caf92ee6'
down_revision = 'b2c3d4e5f6a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('pending_events', sa.Column('country_code', sa.String(length=2), nullable=True))
    op.create_index(op.f('ix_pending_events_country_code'), 'pending_events', ['country_code'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_pending_events_country_code'), table_name='pending_events')
    op.drop_column('pending_events', 'country_code')
