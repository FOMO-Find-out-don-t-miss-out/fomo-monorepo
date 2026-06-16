"""Conservative event collision/duplicate detection.

Pure scoring logic with no DB dependency, mirroring the style of
packages/domain/services/trust_engine.py. Title similarity alone is never
sufficient: a collision requires agreement on *place* and *time* signals,
with title similarity only refining the confidence bucket. See
docs/ingestion/event-deduplication-collision-detection.md for the full
rationale and worked examples.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from enum import StrEnum
from uuid import UUID

# Same-day events starting within this window are considered "time-equal".
TIME_EXACT_WINDOW = timedelta(minutes=30)
# Events starting within this window are still "time-close" (weaker signal).
TIME_CLOSE_WINDOW = timedelta(hours=3)
# Coordinates within this radius are treated as "the same place".
PLACE_COORD_EXACT_METERS = 75.0
# Coordinates within this radius are "nearby" (weaker signal).
PLACE_COORD_NEAR_METERS = 400.0

# Minimum sub-scores required before a candidate counts as a collision at all.
MIN_PLACE_SCORE_FOR_ANY_MATCH = 0.55
MIN_TIME_SCORE_FOR_ANY_MATCH = 0.5
MIN_TITLE_SCORE_FOR_ANY_MATCH = 0.3

# Thresholds for the high_confidence bucket (all three must be met).
HIGH_CONFIDENCE_PLACE_SCORE = 0.85
HIGH_CONFIDENCE_TIME_SCORE = 0.85
HIGH_CONFIDENCE_TITLE_SCORE = 0.45


class CollisionBucket(StrEnum):
    exact_source_match = "exact_source_match"
    high_confidence_collision = "high_confidence_collision"
    possible_collision = "possible_collision"
    no_collision = "no_collision"


@dataclass(frozen=True)
class EventSignature:
    """Plain, DB-agnostic representation of an event used for collision scoring.

    Built by the caller from an Event, PendingEvent, or ExtractedEvent so this
    module never needs to know about ORM rows or SQLModel sessions.
    """

    title: str
    start_time: datetime | None
    location_name: str | None = None
    place_id: UUID | None = None
    lat: float | None = None
    lng: float | None = None
    place_is_resolved: bool = False
    source_provider: str | None = None
    source_url: str | None = None
    end_time: datetime | None = None


@dataclass(frozen=True)
class CollisionScore:
    bucket: CollisionBucket
    title_score: float
    time_score: float
    place_score: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


_TITLE_PUNCTUATION = re.compile(r"[^\w\s]")


def _title_tokens(title: str) -> set[str]:
    cleaned = _TITLE_PUNCTUATION.sub(" ", title.lower())
    return set(cleaned.split())


def _title_score(a: str, b: str) -> float:
    """Word-set (Jaccard) similarity, not character similarity.

    Deliberately not a char-level diff: "Show 1" vs "Show 2" must score low
    (different identifiers) while "Pantera Release Athens 2026" vs "Release
    Athens 2026 / Pantera" (same words, reordered/re-punctuated) must score
    high. Character-level ratios conflate these two very different cases.
    """
    if not a or not b:
        return 0.0
    if a.strip().lower() == b.strip().lower():
        return 1.0
    tokens_a, tokens_b = _title_tokens(a), _title_tokens(b)
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_m = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius_m * math.asin(math.sqrt(a))


def _to_naive_utc(dt: datetime) -> datetime:
    """Strips tzinfo (after UTC conversion) so naive/aware datetimes from
    different storage layers (e.g. SQLite drops tzinfo) can be compared."""
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _time_score(a: EventSignature, b: EventSignature) -> tuple[float, str | None]:
    if a.start_time is None or b.start_time is None:
        return 0.0, None
    delta = abs((_to_naive_utc(a.start_time) - _to_naive_utc(b.start_time)).total_seconds())
    if delta <= TIME_EXACT_WINDOW.total_seconds():
        return 1.0, "start_time_within_30m"
    if delta <= TIME_CLOSE_WINDOW.total_seconds():
        # Linear decay from 1.0 at the exact-window edge to 0.4 at the close-window edge.
        span = TIME_CLOSE_WINDOW.total_seconds() - TIME_EXACT_WINDOW.total_seconds()
        progress = (delta - TIME_EXACT_WINDOW.total_seconds()) / span
        return max(0.4, 1.0 - 0.6 * progress), "start_time_within_3h"
    if _to_naive_utc(a.start_time).date() == _to_naive_utc(b.start_time).date():
        return 0.3, "same_calendar_date"
    return 0.0, None


def _place_score(a: EventSignature, b: EventSignature) -> tuple[float, str | None]:
    if a.place_id is not None and b.place_id is not None and a.place_id == b.place_id:
        return 1.0, "same_place_id"

    a_name = (a.location_name or "").strip().lower()
    b_name = (b.location_name or "").strip().lower()
    if a_name and b_name and a_name == b_name:
        return 0.9, "exact_location_name_match"

    if a.lat is not None and a.lng is not None and b.lat is not None and b.lng is not None:
        distance = _haversine_meters(a.lat, a.lng, b.lat, b.lng)
        if distance <= PLACE_COORD_EXACT_METERS:
            return 0.95, "coordinates_within_75m"
        if distance <= PLACE_COORD_NEAR_METERS:
            return 0.6, "coordinates_within_400m"

    if a_name and b_name:
        name_ratio = SequenceMatcher(None, a_name, b_name).ratio()
        if name_ratio > 0.9:
            return 0.7, "fuzzy_location_name_match"

    return 0.0, None


def score(candidate: EventSignature, existing: EventSignature) -> CollisionScore:
    """Score `candidate` against a single `existing` event/pending event."""

    if (
        candidate.source_url
        and existing.source_url
        and candidate.source_url == existing.source_url
    ):
        return CollisionScore(
            bucket=CollisionBucket.exact_source_match,
            title_score=1.0,
            time_score=1.0,
            place_score=1.0,
            reasons=("same_source_url",),
        )
    if (
        candidate.source_provider
        and existing.source_provider
        and candidate.source_provider == existing.source_provider
        and candidate.title.strip().lower() == existing.title.strip().lower()
        and candidate.start_time is not None
        and existing.start_time is not None
        and _to_naive_utc(candidate.start_time) == _to_naive_utc(existing.start_time)
    ):
        return CollisionScore(
            bucket=CollisionBucket.exact_source_match,
            title_score=1.0,
            time_score=1.0,
            place_score=1.0,
            reasons=("same_provider_title_and_start_time",),
        )

    title_score = _title_score(candidate.title, existing.title)
    time_score, time_reason = _time_score(candidate, existing)
    place_score, place_reason = _place_score(candidate, existing)

    reasons = [r for r in (time_reason, place_reason) if r]

    # Place+time must both clear a minimum bar; title alone never qualifies.
    if (
        place_score < MIN_PLACE_SCORE_FOR_ANY_MATCH
        or time_score < MIN_TIME_SCORE_FOR_ANY_MATCH
        or title_score < MIN_TITLE_SCORE_FOR_ANY_MATCH
    ):
        return CollisionScore(
            bucket=CollisionBucket.no_collision,
            title_score=title_score,
            time_score=time_score,
            place_score=place_score,
            reasons=tuple(reasons),
        )

    # An unresolved place (no coordinates, no place_id) is a weaker identity
    # signal -- never let it alone push a match into high_confidence.
    place_is_strong = existing.place_is_resolved or candidate.place_is_resolved or (
        candidate.place_id is not None and candidate.place_id == existing.place_id
    )

    if (
        place_score >= HIGH_CONFIDENCE_PLACE_SCORE
        and time_score >= HIGH_CONFIDENCE_TIME_SCORE
        and title_score >= HIGH_CONFIDENCE_TITLE_SCORE
        and place_is_strong
    ):
        reasons.append("title_similar_enough")
        return CollisionScore(
            bucket=CollisionBucket.high_confidence_collision,
            title_score=title_score,
            time_score=time_score,
            place_score=place_score,
            reasons=tuple(reasons),
        )

    reasons.append("below_high_confidence_threshold")
    return CollisionScore(
        bucket=CollisionBucket.possible_collision,
        title_score=title_score,
        time_score=time_score,
        place_score=place_score,
        reasons=tuple(reasons),
    )


class EventCollisionService:
    """Stateless façade kept for call-site readability and future extension."""

    @staticmethod
    def score(candidate: EventSignature, existing: EventSignature) -> CollisionScore:
        return score(candidate, existing)

    @staticmethod
    def best_match(
        candidate: EventSignature, existing_events: list[tuple[UUID, EventSignature]]
    ) -> tuple[UUID, CollisionScore] | None:
        """Score against many candidates, returning the single best match.

        Bucket ranking takes priority over raw score so an exact_source_match
        is never displaced by a higher-title-similarity possible_collision.
        """

        bucket_rank = {
            CollisionBucket.exact_source_match: 3,
            CollisionBucket.high_confidence_collision: 2,
            CollisionBucket.possible_collision: 1,
            CollisionBucket.no_collision: 0,
        }
        best: tuple[UUID, CollisionScore] | None = None
        for event_id, signature in existing_events:
            result = score(candidate, signature)
            if result.bucket is CollisionBucket.no_collision:
                continue
            if best is None or bucket_rank[result.bucket] > bucket_rank[best[1].bucket] or (
                bucket_rank[result.bucket] == bucket_rank[best[1].bucket]
                and (result.title_score + result.time_score + result.place_score)
                > (best[1].title_score + best[1].time_score + best[1].place_score)
            ):
                best = (event_id, result)
        return best
