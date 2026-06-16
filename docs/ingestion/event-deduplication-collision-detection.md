# Event Deduplication & Collision Detection (FOMO-16)

## Why this exists

Different scrapers and re-scrapes of the same source routinely produce
slightly different titles for what is clearly the same event ("Pantera
Release Athens 2026" vs. "Release Athens 2026 / Pantera"). The previous
duplicate check only matched on a byte-identical `(title, start_time,
location_name)` triple, so any title drift between scrapes silently created
a second, competing `PendingEvent` or — worse — a second live `Event`.

At the same time, a *too-loose* match is just as dangerous: two distinct
events at the same venue on the same day ("Show 1" vs. "Show 2") must never
be merged just because their titles are textually similar. Place and time
agreement matter more than title text.

This is a shared, DB-agnostic scoring service plus a thin DB-aware wrapper,
used today by ingestion and reconciliation, and intended to be reused by any
future user-submission endpoint.

## Product rule: end users never merge events

End users must never be asked to resolve a duplicate. If a future
user-submission flow detects `exact_source_match` or
`high_confidence_collision` against an existing event, the correct behavior
is to show the user the existing event instead of creating a new one — never
present a "is this the same event?" merge prompt. `possible_collision` is
moderator-only; a user-submission endpoint should still accept the
submission as a new pending row (so the user isn't blocked) and let
moderation review it, exactly like ingestion does. No such endpoint exists
yet; this document describes where one should call `CollisionDetector` when
it is built.

## Components

- `packages/domain/services/event_collision_service.py` — pure scoring
  engine. No DB session, no ORM types; takes plain `EventSignature` dataclass
  inputs and returns a `CollisionScore`. Mirrors the
  `packages/domain/services/trust_engine.py` style.
- `apps/api/app/services/dedup/collision_detector.py` — DB-aware wrapper.
  Builds `EventSignature`s from `Event`, `PendingEvent`, or a freshly-scraped
  `ExtractedEvent`, queries candidate rows within a ±3h window of the
  candidate's `start_time`, and delegates all scoring to
  `EventCollisionService`.
- Callers: `apps/api/app/services/harvester/ingestor.py` (fresh ingestion)
  and `apps/api/app/services/harvester/reconciliation_service.py`
  (`_has_conflicting_live_event`, historical backfill).

## Confidence buckets

| Bucket | Meaning | Action |
| --- | --- | --- |
| `exact_source_match` | Same `source_url`, or same `source_provider` + identical title + identical `start_time`. | Update/link the existing record. Not a duplicate; normal auto-approval flow continues. |
| `high_confidence_collision` | Strong agreement on place and time, with at least a minimally-related title. | Block creating a duplicate (live or pending). For ingestion: claim the source signal onto the existing event/pending row and backfill only currently-missing safe metadata. |
| `possible_collision` | Some signal, but not enough to safely auto-merge. | Keep as a pending row, flagged for moderator review. Never auto-approved, never silently merged. |
| `no_collision` | Insufficient signal on title, place, and time. | Normal creation — no special handling. |

## Scoring model

Three independent sub-scores feed the bucket decision
(`event_collision_service.score()`):

- **Title** — word-set (Jaccard) similarity after lowercasing and stripping
  punctuation: `|tokens_a ∩ tokens_b| / |tokens_a ∪ tokens_b|`. Deliberately
  *not* character-level similarity (`difflib.SequenceMatcher`): "Show 1" vs.
  "Show 2" scores ~0.83 under character similarity (false high-confidence
  merge) but only ~0.33 under word-set Jaccard, while "Pantera Release Athens
  2026" vs. "Release Athens 2026 / Pantera" scores ~1.0 either way (same
  words, different order/punctuation). Jaccard cleanly separates "reordered
  same words" from "same words plus a different trailing identifier."
- **Time** — 1.0 within 30 minutes, decaying linearly to 0.4 out to 3 hours,
  0.3 for same calendar day but outside that window, else 0.
- **Place** — 1.0 for the same `place_id`; 0.95 for coordinates within 75m;
  0.9 for an exact `location_name` match; 0.6 for coordinates within 400m;
  0.7 for a fuzzy `location_name` match (`SequenceMatcher` ratio > 0.9, same
  threshold already used in `place_repository.py`); else 0.

All three sub-scores must clear a minimum floor
(`MIN_TITLE_SCORE_FOR_ANY_MATCH=0.3`, `MIN_TIME_SCORE_FOR_ANY_MATCH=0.5`,
`MIN_PLACE_SCORE_FOR_ANY_MATCH=0.55`) before any collision is registered at
all — this is what keeps two unrelated events at the same venue on different
days/times, or the same title at a different place, at `no_collision`.

Above the floor, `high_confidence_collision` additionally requires both
place and time scores to be high (`>= 0.85`) and the title score to clear a
slightly higher bar (`>= 0.45`) — except when the only place signal
available is a shared `place_id` on an *unresolved* place (no coordinates
yet); a shared `place_id` is treated as a strong identity signal on its own,
so two scrapes of the same not-yet-geocoded venue can still collide at high
confidence rather than being silently blocked by the FOMO-156 guard. An
unresolved place with no shared `place_id` (only matching `location_name`
text) cannot reach `high_confidence_collision` — that requires an additional
strong identity signal. Anything above the floor but below the
high-confidence bar is `possible_collision`.

## Ingestion behavior

`ingestor.py` builds a candidate `EventSignature` from the incoming
`ExtractedEvent` and calls `CollisionDetector(db).assess(...)`, which checks
both pending and live rows in the same ±3h window:

- If the best match against another **pending** row is
  `exact_source_match` or `high_confidence_collision`, ingestion updates
  that existing `PendingEvent` in place instead of creating a second one
  (the existing title is preserved; only metadata fields are refreshed).
- If the best match against a **live** `Event` is `exact_source_match` or
  `high_confidence_collision`, ingestion never creates a second live event.
  Instead it claims only currently-`None` safe fields
  (`ticket_url`, `photo_url`, `description`, `end_time`) onto the existing
  row. `title`, `start_time`, `location`, `place_id`, `status`,
  `trust_level`, `provenance`, and `visibility` are never touched by
  claiming.
- If the bucket is `possible_collision` against either a pending or live
  row, auto-approval is disabled for this candidate and the row is left
  pending for moderator review — never silently merged, never promoted to
  live.
- `dedupe_status` (`not_checked` / `possible_match` / `duplicate_confirmed`)
  and `candidate_event_id` are persisted on the `PendingEvent` row from the
  assessment, and surfaced on `PendingEventResponse` so the moderation
  dashboard can filter pending events by dedupe status
  (`GET /api/v1/moderation/pending-events?dedupe_status=possible_match`).

This sits alongside, and never overrides, the existing FOMO-156 and FOMO-163
guards: an unresolved place still disables auto-approval regardless of the
collision bucket, and a `rejected`/`published` `PendingEvent` is still never
touched by a repeated scrape.

## Reconciliation behavior

`ReconciliationService._has_conflicting_live_event()` now also uses
`CollisionDetector` instead of the previous exact-triple lookup: any
non-`no_collision` match against a live event blocks auto-approval during
reconciliation, which is intentionally more conservative than ingestion (no
claiming happens here — reconciliation only decides whether it is safe to
publish, it doesn't mutate other rows).

## Logging

`collision_detector.log_assessment()` emits one structured, non-sensitive
log line per assessed candidate: candidate title, `source_provider`,
number of candidates checked, the resulting bucket, the sorted set of reason
codes that produced it (e.g. `same_place_id`, `start_time_within_30m`,
`title_similar_enough`), and the action taken (`create_new`,
`create_pending`, `link_to_existing`, `block_duplicate`,
`mark_possible_collision`, `skip_protected`). No raw event payloads, URLs
with credentials, or PII are logged.

## Tests

- `apps/api/tests/services/test_event_collision_service.py` — pure scoring:
  exact source match, near-duplicate title at the same place/time, same
  title at a different place, same place/day with a clearly different
  title/time, same-venue multiple-events-same-day non-over-merge, unresolved
  place with/without a shared `place_id`, title-only without place/time, and
  `best_match` ranking.
- `apps/api/tests/services/test_collision_detector.py` — DB-aware ingestion
  behavior: same source URL updates the existing pending row, a near-duplicate
  title at the same place/time links into one pending row instead of two, a
  high-confidence collision against a live event blocks a duplicate and
  claims safe metadata, a possible collision stays pending and flagged, and a
  baseline no-collision assessment against an empty/unrelated DB.
- `apps/api/tests/services/test_reconciliation.py` and
  `apps/api/tests/api/test_internal.py` — unchanged pre-existing suites,
  re-run to confirm the FOMO-156/FOMO-163 guards and prior ingestion
  behavior (including the "Show 1"/"Show 2" same-venue non-merge case) still
  hold with the new shared collision detector wired in.

## Follow-ups

- No user-submission endpoint exists yet. When one is built, it should call
  `CollisionDetector(db).assess(...)` with a signature built from the user's
  submission and follow the product rule above: on
  `exact_source_match`/`high_confidence_collision`, return the existing
  event to the user instead of creating a duplicate; on `possible_collision`,
  accept the submission as a new pending row for moderator review.
- There is no moderator merge UI for events (only for Places). If
  `possible_collision` volume becomes high enough to need a queue, that is a
  candidate for a future ticket — out of scope here.
