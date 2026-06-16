"""Tests for ingestion reconciliation / self-healing (FOMO-163)."""

from datetime import UTC, datetime, timedelta

from app.services.harvester.reconciliation_service import (
    ReconciliationOutcome,
    ReconciliationService,
)
from sqlmodel import Session, select

from packages.domain.models import Event, EventProvenance, EventStatus, PendingEvent, Place
from packages.domain.models.place import PlaceVerificationStatus

FUTURE = datetime.now(UTC) + timedelta(days=30)


def make_place(**kwargs: object) -> Place:
    defaults: dict[str, object] = dict(country_code="GR", relevance=1.0)
    defaults.update(kwargs)
    return Place(**defaults)


def make_pending(**kwargs: object) -> PendingEvent:
    defaults: dict[str, object] = dict(
        title="Some Event",
        start_time=FUTURE,
        status="pending",
        geocoding_status="failed",
        ingestion_method="json_ld",
        country_code="GR",
    )
    defaults.update(kwargs)
    return PendingEvent(**defaults)


def test_missing_place_candidate_id_backfilled_without_auto_approval(session: Session) -> None:
    place = make_place(
        name="Hidden Hall",
        lat=37.9,
        lng=23.7,
        full_address="Main St",
        verification_status=PlaceVerificationStatus.manually_verified,
    )
    pending = make_pending(
        title="No Manual Trust",
        location_name="Hidden Hall",
        ingestion_method="manual",  # fails TrustEngine source gate on purpose
    )
    session.add_all([place, pending])
    session.commit()

    outcome = ReconciliationService(session).reconcile_pending_event(pending)

    assert outcome == ReconciliationOutcome.reconciled
    session.refresh(pending)
    assert pending.place_candidate_id == place.id
    assert pending.geocoding_status == "verified"
    assert pending.status == "pending"


def test_auto_approval_after_full_reconciliation(session: Session) -> None:
    place = make_place(
        name="Resolved Arena",
        lat=37.9,
        lng=23.7,
        full_address="Main St",
        verification_status=PlaceVerificationStatus.manually_verified,
    )
    pending = make_pending(title="Big Show", location_name="Resolved Arena")
    session.add_all([place, pending])
    session.commit()

    outcome = ReconciliationService(session).reconcile_pending_event(pending)

    assert outcome == ReconciliationOutcome.reconciled_and_approved
    session.refresh(pending)
    assert pending.status == "published"
    assert pending.place_candidate_id == place.id

    live = session.exec(select(Event).where(Event.title == "Big Show")).first()
    assert live is not None
    assert live.place_id == place.id


def test_unresolved_place_stays_pending_no_auto_approval(session: Session) -> None:
    place = make_place(name="Ghost Venue", verification_status=PlaceVerificationStatus.unverified)
    pending = make_pending(
        title="Mystery Gig", location_name="Ghost Venue", place_candidate_id=place.id
    )
    session.add_all([place, pending])
    session.commit()

    outcome = ReconciliationService(session).reconcile_pending_event(pending)

    assert outcome == ReconciliationOutcome.skipped_unresolved_place
    session.refresh(pending)
    assert pending.status == "pending"
    assert session.exec(select(Event).where(Event.title == "Mystery Gig")).first() is None


def test_no_upgrade_when_no_place_candidate_exists(session: Session) -> None:
    pending = make_pending(title="Lonely Event", location_name="Nowhere Special")
    session.add(pending)
    session.commit()

    outcome = ReconciliationService(session).reconcile_pending_event(pending)

    assert outcome == ReconciliationOutcome.no_change
    session.refresh(pending)
    assert pending.geocoding_status == "failed"
    assert pending.place_candidate_id is None


def test_place_resolved_later_upgrades_to_ambiguous_not_verified(session: Session) -> None:
    """A place that gains coordinates without manual verification only reaches
    'ambiguous' — never auto-approval-eligible 'verified' status."""
    place = make_place(name="Slow Venue", verification_status=PlaceVerificationStatus.unverified)
    pending = make_pending(
        title="Late Bloomer", location_name="Slow Venue", place_candidate_id=place.id
    )
    session.add_all([place, pending])
    session.commit()

    first_pass = ReconciliationService(session).reconcile_pending_event(pending)
    assert first_pass == ReconciliationOutcome.skipped_unresolved_place

    # The same place row later gets resolved by a normal (non-manual) geocode.
    place.lat, place.lng = 37.9, 23.7
    session.add(place)
    session.commit()

    second_pass = ReconciliationService(session).reconcile_pending_event(pending)

    assert second_pass == ReconciliationOutcome.reconciled
    session.refresh(pending)
    assert pending.geocoding_status == "ambiguous"
    assert pending.status == "pending"


