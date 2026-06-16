# Ingestion Reconciliation (FOMO-163)

## Why this exists

Pending events are created by repeated, independent scrapes of the same
sources. A first pass at a venue often produces weak or failed geocoding
(`geocoding_status="failed"` or `"ambiguous"`, or no `place_candidate_id` at
all), and historically nothing ever revisited that `PendingEvent` once better
location data became available — either from a later scrape of the same
place, or from a moderator manually verifying the place in the dashboard.

`ReconciliationService`
(`apps/api/app/services/harvester/reconciliation_service.py`) closes that gap.
It re-checks a pending event against the current state of its linked `Place`,
upgrades only the fields that are objectively weaker than what is now known,
and re-runs the *same* `TrustEngine` / `ModerationService` auto-approval path
used by fresh ingestion. It is intentionally conservative: it never invents
new matching logic, never bypasses the FOMO-156 unresolved-place guard, and
never touches a pending event a moderator has already decided on.

## Same-event identity matching

Reconciliation does not introduce new deduplication. It only acts on the
`PendingEvent` row it is handed (by historical scan or by the place-update
hook below) and matches the *Place* using the existing
`PlaceRepository.get_by_name()` lookup (exact name match, then safe fuzzy
match within a city hint) — the same lookup ingestion already uses. Before
publishing, it additionally guards against creating a duplicate live `Event`
by checking for an existing `Event` with the same `(title, start_time,
location_name)` triple, which mirrors the table's existing identity key.

## Weak vs. protected fields

**May be upgraded** when a stronger value is available:
- `place_candidate_id` (when missing, or when a stronger resolved `Place` is
  found for the same location name)
- `geocoding_status` (`failed` → `ambiguous` → `verified`, never the reverse)
- `confidence_score`, `location`, `geocoding_metadata` (kept in lockstep with
  `geocoding_status` upgrades)
- Auto-approval eligibility (re-evaluated, not assumed)

**Never touched:**
- Any `PendingEvent` with `status in {"rejected", "published"}`
  (`PROTECTED_STATUSES` in `reconciliation_service.py`) — a moderator's
  decision is final.
- A `Place` already `manually_verified` with coordinates — reconciliation will
  never swap it for a different, weaker candidate.
- Anything when the only available candidate is an unresolved place (no
  `lat`/`lng`); a cache hit on an unresolved place is explicitly not treated
  as new evidence.

The same protection applies to *live re-ingestion*, not just historical
backfill: `ingestor.py` now checks whether an existing `PendingEvent` for the
same identity is `rejected` or `published` before touching it, so a repeated
scrape can never resurrect or duplicate a moderator's decision.

## Geocoding upgrade rules

Strength is ranked `failed (0) < ambiguous (1) < verified (2)`
(`_GEOCODING_STRENGTH`). An upgrade is only applied when the new status is
strictly stronger than the current one, and only when backed by a `Place`
row that actually has coordinates (`_is_resolved`). A `Place` becomes
`"verified"` strength only when `verification_status == "manually_verified"`;
otherwise a resolved-but-unverified place upgrades a pending event to
`"ambiguous"` at most. This preserves the FOMO-156 rule that auto-approval
must never happen for an event linked to an unresolved place, since
`_is_place_resolved()` (used as the gate before re-running `TrustEngine`)
returns `False` whenever the linked place still lacks coordinates.

## Auto-approval during reconciliation

`reconcile_pending_event()` always repairs weak data first
(`_upgrade_location()`), then re-runs eligibility from scratch — it never
trusts a stale `is_auto_approved` flag. Eligibility requires, in order:

1. The pending event is not protected (not already rejected/published).
2. The linked place is resolved (or there was never a place at all).
3. `TrustEngine.is_trusted_for_autopublish()` passes — the exact same gate
   (source, geocoding, future, distance) used by fresh ingestion, since
   `TrustEngine` is duck-typed against any object exposing `ingestion_method`,
   `geocoding_status`, `confidence_score`, `start_time`, `event_metadata`,
   `lat`, `lng`.
4. No conflicting live `Event` already exists for the same identity.

If eligible, publishing goes through `ModerationService.approve_events()` —
the same path the moderation dashboard uses — rather than a separate
"reconciliation publish" implementation.

Each outcome is logged and counted as one of:
- `no_change` — nothing to repair, nothing newly eligible.
- `reconciled` — location data was repaired but auto-approval still not met.
- `reconciled_and_approved` — repaired and published.
- `skipped_unresolved_place` — still no resolved place; stays pending.
- `skipped_protected` — moderator already decided; untouched.
- `skipped_duplicate_risk` — would-be publish collided with an existing live
  `Event`.

`dry_run=True` runs the full decision logic and returns the outcome that
*would* apply, then calls `self.db.rollback()` so no field changes or
approvals are persisted — useful for auditing a backfill before committing
to it.

## Place verification propagation

When a moderator edits a `Place` via `PlaceModerationService.update_place()`
(`apps/api/app/services/moderation/place_service.py`) and the place ends up
with coordinates, every `PendingEvent` synced to that place by name is
updated as before. If that sync sets `geocoding_status="verified"` (i.e. the
place is `manually_verified`), the affected pending event IDs are collected
and, once the place update commits, each `pending`-status candidate is run
through `ReconciliationService.reconcile_pending_event()`. This is what lets
"moderator verifies a place" immediately auto-approve any pending event that
was only waiting on that location.

## Historical backfill

`POST /api/v1/ingestion/reconcile-pending?batch_size=100&dry_run=false` (see
`apps/api/app/api/v1/ingestion.py`) runs `ReconciliationService.reconcile_historical()`
as a background task, mirroring the existing `/batch-geocode` endpoint
pattern. It pages through `PendingEvent` rows where `status="pending"` and
either `geocoding_status in ("failed", "ambiguous")` or
`place_candidate_id is None`, reconciling each one and returning aggregate
counts per outcome in the server log. It is idempotent and safe to re-run:
already-resolved or already-protected rows simply produce `no_change` /
`skipped_protected` on subsequent runs.

Run a dry run first to see what would happen before committing changes:

```
POST /api/v1/ingestion/reconcile-pending?batch_size=200&dry_run=true
```

Then run for real:

```
POST /api/v1/ingestion/reconcile-pending?batch_size=200&dry_run=false
```

## Validation queries

Pending events still stuck after a backfill pass (worth investigating
manually — usually means no matching `Place` has ever resolved):

```sql
SELECT id, title, location_name, geocoding_status, place_candidate_id
FROM pending_events
WHERE status = 'pending'
  AND (geocoding_status IN ('failed', 'ambiguous') OR place_candidate_id IS NULL)
ORDER BY created_at;
```

Pending events reconciliation should never have touched (sanity check —
should return zero rows where location data changed after rejection/publish):

```sql
SELECT id, title, status, geocoding_status, reviewed_at
FROM pending_events
WHERE status IN ('rejected', 'published')
  AND reviewed_at < updated_at;
```

Places that are `manually_verified` but still have pending events sitting on
`failed`/`ambiguous` geocoding for the same location name (candidates for a
manual `/reconcile-pending` run or indicates a name-matching gap):

```sql
SELECT p.id AS place_id, p.name, pe.id AS pending_id, pe.geocoding_status
FROM places p
JOIN pending_events pe ON pe.location_name = p.name
WHERE p.verification_status = 'manually_verified'
  AND pe.status = 'pending'
  AND pe.geocoding_status != 'verified';
```
