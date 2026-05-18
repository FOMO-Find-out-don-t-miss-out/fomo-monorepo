"""rename_venues_to_places

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-05-18 19:00:00.000000

"""

import geoalchemy2
import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e8f9a0b1c2d3"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    place_type = postgresql.ENUM(
        "venue",
        "outdoor_area",
        "route_start",
        "temporary_spot",
        "unknown",
        name="place_type",
        create_type=False,
    )
    place_verification_status = postgresql.ENUM(
        "unverified",
        "system_matched",
        "manually_verified",
        name="place_verification_status",
        create_type=False,
    )

    op.rename_table("venues", "places")
    op.execute("ALTER INDEX ix_venues_name RENAME TO ix_places_name")
    op.execute("ALTER INDEX ix_venues_country_code RENAME TO ix_places_country_code")
    op.execute("ALTER INDEX ix_venues_city RENAME TO ix_places_city")
    op.execute("ALTER INDEX ix_venues_name_country RENAME TO ix_places_name_country")
    op.execute("ALTER INDEX venues_pkey RENAME TO places_pkey")

    op.alter_column("places", "relevance", new_column_name="match_confidence")
    op.add_column(
        "places",
        sa.Column("normalized_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "places",
        sa.Column(
            "location",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeogFromText",
                name="geography",
                spatial_index=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "places",
        sa.Column("place_type", place_type, server_default="unknown", nullable=False),
    )
    op.add_column(
        "places",
        sa.Column(
            "verification_status",
            place_verification_status,
            server_default="unverified",
            nullable=False,
        ),
    )
    op.add_column(
        "places",
        sa.Column("source_provider", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "places",
        sa.Column("external_place_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )

    op.execute("UPDATE places SET normalized_name = lower(name) WHERE normalized_name IS NULL")
    op.execute(
        """
        UPDATE places
        SET location = ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography
        WHERE location IS NULL
        """
    )
    op.execute(
        """
        UPDATE places
        SET verification_status = CASE
            WHEN is_manually_verified THEN 'manually_verified'::place_verification_status
            ELSE 'unverified'::place_verification_status
        END
        """
    )

    op.create_index(op.f("ix_places_normalized_name"), "places", ["normalized_name"], unique=False)
    op.create_index(op.f("ix_places_source_provider"), "places", ["source_provider"], unique=False)
    op.create_index(
        op.f("ix_places_external_place_id"),
        "places",
        ["external_place_id"],
        unique=False,
    )
    op.create_index("idx_places_location", "places", ["location"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("idx_places_location", table_name="places")
    op.drop_index(op.f("ix_places_external_place_id"), table_name="places")
    op.drop_index(op.f("ix_places_source_provider"), table_name="places")
    op.drop_index(op.f("ix_places_normalized_name"), table_name="places")

    op.drop_column("places", "external_place_id")
    op.drop_column("places", "source_provider")
    op.drop_column("places", "verification_status")
    op.drop_column("places", "place_type")
    op.drop_column("places", "location")
    op.drop_column("places", "normalized_name")
    op.alter_column("places", "match_confidence", new_column_name="relevance")

    op.execute("ALTER INDEX ix_places_name_country RENAME TO ix_venues_name_country")
    op.execute("ALTER INDEX ix_places_city RENAME TO ix_venues_city")
    op.execute("ALTER INDEX ix_places_country_code RENAME TO ix_venues_country_code")
    op.execute("ALTER INDEX ix_places_name RENAME TO ix_venues_name")
    op.execute("ALTER INDEX places_pkey RENAME TO venues_pkey")
    op.rename_table("places", "venues")