def test_manually_rejected_pending_event_not_overwritten(session: Session) -> None:
    place = make_place(
        name="Verified Spot",
        lat=37.9,
        lng=23.7,
        full_address="Main St",
        verification_status=PlaceVerificationStatus.manually_verified,
    )
    pending = make_pending(title="Rejected One", location_name="Verified Spot", status="rejected")
    session.add_all([place, pending])
    session.commit()

    outcome = ReconciliationService(session).reconcile_pending_event(pending)

    assert outcome == ReconciliationOutcome.skipped_protected
    session.refresh(pending)
    assert pending.status == "rejected"
    assert pending.geocoding_status == "failed"
    assert pending.place_candidate_id is None


def test_published_event_not_reapproved_or_duplicated(session: Session) -> None:
    place = make_place(
        name="Already Live Spot",
        lat=37.9,
        lng=23.7,
        full_address="Main St",
        verification_status=PlaceVerificationStatus.manually_verified,
    )
    pending = make_pending(
        title="Already Live", location_name="Already Live Spot", status="published"
    )
    session.add_all([place, pending])
    session.commit()

    outcome = ReconciliationService(session).reconcile_pending_event(pending)

    assert outcome == ReconciliationOutcome.skipped_protected
    assert session.exec(select(Event).where(Event.title == "Already Live")).first() is None


def test_skips_when_conflicting_live_event_already_exists(session: Session) -> None:
    place = make_place(
        name="Dual Spot",
        lat=37.9,
        lng=23.7,
        full_address="Main St",
        verification_status=PlaceVerificationStatus.manually_verified,
    )
    pending = make_pending(
        title="Dual Event",
        location_name="Dual Spot",
        place_candidate_id=place.id,
        geocoding_status="verified",
        confidence_score=1.0,
    )
    existing_live = Event(
        title="Dual Event",
        start_time=pending.start_time,
        location_name="Dual Spot",
        status=EventStatus.live,
        provenance=EventProvenance.aggregated,
    )
    session.add_all([place, pending, existing_live])
    session.commit()

    outcome = ReconciliationService(session).reconcile_pending_event(pending)

    assert outcome == ReconciliationOutcome.skipped_duplicate_risk
    session.refresh(pending)
    assert pending.status == "pending"
    live_rows = session.exec(select(Event).where(Event.title == "Dual Event")).all()
    assert len(live_rows) == 1


def test_reconcile_historical_dry_run_does_not_persist_changes(session: Session) -> None:
    resolved_place = make_place(
        name="Backfill Resolved",
        lat=37.9,
        lng=23.7,
        full_address="Main St",
        verification_status=PlaceVerificationStatus.manually_verified,
    )
    unresolved_place = make_place(
        name="Backfill Unresolved", verification_status=PlaceVerificationStatus.unverified
    )
    approvable = make_pending(title="Will Approve", location_name="Backfill Resolved")
    stays_pending = make_pending(
        title="Stays Pending",
        location_name="Backfill Unresolved",
        place_candidate_id=unresolved_place.id,
    )
    session.add_all([resolved_place, unresolved_place, approvable, stays_pending])
    session.commit()

    stats = ReconciliationService(session).reconcile_historical(dry_run=True)

    assert stats["scanned"] == 2
    assert stats[ReconciliationOutcome.reconciled_and_approved.value] == 1
    assert stats[ReconciliationOutcome.skipped_unresolved_place.value] == 1

    session.expire_all()
    refreshed_approvable = session.exec(
        select(PendingEvent).where(PendingEvent.title == "Will Approve")
    ).first()
    refreshed_pending = session.exec(
        select(PendingEvent).where(PendingEvent.title == "Stays Pending")
    ).first()
    assert refreshed_approvable is not None
    assert refreshed_approvable.status == "pending"
    assert refreshed_approvable.geocoding_status == "failed"
    assert refreshed_pending is not None
    assert refreshed_pending.status == "pending"
    assert session.exec(select(Event).where(Event.title == "Will Approve")).first() is None


def test_reconcile_historical_applies_changes_when_not_dry_run(session: Session) -> None:
    resolved_place = make_place(
        name="Live Backfill Resolved",
        lat=37.9,
        lng=23.7,
        full_address="Main St",
        verification_status=PlaceVerificationStatus.manually_verified,
    )
    unresolved_place = make_place(
        name="Live Backfill Unresolved", verification_status=PlaceVerificationStatus.unverified
    )
    approvable = make_pending(title="Real Approve", location_name="Live Backfill Resolved")
    stays_pending = make_pending(
        title="Real Stays Pending",
        location_name="Live Backfill Unresolved",
        place_candidate_id=unresolved_place.id,
    )
    session.add_all([resolved_place, unresolved_place, approvable, stays_pending])
    session.commit()

    stats = ReconciliationService(session).reconcile_historical()

    assert stats["scanned"] == 2
    assert stats[ReconciliationOutcome.reconciled_and_approved.value] == 1
    assert stats[ReconciliationOutcome.skipped_unresolved_place.value] == 1

    session.refresh(approvable)
    session.refresh(stays_pending)
    assert approvable.status == "published"
    assert stays_pending.status == "pending"
    assert session.exec(select(Event).where(Event.title == "Real Approve")).first() is not None
