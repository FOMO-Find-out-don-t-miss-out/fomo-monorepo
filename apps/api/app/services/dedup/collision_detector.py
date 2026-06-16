"""DB-aware wrapper around the pure EventCollisionService scorer.

Builds EventSignature objects from ORM rows (Event / PendingEvent) or from a
freshly-extracted scrape (ExtractedEvent), queries a small time-windowed
candidate pool, and returns the best collision match per target type
(live events vs. pending events) so callers (ingestion, reconciliation) can
decide what action to take. See
docs/ingestion/event-deduplication-collision-detection.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlmodel import Session, select

from packages.domain.models import Event, PendingEvent, Place
from packages.domain.schemas.extracted_event import ExtractedEvent
from packages.domain.services.event_collision_service import (
    TIME_CLOSE_WINDOW,
    CollisionBucket,
    CollisionScore,
    EventCollisionService,
    EventSignature,
)

logger = logging.getLogger(__name__)

_BUCKET_RANK = {
    CollisionBucket.exact_source_match: 3,
    CollisionBucket.high_confidence_collision: 2,
    CollisionBucket.possible_collision: 1,
    CollisionBucket.no_collision: 0,
}


@dataclass(frozen=True)
class CollisionMatch:
    target_type: Literal["event", "pending_event"]
    target_id: UUID
    score: CollisionScore


@dataclass(frozen=True)
class CollisionAssessment:
    candidate_title: str
    candidates_checked: int
    best_live_match: CollisionMatch | None
    best_pending_match: CollisionMatch | None

    @property
    def bucket(self) -> CollisionBucket:
        matches = [m for m in (self.best_live_match, self.best_pending_match) if m is not None]
        if not matches:
            return CollisionBucket.no_collision
        return max((m.score.bucket for m in matches), key=lambda b: _BUCKET_RANK[b])


def _place_lat_lng(db: Session, place_id: UUID | None) -> tuple[float | None, float | None, bool]:
    if place_id is None:
        return None, None, False
    place = db.get(Place, place_id)
    if place is None:
        return None, None, False
    resolved = place.lat is not None and place.lng is not None
    return place.lat, place.lng, resolved


def signature_from_event(db: Session, event: Event) -> EventSignature:
    lat, lng, resolved = _place_lat_lng(db, event.place_id)
    return EventSignature(
        title=event.title,
        start_time=event.start_time,
        end_time=event.end_time,
        location_name=event.location_name,
        place_id=event.place_id,
        lat=lat,
        lng=lng,
        place_is_resolved=resolved,
        source_provider=event.source_provider,
        source_url=event.source_url,
    )


def signature_from_pending(db: Session, pending: PendingEvent) -> EventSignature:
    lat, lng, resolved = _place_lat_lng(db, pending.place_candidate_id)
    return EventSignature(
        title=pending.title,
        start_time=pending.start_time,
        end_time=pending.end_time,
        location_name=pending.location_name,
        place_id=pending.place_candidate_id,
        lat=lat,
        lng=lng,
        place_is_resolved=resolved,
        source_provider=pending.source_provider,
        source_url=pending.source_url,
    )


def signature_from_extracted(
    extracted: ExtractedEvent, *, place_id: UUID | None, place_is_resolved: bool
) -> EventSignature:
    metadata = extracted.event_metadata if isinstance(extracted.event_metadata, dict) else {}
    return EventSignature(
        title=extracted.title,
        start_time=extracted.start_time,
        end_time=extracted.end_time,
        location_name=extracted.location_name,
        place_id=place_id,
        lat=extracted.lat,
        lng=extracted.lng,
        place_is_resolved=place_is_resolved,
        source_provider=extracted.source_provider,
        source_url=metadata.get("original_link"),
    )


class CollisionDetector:
    """Finds the best existing live/pending event match for a candidate signature."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def assess(
        self,
        candidate: EventSignature,
        *,
        exclude_pending_id: UUID | None = None,
        exclude_live_id: UUID | None = None,
    ) -> CollisionAssessment:
        if candidate.start_time is None:
            return CollisionAssessment(
                candidate_title=candidate.title,
                candidates_checked=0,
                best_live_match=None,
                best_pending_match=None,
            )

        window_start = candidate.start_time - TIME_CLOSE_WINDOW
        window_end = candidate.start_time + TIME_CLOSE_WINDOW

        live_rows = self.db.exec(
            select(Event).where(
                Event.start_time >= window_start, Event.start_time <= window_end
            )
        ).all()
        if exclude_live_id is not None:
            live_rows = [e for e in live_rows if e.id != exclude_live_id]

        pending_rows = self.db.exec(
            select(PendingEvent).where(
                PendingEvent.start_time >= window_start, PendingEvent.start_time <= window_end
            )
        ).all()
        if exclude_pending_id is not None:
            pending_rows = [p for p in pending_rows if p.id != exclude_pending_id]

        live_signatures = [(e.id, signature_from_event(self.db, e)) for e in live_rows]
        pending_signatures = [(p.id, signature_from_pending(self.db, p)) for p in pending_rows]

        best_live = EventCollisionService.best_match(candidate, live_signatures)
        best_pending = EventCollisionService.best_match(candidate, pending_signatures)

        assessment = CollisionAssessment(
            candidate_title=candidate.title,
            candidates_checked=len(live_rows) + len(pending_rows),
            best_live_match=CollisionMatch("event", best_live[0], best_live[1])
            if best_live
            else None,
            best_pending_match=CollisionMatch("pending_event", best_pending[0], best_pending[1])
            if best_pending
            else None,
        )
        return assessment


def log_assessment(
    assessment: CollisionAssessment, *, source_provider: str | None, action: str
) -> None:
    """Structured, non-sensitive log line for collision decisions."""
    reasons: list[str] = []
    for match in (assessment.best_live_match, assessment.best_pending_match):
        if match:
            reasons.extend(match.score.reasons)
    logger.info(
        "[COLLISION] title=%r provider=%s candidates_checked=%d bucket=%s reasons=%s action=%s",
        assessment.candidate_title,
        source_provider,
        assessment.candidates_checked,
        assessment.bucket.value,
        sorted(set(reasons)),
        action,
    )
