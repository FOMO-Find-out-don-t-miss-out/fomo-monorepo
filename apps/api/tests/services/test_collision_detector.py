"""DB-aware collision detection tests (FOMO-16): ingestion claiming/blocking
and the CollisionDetector candidate query itself. Reconciliation's use of the
same detector is covered by
apps/api/tests/services/test_reconciliation.py::test_skips_when_conflicting_live_event_already_exists.
"""

from datetime import UTC, datetime, timedelta

import pytest
from app.services.dedup.collision_detector import CollisionDetector, signature_from_pending
from app.services.harvester.ingestor import IngestionService
from sqlmodel import Session, select

from packages.domain.models import (
    DedupeStatus,
    Event,
    EventProvenance,
    EventStatus,
    PendingEvent,
    Place,
)
from packages.domain.schemas.extracted_event import ExtractedEvent
from packages.domain.services.event_collision_service import CollisionBucket

FUTURE = datetime.now(UTC) + timedelta(days=30)


def _extracted(**overrides: object) -> ExtractedEvent:
    defaults: dict[str, object] = dict(
        title="Test Show",
        start_time=FUTURE,
        category="Music",
        ingestion_method="json_ld",
    )
    defaults.update(overrides)
    return ExtractedEvent(**defaults)


@pytest.mark.asyncio
async def test_ingest_same_source_url_updates_existing_pending_not_a_duplicate(
    session: Session,
) -> None:
    """exact_source_match: re-scraping the same source URL must update the
    existing pending row, never create a second one — even if the title text
    changed slightly between scrapes."""
    first = _extracted(
        title="Old Title For Show",
        event_metadata={"original_link": "https://example.com/e/1"},
    )
    await IngestionService.ingest_events(session, [first])

    second = _extracted(
        title="New Title For Show",
        event_metadata={"original_link": "https://example.com/e/1"},
    )
    summary = await IngestionService.ingest_events(session, [second])

    assert summary.added == 0
    assert summary.updated == 1
    rows = session.exec(
        select(PendingEvent).where(PendingEvent.source_url == "https://example.com/e/1")
    ).all()
    assert len(rows) == 1
    assert rows[0].dedupe_status == DedupeStatus.duplicate_confirmed


@pytest.mark.asyncio
async def test_ingest_near_duplicate_title_same_place_time_links_into_one_pending_row(
    session: Session,
) -> None:
    """high_confidence_collision against another pending row: do not create a
    second, inconsistent pending row for what is clearly the same event."""
    first = _extracted(
        title="Pantera Release Athens 2026",
        location_name="Release Athens",
        lat=37.99,
        lng=23.73,
    )
    await IngestionService.ingest_events(session, [first])

    second = _extracted(
        title="Release Athens 2026 / Pantera",
        location_name="Release Athens",
        lat=37.99,
        lng=23.73,
    )
    summary = await IngestionService.ingest_events(session, [second])

    assert summary.added == 0
    assert summary.updated == 1
    rows = session.exec(
        select(PendingEvent).where(PendingEvent.location_name == "Release Athens")
    ).all()
    assert len(rows) == 1
    assert rows[0].dedupe_status == DedupeStatus.duplicate_confirmed
    # Title is never overwritten by collision claiming, even on the linked row.
    assert rows[0].title == "Pantera Release Athens 2026"


@pytest.mark.asyncio
async def test_ingest_blocks_duplicate_live_event_and_claims_safe_metadata(
    session: Session,
) -> None:
    """high_confidence_collision against a live Event: never create a second
    live row; claim only currently-missing safe metadata onto the existing one."""
    place = Place(name="Release Athens", country_code="GR", lat=37.99, lng=23.73, relevance=1.0)
    session.add(place)
    existing_live = Event(
        title="Pantera Release Athens 2026",
        start_time=FUTURE,
        location_name="Release Athens",
        place_id=place.id,
        status=EventStatus.live,
        provenance=EventProvenance.aggregated,
        ticket_url=None,
    )
    session.add(existing_live)
    session.commit()

    # Pre-cached, resolved venue match makes this candidate auto-approve-eligible
    # (same path exercised by test_internal_ingest_logic_venue_match) so the
    # claim-vs-create-duplicate branch actually runs.
    candidate = _extracted(
        title="Release Athens 2026 / Pantera",
        location_name="Release Athens",
        ticket_url="https://tickets.example.com/abc",
    )
    await IngestionService.ingest_events(session, [candidate])

    live_rows = session.exec(select(Event).where(Event.location_name == "Release Athens")).all()
    assert len(live_rows) == 1
    assert live_rows[0].title == "Pantera Release Athens 2026"  # untouched
    assert live_rows[0].ticket_url == "https://tickets.example.com/abc"  # safely claimed


@pytest.mark.asyncio
async def test_ingest_possible_collision_stays_pending_and_flagged(session: Session) -> None:
    """Strong place+time agreement but only partial title overlap: not
    confident enough to merge, but too suspicious to ignore — stays pending,
    flagged for moderator review, never silently merged or auto-approved."""
    first = _extracted(
        title="Open Air Jazz Night",
        location_name="Rooftop Athens",
        lat=37.98,
        lng=23.72,
        start_time=FUTURE,
    )
    await IngestionService.ingest_events(session, [first])

    second = _extracted(
        title="Jazz Late Night Session",
        location_name="Rooftop Athens",
        lat=37.98,
        lng=23.72,
        start_time=FUTURE,
    )
    summary = await IngestionService.ingest_events(session, [second])

    assert summary.added == 1
    pending = session.exec(
        select(PendingEvent).where(PendingEvent.title == "Jazz Late Night Session")
    ).first()
    assert pending is not None
    assert pending.dedupe_status == DedupeStatus.possible_match
    assert pending.status == "pending"


def test_collision_detector_assess_returns_no_match_for_unrelated_event(session: Session) -> None:
    pending = PendingEvent(
        title="Unrelated Event",
        start_time=FUTURE,
        location_name="Far Away Place",
        category="Other",
        status="pending",
        geocoding_status="failed",
    )
    session.add(pending)
    session.commit()

    signature = signature_from_pending(session, pending)
    # Exclude itself; an empty DB otherwise should yield no_collision.
    assessment = CollisionDetector(session).assess(signature, exclude_pending_id=pending.id)
    assert assessment.bucket is CollisionBucket.no_collision
    assert assessment.best_live_match is None
    assert assessment.best_pending_match is None
