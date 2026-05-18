"""add_lifecycle_provenance_trust_visibility_enums

Revision ID: c6e7f8a9b0c1
Revises: ca8a542b4fd7
Create Date: 2026-05-18 18:00:00.000000

"""

from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c6e7f8a9b0c1"
down_revision = "ca8a542b4fd7"
branch_labels = None
depends_on = None


ENUM_TYPES = (
    (
        "event_status",
        (
            "approved",
            "live",
            "expired",
            "archived",
            "under_investigation",
            "removed",
        ),
    ),
    (
        "event_provenance",
        (
            "aggregated",
            "community_submitted",
            "claimed_official",
            "verified_organizer",
        ),
    ),
    (
        "event_trust_level",
        (
            "unverified",
            "community_validated",
            "trusted_source",
            "official",
        ),
    ),
    (
        "event_visibility",
        (
            "public",
            "hidden",
            "shadow_hidden",
            "restricted",
        ),
    ),
    (
        "submission_type",
        (
            "harvested",
            "community_submission",
            "organizer_submission",
            "claim_conversion",
        ),
    ),
    (
        "dedupe_status",
        (
            "not_checked",
            "no_match",
            "possible_match",
            "merged",
            "duplicate_confirmed",
        ),
    ),
    (
        "event_relation_type",
        (
            "series",
            "occurrence",
            "bundle",
            "child_event",
        ),
    ),
    (
        "relationship_type",
        (
            "interested",
            "saved",
            "going",
        ),
    ),
    (
        "report_status",
        (
            "open",
            "under_review",
            "resolved",
            "dismissed",
        ),
    ),
    (
        "report_resolution",
        (
            "event_removed",
            "event_kept",
            "merged",
            "needs_monitoring",
            "report_rejected",
        ),
    ),
    (
        "gps_validation_status",
        (
            "not_checked",
            "valid",
            "invalid",
            "not_available",
        ),
    ),
    (
        "organizer_verification_status",
        (
            "unverified",
            "pending",
            "verified",
            "rejected",
        ),
    ),
    (
        "place_type",
        (
            "venue",
            "outdoor_area",
            "route_start",
            "temporary_spot",
            "unknown",
        ),
    ),
    (
        "place_verification_status",
        (
            "unverified",
            "system_matched",
            "manually_verified",
        ),
    ),
    (
        "connection_status",
        (
            "pending",
            "accepted",
            "rejected",
            "blocked",
        ),
    ),
    (
        "wallet_transaction_type",
        (
            "spend",
            "refund",
            "grant",
            "adjustment",
        ),
    ),
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_name, enum_values in ENUM_TYPES:
        postgresql.ENUM(*enum_values, name=enum_name).create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for enum_name, enum_values in reversed(ENUM_TYPES):
        postgresql.ENUM(*enum_values, name=enum_name).drop(bind, checkfirst=True)
