# FOMO-156: Ingestion & Geocoding — Case Study

**Ticket:** FOMO-156  
**Area:** Ingestion pipeline, place resolution, auto-approval, dashboard, CI  
**Severity:** High — scraped events were silently dropped from moderation  

---

## 1. High-Level Summary

FOMO-156 started as a deceptively simple complaint: events scraped from external sources were not appearing in the moderation dashboard on staging.

The root cause was not a single bug but a chain of independent failures that each masked the next one:

- `location_name` was silently dropped in one ingestion path, so geocoding was never attempted.
- When geocoding was attempted, the Mapbox token was missing from the staging API pod, causing the geocoder to silently return `None`.
- No place candidate was created for failed geocoding — events were orphaned with no place link.
- The `places` table had non-nullable `lat`, `lng`, and `full_address` columns, blocking unresolved place creation entirely.
- Unresolved place cache hits could still set `geocoding_status = "verified"` and `confidence_score = 1.0`, making TrustEngine approve events with no valid location.
- The dashboard map iframe was receiving an `sk.*` token instead of the required public `pk.*` token, causing map rendering failures.
- Pydantic validation on `GeocodeResult.full_address` crashed when Mapbox returned a feature with no address, raising an exception caught only by the broad `except` in the cleanser — silently discarding the geocoding result.

The fix touched six layers: database schema, ingestion service, geocoder, repository, moderation schema, dashboard components, and CI quality gates.

---

## 2. Ingestion Flow

Understanding the two ingestion paths is essential for debugging future issues.

### Path A: `/api/v1/ingestion/ingest` (direct API call)

```
caller POST /ingest {events: [EventBase]}
  → router converts EventBase → ExtractedEvent
  → IngestionService.ingest_events(db, events)
  → for each event:
      - TrustEngine.is_junk() filter
      - venue cache lookup (SELECT Place WHERE name = location_name)
      - if cache hit: copy coords, mark verified
      - if cache miss + no coords: GeocoderService.get_coordinates()
          → Mapbox Search Box → Mapbox Geocode V6
          → GeocodingPolicy.determine_status()
          → if result: save to Place cache
          → if no result: save_unresolved_place()
      - if coords present (scraper-provided): upgrade status from "failed" to "ambiguous"
      - TrustEngine.is_trusted_for_autopublish()
      - defense-in-depth guard: unresolved place → force pending
      - INSERT PendingEvent (status=pending or published)
      - if auto-approved: INSERT Event (live)
```

### Path B: `/api/v1/ingestion/run-scraper` (n8n webhook)

```
n8n POST /run-scraper {url, source_provider, ...}
  → ScraperRegistry.run(url)
      → fetch raw HTML/JSON-LD
      → CleansingService.clean_json_ld() or .clean_html_fallback()
          → JsonLdExtractor or AiExtractor
          → EventClassifier (category, tags)
          → GeocoderService.get_coordinates()  ← runs here, before ingest
  → list[ExtractedEvent] with lat/lng already populated (or not)
  → IngestionService.ingest_events()
      → venue cache lookup (using already-geocoded coords)
      → same guard logic as Path A
```

Key difference: Path B runs geocoding inside the cleanser **before** reaching `IngestionService`, so when the event arrives at ingest it may already have coordinates. The `ingestor.py` still runs its own venue cache lookup and auto-approval logic regardless.

### Data tables involved

| Table | Role |
|---|---|
| `pending_events` | Holds harvested events awaiting moderation |
| `events` | Live events visible to end users |
| `places` | Venue/location cache; can be resolved (has coords) or unresolved |

`pending_events.place_candidate_id` → FK to `places.id`. Used by the dashboard to link events to their venue node.

---

## 3. Root Causes

### RC-1: `location_name` dropped in direct ingest path

