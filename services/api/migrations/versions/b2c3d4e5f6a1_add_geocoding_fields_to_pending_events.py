"""add_geocoding_fields_to_pending_events

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-03-20 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a1'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('pending_events', 
        sa.Column('location_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True)
    )
    op.add_column('pending_events', 
        sa.Column('confidence_score', sa.Float(), nullable=True)
    )
    op.add_column('pending_events', 
        sa.Column('geocoding_status', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='failed')
    )
    op.add_column('pending_events', 
        sa.Column('geocoding_metadata', sa.JSON(), nullable=False, server_default='{}')
    )
    op.create_index(op.f('ix_pending_events_geocoding_status'), 'pending_events', ['geocoding_status'], unique=False)
    op.create_index(op.f('ix_pending_events_location_name'), 'pending_events', ['location_name'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_pending_events_location_name'), table_name='pending_events', if_exists=True)
    op.drop_index(op.f('ix_pending_events_geocoding_status'), table_name='pending_events', if_exists=True)
    op.drop_column('pending_events', 'geocoding_metadata')
    op.drop_column('pending_events', 'geocoding_status')
    op.drop_column('pending_events', 'confidence_score')
    op.drop_column('pending_events', 'location_name')