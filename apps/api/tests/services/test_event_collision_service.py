"""Tests for the pure event collision scorer (FOMO-16).

Lives under apps/api/tests (not packages/domain/tests) so it runs under the
project's default `testpaths = ["apps/api/tests"]` pytest configuration, even
though the service under test is in packages/domain.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from packages.domain.services.event_collision_service import (
    CollisionBucket,
    EventCollisionService,
    EventSignature,
    score,
)

START = datetime(2026, 7, 1, 21, 0, tzinfo=UTC)


def sig(**overrides: object) -> EventSignature:
    defaults: dict[str, object] = dict(
        title="Pantera Release Athens 2026",
        start_time=START,
        location_name="Release Athens",
        lat=37.99,
        lng=23.73,
        place_is_resolved=True,
    )
    defaults.update(overrides)
    return EventSignature(**defaults)


def test_same_source_url_is_exact_source_match() -> None:
    a = sig(source_url="https://example.com/event/1", title="Different Title Entirely")
    b = sig(source_url="https://example.com/event/1", title="Other Title")
    assert score(a, b).bucket is CollisionBucket.exact_source_match


def test_slightly_different_title_same_place_time_is_high_confidence() -> None:
    a = sig(title="Pantera Release Athens 2026")
    b = sig(title="Release Athens 2026 / Pantera")
    result = score(a, b)
    assert result.bucket is CollisionBucket.high_confidence_collision


def test_same_title_different_place_is_no_collision() -> None:
    a = sig(location_name="Release Athens", lat=37.99, lng=23.73)
    b = sig(location_name="Gazi Music Hall", lat=38.5, lng=24.5)
    assert score(a, b).bucket is CollisionBucket.no_collision


def test_same_place_and_day_but_different_title_and_time_is_no_collision() -> None:
    a = sig(title="Jazz Night", start_time=START)
    b = sig(title="Techno Rave", start_time=START + timedelta(hours=10))
    assert score(a, b).bucket is CollisionBucket.no_collision


def test_same_venue_multiple_events_same_day_does_not_over_merge() -> None:
    """Different shows at the same venue/day with distinct numeric identifiers
    must not be treated as the same event just because titles are similar."""
    a = sig(title="Show 1", start_time=START)
    b = sig(title="Show 2", start_time=START)
    result = score(a, b)
    assert result.bucket is not CollisionBucket.high_confidence_collision


def test_unresolved_place_does_not_reach_high_confidence_alone() -> None:
    a = sig(
        title="Pantera Release Athens 2026",
        location_name="Release Athens",
        lat=None,
        lng=None,
        place_is_resolved=False,
    )
    b = sig(
        title="Release Athens 2026 / Pantera",
        location_name="Release Athens",
        lat=None,
        lng=None,
        place_is_resolved=False,
    )
    result = score(a, b)
    assert result.bucket is not CollisionBucket.high_confidence_collision


def test_unresolved_place_still_reaches_high_confidence_with_strong_place_id() -> None:
    place_id = uuid4()
    a = sig(
        title="Pantera Release Athens 2026",
        place_id=place_id,
        lat=None,
        lng=None,
        place_is_resolved=False,
    )
    b = sig(
        title="Release Athens 2026 / Pantera",
        place_id=place_id,
        lat=None,
        lng=None,
        place_is_resolved=False,
    )
    assert score(a, b).bucket is CollisionBucket.high_confidence_collision


def test_title_only_match_without_place_or_time_is_no_collision() -> None:
    a = sig(title="Pantera Release Athens 2026", location_name=None, lat=None, lng=None)
    b = sig(title="Pantera Release Athens 2026", location_name=None, lat=None, lng=None)
    assert score(a, b).bucket is CollisionBucket.no_collision


def test_best_match_prefers_higher_ranked_bucket_over_raw_score() -> None:
    candidate = sig(source_url="https://example.com/event/9", title="Anything")
    exact_id = uuid4()
    possible_id = uuid4()
    candidates = [
        (possible_id, sig(title="Loosely Similar Title", source_url=None)),
        (exact_id, sig(source_url="https://example.com/event/9", title="Wildly Different")),
    ]
    best = EventCollisionService.best_match(candidate, candidates)
    assert best is not None
    assert best[0] == exact_id
    assert best[1].bucket is CollisionBucket.exact_source_match


def test_best_match_returns_none_when_no_candidate_collides() -> None:
    candidate = sig(location_name="Somewhere Else", lat=10.0, lng=10.0, title="Unrelated")
    candidates = [(uuid4(), sig(location_name="Release Athens", lat=37.99, lng=23.73))]
    assert EventCollisionService.best_match(candidate, candidates) is None