**File:** `apps/api/app/api/v1/ingestion.py` (router)  
**Symptom:** Events posted to `/ingest` landed with `location_name = NULL` even when provided.  
**Cause:** The `EventBase → ExtractedEvent` conversion at the router layer did not forward the `location_name` field. Geocoding was never attempted. Events had `geocoding_status = "failed"` by default (the column default) even though they were never geocoded.

### RC-2: `geocoding_status = "failed"` conflates "not attempted" with "failed"

The `pending_events.geocoding_status` column defaults to `"failed"`. This means:
- An event that was never geocoded looks the same as one that was geocoded and genuinely failed.
- Batch geocoding jobs that filter on `geocoding_status = "failed"` will pick up both groups, but events with no `location_name` cannot be geocoded and are silently skipped.

**Partial fix:** When a scraper provides coordinates directly (bypassing geocoding), we now upgrade `geocoding_status` from `"failed"` to `"ambiguous"` — but only if no upstream component has already set a meaningful status (e.g. `"verified"` from `CleansingService`).

### RC-3: `MAPBOX_ACCESS_TOKEN` missing in staging

**File:** `apps/api/app/services/harvester/location/geocoder.py`  
**Symptom:** Geocoder silently returned `None` for all location names.  
**Cause:** The Mapbox token was not present in the staging API pod environment. The original code returned `None` without logging. We added a `logger.warning` when the token is missing so this failure is visible in logs.

**Platform action required:** `MAPBOX_ACCESS_TOKEN` must be injected from a Kubernetes Secret into the fomo-api Deployment.

### RC-4: No place candidate created on geocoding failure

**File:** `apps/api/app/services/harvester/ingestor.py`  
**Symptom:** Events with `location_name` but no geocoding result had `place_candidate_id = NULL`.  
**Cause:** The original code only created a `Place` record when geocoding succeeded. A failed geocode left no trace. Moderators could not see which events were associated with which venue.

**Fix:** When geocoding returns no result, create (or reuse) an **unresolved place** via `PlaceRepository.save_unresolved_place()`. Link it to `pending_events.place_candidate_id`. The unresolved place has `lat = NULL`, `lng = NULL`, `full_address = NULL`, `match_confidence = 0.0`, `verification_status = "unverified"`.

### RC-5: `places.lat/lng/full_address` were NOT NULL

**File:** `packages/domain/models/place.py`  
**Symptom:** `save_unresolved_place()` failed with a DB constraint error.  
**Cause:** The `lat`, `lng`, and `full_address` columns in `places` had `NOT NULL` constraints. Unresolved place candidates by definition lack coordinates.

**Fix:** Made those three columns nullable via Alembic migration `1b2c3d4e5f6a`.

### RC-6: Unresolved cache hits could trigger auto-approval

**File:** `apps/api/app/services/harvester/ingestor.py`  
**Symptom:** A subsequent scrape of the same venue (after an unresolved place had been created) found the place via the cache lookup and set `geocoding_status = "verified"` and `confidence_score = 1.0` unconditionally — regardless of whether the place had coordinates.

**Cause:** The venue cache lookup branch did not distinguish between resolved and unresolved cache hits. TrustEngine Gate #2 (`geocoding_status == "verified" and confidence_score >= 0.9`) then passed, and Gate #4 (distance check) was skipped because `lat/lng = None` made the haversine calculation impossible. Result: a json_ld event with a future date and an unresolved venue cache hit would be auto-published as a live event with no location.

### RC-7: Dashboard map received `sk.*` token

**Files:** `apps/harvester-dashboard/components/dashboard/event-inspector.tsx`, `venue-inspector.tsx`  
**Symptom:** Browser console showed `Use a public access token (pk.*) with Mapbox GL`.  
**Cause:** The Jenkins credential used for `NEXT_PUBLIC_MAPBOX_TOKEN` had been set to the server-side `sk.*` token. The dashboard code only checked truthiness (`if token`), not token type.

### RC-8: `GeocodeResult.full_address` validation crash

