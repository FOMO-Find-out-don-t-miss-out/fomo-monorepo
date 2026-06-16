"""Ingestion reconciliation / self-healing for pending events (FOMO-163).

Repeated scrapes and moderator place corrections can leave a PendingEvent stuck
with weak or failed location data even after a better Place candidate becomes
available. This module re-checks a pending event against the current Place
state, upgrades only the fields that are objectively weaker than what is now
known, and re-runs the same TrustEngine/ModerationService auto-approval path
used by fresh ingestion. It never touches a pending event that a moderator has
already decided on (rejected or published).
"""

import logging
from enum import StrEnum
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlmodel import Session, or_, select

from app.repositories.place_repository import PlaceRepository
from app.services.dedup.collision_detector import CollisionDetector, signature_from_pending
from app.services.moderation.moderation_service import ModerationService
from packages.domain.models import PendingEvent, Place, PlaceVerificationStatus
from packages.domain.services.event_collision_service import CollisionBucket
from packages.domain.services.trust_engine import TrustEngine

logger = logging.getLogger(__name__)

# Protected decisions a moderator has already made; reconciliation must not touch them.
PROTECTED_STATUSES = {"rejected", "published"}

# Relative strength used to decide whether new geocoding data is an upgrade.
_GEOCODING_STRENGTH = {"failed": 0, "ambiguous": 1, "verified": 2}


class ReconciliationOutcome(StrEnum):
    no_change = "no_change"
    reconciled = "reconciled"
    reconciled_and_approved = "reconciled_and_approved"
    skipped_unresolved_place = "skipped_unresolved_place"
    skipped_protected = "skipped_protected"
    skipped_duplicate_risk = "skipped_duplicate_risk"


class ReconciliationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.places = PlaceRepository(db)

    def reconcile_pending_event(
        self, pending: PendingEvent, *, dry_run: bool = False
    ) -> ReconciliationOutcome:
        """Repairs weak/failed location data on a pending event and re-runs auto-approval.

        Only acts on events still awaiting moderation (status == "pending"); a
        manually rejected or already-published event is left untouched.
        """
        if pending.status in PROTECTED_STATUSES:
            logger.info(
                "[RECONCILE] Skipped protected pending event (status=%s): '%s'",
                pending.status,
                pending.title,
            )
            return ReconciliationOutcome.skipped_protected

        changed = self._upgrade_location(pending)
        outcome = ReconciliationOutcome.reconciled if changed else ReconciliationOutcome.no_change

        place_is_resolved = self._is_place_resolved(pending.place_candidate_id)
        eligible_for_approval = False

        if pending.place_candidate_id and not place_is_resolved:
            if not changed:
                outcome = ReconciliationOutcome.skipped_unresolved_place
            logger.info(
                "[RECONCILE] Place still unresolved for '%s'; staying pending.", pending.title
            )
        else:
            trust_engine = TrustEngine(country_code=pending.country_code or "GR")
            if trust_engine.is_trusted_for_autopublish(pending):
                if self._has_conflicting_live_event(pending):
                    outcome = ReconciliationOutcome.skipped_duplicate_risk
                    logger.info(
                        "[RECONCILE] Skipped duplicate/conflict risk for '%s'", pending.title
                    )
                else:
                    eligible_for_approval = True

        if dry_run:
            self.db.rollback()
            if eligible_for_approval:
                return ReconciliationOutcome.reconciled_and_approved
            return outcome

        self.db.add(pending)
        self.db.commit()

        if eligible_for_approval:
            approved = ModerationService(self.db).approve_events(
                [pending.id],
                review_notes="Auto-approved by ingestion reconciliation (FOMO-163)",
            )
            if approved:
                logger.info("[RECONCILE] Reconciled and auto-approved '%s'", pending.title)
                return ReconciliationOutcome.reconciled_and_approved

        logger.info("[RECONCILE] %s for '%s'", outcome.value, pending.title)
        return outcome

    def reconcile_historical(
        self, *, batch_size: int = 100, dry_run: bool = False
    ) -> dict[str, int]:
        """Batch self-healing pass over pending events with weak/failed location data.

        Idempotent and safe to re-run: only pending events with failed/ambiguous
        geocoding or a missing place candidate are revisited, and protected
        (rejected/published) rows are always skipped.
        """
        stats: dict[str, int] = dict.fromkeys(
            [outcome.value for outcome in ReconciliationOutcome], 0
        )
        stats["scanned"] = 0
        processed: set[UUID] = set()

        while True:
            statement = (
                select(PendingEvent)
                .where(
                    PendingEvent.status == "pending",
                    or_(
                        PendingEvent.geocoding_status.in_(["failed", "ambiguous"]),
                        PendingEvent.place_candidate_id.is_(None),
                    ),
                )
                .limit(batch_size)
            )
            if processed:
                statement = statement.where(PendingEvent.id.not_in(processed))

            batch = self.db.exec(statement).all()
            if not batch:
                break

            for pending in batch:
                processed.add(pending.id)
                stats["scanned"] += 1
                outcome = self.reconcile_pending_event(pending, dry_run=dry_run)
                stats[outcome.value] += 1

        return stats

    def _upgrade_location(self, pending: PendingEvent) -> bool:
        """Updates only fields that are objectively weaker than newly available data."""
        candidate = self._find_better_place(pending)
        if candidate is None:
            return False

        changed = False
        if pending.place_candidate_id != candidate.id:
            pending.place_candidate_id = candidate.id
            changed = True

        new_status = self._status_for_place(candidate)
        current_strength = _GEOCODING_STRENGTH.get(pending.geocoding_status, 0)
        if _GEOCODING_STRENGTH[new_status] > current_strength:
            pending.geocoding_status = new_status
            pending.confidence_score = (
                1.0 if new_status == "verified" else candidate.match_confidence
            )
            pending.location = WKTElement(f"POINT({candidate.lng} {candidate.lat})", srid=4326)
            pending.geocoding_metadata = {
                **(pending.geocoding_metadata or {}),
                "source": "reconciliation",
                "full_address": candidate.full_address,
                "city": candidate.city,
            }
            changed = True

        return changed

    def _find_better_place(self, pending: PendingEvent) -> Place | None:
        if not pending.location_name:
            return None

        current = (
            self.db.get(Place, pending.place_candidate_id) if pending.place_candidate_id else None
        )
        if current and self._is_resolved(current) and self._is_verified(current):
            return None  # already as strong as it gets — never downgrade

        city_hint = (pending.geocoding_metadata or {}).get("city")
        found = self.places.get_by_name(
            pending.location_name, pending.country_code or "GR", city_hint=city_hint
        )
        if not found or not self._is_resolved(found):
            return None

        if (
            current
            and self._is_resolved(current)
            and current.id != found.id
            and not self._is_verified(found)
        ):
            # Current candidate already has coordinates from a different place —
            # only swap it for a manually verified place (stronger evidence).
            return None

        return found

    @staticmethod
    def _status_for_place(place: Place) -> str:
        return "verified" if ReconciliationService._is_verified(place) else "ambiguous"

    @staticmethod
    def _is_resolved(place: Place) -> bool:
        return place.lat is not None and place.lng is not None

    @staticmethod
    def _is_verified(place: Place) -> bool:
        return place.verification_status == PlaceVerificationStatus.manually_verified

    def _is_place_resolved(self, place_id: UUID | None) -> bool:
        if not place_id:
            return True
        place = self.db.get(Place, place_id)
        return bool(place and self._is_resolved(place))

    def _has_conflicting_live_event(self, pending: PendingEvent) -> bool:
        """FOMO-16: shared collision detection, conservative by design — any
        non-no_collision match against a live event blocks auto-approval here,
        consistent with the policy already enforced for fresh ingestion.
        """
        signature = signature_from_pending(self.db, pending)
        assessment = CollisionDetector(self.db).assess(signature, exclude_pending_id=pending.id)
        return (
            assessment.best_live_match is not None
            and assessment.best_live_match.score.bucket is not CollisionBucket.no_collision
        )