**File:** `apps/api/app/services/harvester/location/geocoder.py`  
**Symptom:** `[CLEANSER] Geocoding failed ... 1 validation error for GeocodeResult` in logs even for HTTP 200 Mapbox responses.  
**Cause:** After making `places.full_address` nullable (RC-5 fix), the geocoder's internal cache lookup could return a `Place` with `full_address = None`. The `GeocodeResult` model declared `full_address: str` (required, non-nullable), so Pydantic raised a `ValidationError`. This was caught by the broad `except Exception` in `CleansingService._enrich_geocoding`, silently discarding the geocoding result.

---

## 4. Final Target Behavior

After FOMO-156, the intended behavior at each stage is:

| Situation | Expected outcome |
|---|---|
| `location_name` provided, geocoding succeeds | Resolved `Place` created/updated. `pending_events.place_candidate_id` set. Event eligible for auto-approval if trust rules pass. |
| `location_name` provided, geocoding fails | Unresolved `Place` created (no coords). `place_candidate_id` set. Event stays `pending`. Never auto-approved. |
| `location_name` provided, coords already in payload | Status upgraded to `"ambiguous"` (not "failed"). Saved to `Place` cache if coords are valid. |
| No `location_name` | `place_candidate_id = NULL`. Event stays `pending`. |
| Venue cache hit — resolved place | Coordinates copied from cache. `geocoding_status = "verified"`, `confidence_score = 1.0`. Auto-approval eligible. |
| Venue cache hit — unresolved place | Place linked for moderation. `geocoding_status` unchanged (stays `"failed"`). Auto-approval **blocked**. |
| Dashboard — valid `pk.*` token + coordinates | Map iframe renders. |
| Dashboard — missing or `sk.*` token | Fallback UI with message: "Map is unavailable because the Mapbox public token is not configured correctly." |
| Dashboard — unresolved venue (no coords) | Fallback UI with message: "Location not yet resolved — geocoding pending." |

Historical rows (events ingested before the fix) may have `place_candidate_id = NULL` even when `location_name` is set. A reconciliation task should be run separately.

---

## 5. Implementation Changes

### 5.1 `packages/domain/models/place.py`

Made `lat`, `lng`, and `full_address` nullable:

```python
lat: float | None = Field(default=None)
lng: float | None = Field(default=None)
full_address: str | None = Field(default=None)
```

`match_confidence` remained NOT NULL — unresolved places use `0.0`.

### 5.2 Alembic migration `1b2c3d4e5f6a`

Located at `apps/api/migrations/versions/1b2c3d4e5f6a_make_places_coords_nullable.py`.

```python
def upgrade() -> None:
    op.alter_column("places", "lat",          existing_type=sa.Float(), nullable=True)
    op.alter_column("places", "lng",          existing_type=sa.Float(), nullable=True)
    op.alter_column("places", "full_address", existing_type=sa.String(), nullable=True)

def downgrade() -> None:
    # Removes rows with NULL coords before re-adding constraint
    op.execute("DELETE FROM places WHERE lat IS NULL OR lng IS NULL OR full_address IS NULL")
    op.alter_column("places", "lat",          nullable=False)
    op.alter_column("places", "lng",          nullable=False)
    op.alter_column("places", "full_address", nullable=False)
```

Run via:
```bash
docker compose exec api alembic upgrade head
```

### 5.3 `apps/api/app/repositories/place_repository.py`

Added `save_unresolved_place()`:

```python
def save_unresolved_place(
    self,
    name: str,
    country_code: str,
    source_provider: str | None = None,
) -> Place:
```

Creates a `Place` with no coordinates and `verification_status = unverified`. Idempotent — returns the existing record if the name/country already exists. Never downgrades a resolved or manually-verified place.

Also changed `save_place(full_address: str)` signature to `save_place(full_address: str | None)` to handle Mapbox responses that return no address text.

### 5.4 `apps/api/app/services/harvester/ingestor.py`

Key logic changes in `IngestionService.ingest_events()`:

1. **Resolved vs unresolved cache hit:**
   ```python
   place_is_resolved = False
   if venue:
       place_candidate_id = venue.id
       if venue.lat is not None and venue.lng is not None:
           # copy coords, mark verified, set place_is_resolved = True
       else:
           # link place, log warning, leave place_is_resolved = False
   ```

2. **Unresolved place on geocoder failure:**
   ```python
   else:
       unresolved = PlaceRepository(db).save_unresolved_place(...)
       place_candidate_id = unresolved.id
   ```

3. **Scraper-provided coords status upgrade:**
   ```python
   if event_data.geocoding_status == "failed":
       event_data.geocoding_status = "ambiguous"
   ```

4. **Defense-in-depth auto-approval block:**
   ```python
   if is_auto_approved and place_candidate_id and not place_is_resolved:
       is_auto_approved = False
   ```

### 5.5 `apps/api/app/services/harvester/location/geocoder.py`

- Added `logger.warning` when `MAPBOX_ACCESS_TOKEN` is not set.
- Made `GeocodeResult.full_address: str | None = None` (was `str`, required).
- Cache lookup now skips unresolved places:
  ```python
  if cached and cached.lat is not None and cached.lng is not None:
      return GeocodeResult(...)
  ```
  Previously, an unresolved cached place would cause a `ValidationError` on `full_address = None`.

### 5.6 `apps/api/app/main.py`

Added log suppression for httpx request-level logs, which included full Mapbox URLs with `access_token`:

```python
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
```

### 5.7 Moderation schema — `apps/api/app/schemas/moderation.py`

`PlaceResponse` updated:

```python
class PlaceResponse(BaseModel):
    lat: float | None = None
    lng: float | None = None
    full_address: str | None = None
```

Previously these fields were required/non-optional. Generated OpenAPI artifact and TypeScript types were regenerated via `pnpm --filter @fomo/api-spec build`.

### 5.8 `apps/api/app/services/moderation/place_service.py`

Added null-guards for coordinates before constructing WKT and before batch-updating event locations:

```python
has_coords = target.lat is not None and target.lng is not None
if has_coords:
    ev.location = WKTElement(f"POINT({target.lng} {target.lat})", srid=4326)
```

### 5.9 Dashboard — `event-inspector.tsx` and `venue-inspector.tsx`

Token validation:

```tsx
const rawMapboxToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN
const mapboxToken = rawMapboxToken?.startsWith('pk.') ? rawMapboxToken : null
```

- `mapboxToken` is `null` when the env var is absent, empty, or begins with `sk.`.
- Map iframe is only rendered when `mapboxToken` is non-null.
- `event-inspector.tsx`: map always falls back if token is invalid (no coord check — uses Athens as default).
- `venue-inspector.tsx`: map falls back if token is invalid **or** if `editedVenue.lat / .lng` are null.

Input null-safety (venue form):
```tsx
value={editedVenue.full_address ?? ""}
value={editedVenue.lat ?? ""}
value={editedVenue.lng ?? ""}
```

Change handlers parse empty string back to `null`:
```tsx
onChange={(e) => setEditedVenue({ ...editedVenue, lat: e.target.value === '' ? null : parseFloat(e.target.value) })}
```

`batchUpdateLocation` is only called when `v.lat != null && v.lng != null`, because `LocationBatchUpdate.lat/lng` are required non-nullable fields.

---

## 6. Auto-Approval Guard

TrustEngine applies four gates in sequence. A place cache hit was bypassing all of them by setting `geocoding_status = "verified"` and `confidence_score = 1.0` unconditionally:

| Gate | Condition | What it was missing |
|---|---|---|
| Gate 1 | `ingestion_method == "json_ld"` | Passed for all structured-data events |
| Gate 2 | `geocoding_status in {"verified","ambiguous"} AND confidence_score >= 0.9` | Was passing because cache hit unconditionally set verified/1.0 |
| Gate 3 | `start_time > now()` | Passed for future events |
| Gate 4 | Distance ≤ bbox | Skipped because lat/lng were None — haversine returned None, guard fell through |

The fix has two layers:

**Primary:** Only set `geocoding_status = "verified"` and `confidence_score = 1.0` when the cached place has actual coordinates. Unresolved cache hits leave the status unchanged.

**Defense-in-depth:** After TrustEngine runs, explicitly block auto-approval if the linked place has no coordinates, regardless of what TrustEngine decided based on event fields alone:

```python
if is_auto_approved and place_candidate_id and not place_is_resolved:
    is_auto_approved = False
    logger.info("[INGEST] Auto-Approve skipped: unresolved place candidate")
```

This ensures that even if future changes to TrustEngine accidentally re-introduce a bypass, the guard prevents unresolved places from producing live events.

---

## 7. Mapbox Token Separation

Two distinct Mapbox tokens are required. Mixing them causes failures that are not obvious from error messages alone.

| Token | Variable | Scope | Format | Where set |
|---|---|---|---|---|
| Backend geocoding | `MAPBOX_ACCESS_TOKEN` | API server only — never exposed to browser | `sk.*` or restricted `pk.*` | Kubernetes Secret → fomo-api Deployment env |
| Dashboard map rendering | `NEXT_PUBLIC_MAPBOX_TOKEN` | Baked into Next.js client bundle at build time | Public `pk.*` only | Jenkins credential `mapbox-public-token-staging` → `--build-arg` |

**Why they must be separate:**

- `sk.*` tokens are secret. If used as `NEXT_PUBLIC_MAPBOX_TOKEN`, they are embedded in the JS bundle and visible to any browser. Mapbox itself rejects `sk.*` tokens for browser requests with a clear error.
- `NEXT_PUBLIC_*` env vars in Next.js are baked at **build time**, not runtime. Injecting them at container startup has no effect. They must be passed as Docker `--build-arg` during `next build`.

**Dashboard enforcement:**

```tsx
const rawMapboxToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN
const mapboxToken = rawMapboxToken?.startsWith('pk.') ? rawMapboxToken : null
```

If the token is missing, empty, or starts with `sk.`, `mapboxToken` is `null` and the map iframe is not rendered. The token is never logged or printed to the DOM.

**API log suppression:**

httpx logs every outbound request URL at INFO level, which includes the `access_token` query parameter appended by the Mapbox client. Setting `httpx` and `httpcore` loggers to WARNING prevents this.

---

## 8. CI Lessons

### 8.1 Ruff import ordering (I001)

After adding new test functions, ruff's import-order check (`I001`) failed because local imports inside test function bodies were in the wrong order. Fix: run `uv run ruff check --fix` after writing test code and before committing.

### 8.2 Generated API artifact drift

The `verify-schema-sync` CI gate checks that `packages/api-spec/openapi.json` and the generated TypeScript type files match the live FastAPI schema. Any change to Pydantic schemas (`PlaceResponse`, `GeocodeResult`, etc.) must be followed by:

```bash
pnpm --filter @fomo/api-spec build
```

This regenerates:
- `packages/api-spec/openapi.json`
- `apps/harvester-dashboard/types/api.generated.ts`
- `apps/mobile/...` generated types (if applicable)

Failing to do this causes `verify-schema-sync` to fail even if the Python tests pass.

### 8.3 Dashboard typecheck after nullable backend changes

After `PlaceResponse.lat/lng/full_address` became nullable, the generated TypeScript type changed from `number` to `number | null | undefined`. This immediately caused TypeScript errors in:

- Input `value` props (HTML inputs do not accept `null`)
- `batchUpdateLocation` calls (required non-null `lat: number`)
- Test fixtures (fields that do not exist on the schema type)

**Cascade checklist for any backend schema change that makes a field nullable:**

1. Update Python model (`packages/domain/models/`)
2. Update Pydantic response schema (`apps/api/app/schemas/`)
3. Generate Alembic migration if it's a DB column
4. Run `pnpm --filter @fomo/api-spec build` to regenerate OpenAPI + TypeScript types
5. Check dashboard components that use the changed field — add null coalescing (`?? ""`, `?? 0`) for input values
6. Check dashboard API calls that pass the field to endpoints expecting non-nullable types
7. Run `pnpm --filter @fomo/harvester-dashboard run check-quality` (lint + typecheck + test)

---

## 9. Verification Checklist

After deploying a fix for ingestion/geocoding/place issues, run the following checks.

### Token security

```bash
# In the running dashboard container — no sk.* token should be in any JS bundle
grep -R "sk\.eyJ" /app/.next 2>/dev/null | wc -l  # must be 0
```

### API log safety

Inspect API logs after a scraper run. These patterns must not appear:
- `access_token=sk.`
- `access_token=pk.`
- `sk.eyJ`
- `pk.eyJ`

### Database invariants

After a fresh ingestion run, verify in PostgreSQL:

```sql
-- No live event linked to an unresolved place
SELECT COUNT(*)
FROM events e
JOIN places p ON e.place_id = p.id
WHERE p.lat IS NULL OR p.lng IS NULL;
-- Expected: 0

-- Pending events with location_name must have place_candidate_id
SELECT COUNT(*)
FROM pending_events
WHERE location_name IS NOT NULL
  AND place_candidate_id IS NULL;
-- Expected: 0 for newly ingested events
-- (Historical rows from before the fix may still show non-zero here)

-- Places table: unresolved entries should have no coordinates
SELECT COUNT(*)
FROM places
WHERE (lat IS NULL OR lng IS NULL)
  AND verification_status != 'unverified';
-- Expected: 0
```

### Dashboard map

| Scenario | Expected UI |
|---|---|
| Resolved venue, valid `pk.*` token | Map iframe visible |
| Resolved venue, no token or `sk.*` token | "Map is unavailable..." fallback |
| Unresolved venue (null coords), valid `pk.*` token | "Location not yet resolved..." fallback |

---

## 10. Follow-Up Tasks

### 10.1 Historical row reconciliation

Events ingested before this fix may have `place_candidate_id = NULL` even when they have a `location_name`. A batch script or migration should:

1. For each `pending_event` where `location_name IS NOT NULL AND place_candidate_id IS NULL`:
   - Look up the place by name.
   - If found, set `place_candidate_id`.
   - If not found, create an unresolved place and set `place_candidate_id`.

This should be run as a one-off script, not as part of normal migrations.

### 10.2 Alembic migration execution in deployment

The `1b2c3d4e5f6a` migration must be applied to staging and production databases before deploying API images that rely on nullable `lat/lng/full_address`. The current deployment flow (Jenkins + Helm) does not automatically run migrations. A pre-deploy hook or init container running `alembic upgrade head` is needed.

### 10.3 `geocoding_status` semantic cleanup

The default value `"failed"` for `pending_events.geocoding_status` conflates two states: "not attempted" and "genuinely failed". A future migration could add an explicit `"pending"` or `"not_attempted"` status to make batch geocoding logic more precise and avoid re-processing events that had no location name.

### 10.4 Batch geocoder for staging backfill

The existing `GeocoderService.batch_geocode_pending_events()` processes events with `geocoding_status = "failed"`. Once `MAPBOX_ACCESS_TOKEN` is wired in staging, triggering a batch run will geocode historical events that previously had no result.

### 10.5 Dashboard place editing UX

Currently, moderators can edit lat/lng directly as numeric inputs in the venue inspector. A future improvement would integrate a Mapbox search widget that populates coordinates from a confirmed place result, reducing manual entry errors.
