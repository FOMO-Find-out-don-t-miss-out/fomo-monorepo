# Explore v1 — Event Search Contract (FOMO-172)

## 1. Status

**Final contract decision for FOMO-172 Explore v1.** This document is the
canonical, implementation-ready specification for `GET /api/v1/events/search`
and its mobile consumption. It supersedes the exploratory options considered
in the Phase 0 design pass with single, final decisions on every open point
raised there. **No production code, generated API artifact, or test file is
created or modified by this document** — it is documentation only.

## 2. Purpose

Define the exact, final request contract, validation rules, search/sort
semantics, response shape, database strategy, and mobile consumption pattern
for Explore v1 event search, so that Phase 1 (backend implementation) can
proceed against a fixed contract instead of an open design.

## 3. Product boundary

Per `docs/product/mobile-navigation-information-architecture.md` (canonical
navigation decision, §7–§8): Discover is ambient/serendipitous, Explore is
intentional. This contract implements **only** the Events entity search
described there as "Explore v1." It does not implement People, Places/Venues,
or Organizers as searchable entities, and does not implement a universal
grouped search. It does not touch `/events/discovery`, which keeps its exact
current behavior, request shape, and response shape unchanged.

## 4. Endpoint decision

**Final: add `GET /api/v1/events/search` as a new, separate route.
`GET /api/v1/events/discovery` (`apps/api/app/api/v1/events.py:24-48`) is
unchanged.**

Router ordering constraint (final): the static `/search` route **must** be
registered before the dynamic `/{event_id}` route
(`apps/api/app/api/v1/events.py:51-60`) in `apps/api/app/api/v1/events.py`.
FastAPI/Starlette resolves path routes in registration order within a router,
and `/{event_id}` is an unconstrained path parameter — if `/search` were
registered after it, a request to `/api/v1/events/search` would be captured
by `/{event_id}` first and fail UUID coercion instead of reaching the search
handler. The implementation must place the new route above
`get_event_detail` in the file.

## 5. Request contract

```
GET /api/v1/events/search
```

| Param | Type | Default | Constraints |
|---|---|---|---|
| `q` | `string \| null` | `null` | Raw max length 200. Normalization and minimum-length rule applied in code, not via `Query(min_length=...)` — see §10. |
| `category` | `list[EventCategory] \| null` | `null` | Repeated query param (e.g. `?category=Music&category=Art`). Must be exact backend `EventCategory` enum values — see §18. |
| `date_from` | `datetime \| null` | `null` | Timezone-aware. |
| `date_to` | `datetime \| null` | `null` | Timezone-aware. Must be later than `date_from` when both given. |
| `lat` | `float \| null` | `null` | `-90..90`. Must be supplied together with `lng`. |
| `lng` | `float \| null` | `null` | `-180..180`. Must be supplied together with `lat`. |
| `radius_km` | `float \| null` | `10.0` (only meaningful when `lat`/`lng` given) | `> 0`, `<= 200`. |
| `limit` | `int` | `20` | `>= 1`, `<= 50`. |
| `offset` | `int` | `0` | `>= 0`. |

**No `upcoming_only` parameter exists** — see §9. Explore always excludes
already-ended events; this is not a request-configurable option in v1.

### At-least-one-criterion rule (final)

A request satisfying none of the following is invalid:

- normalized `q` is not `None` (see §10 for normalization), **or**
- `category` is non-empty, **or**
- `date_from` or `date_to` is present, **or**
- `lat`/`lng` (as a pair) is present.

A request with none of these → **HTTP 422**. This is a deliberate contract
guarantee that Explore never runs an unbounded "return everything live and
public" query — every call must narrow by at least one real criterion.

## 6. Validation rules

- `q` longer than 200 raw characters → 422 (FastAPI `Query(max_length=200)`).
- `q`, after normalization (§10), non-`None` and shorter than 2 characters →
  422, raised explicitly in handler code (not via `Query(min_length=...)`,
  because whitespace stripping must happen **before** the length check —
  a `Query(min_length=2)` constraint would validate the raw string and could
  reject/accept based on un-stripped whitespace, which is the wrong point in
  the pipeline for this rule).
- `radius_km` supplied without both `lat` and `lng` → 422.
- Only one of `lat`/`lng` supplied → 422 (must be a pair).
- `date_to` present and not later than `date_from` when both are given → 422.
- Any `category` value outside the backend `EventCategory` enum → 422
  (free via Pydantic/FastAPI enum coercion on `list[EventCategory]`).
- No criterion present at all (§5) → 422.
- `limit`/`offset` out of their stated bounds → 422 (standard `Query` bounds).

## 7. Search fields

**Included** (final, matched against for the `q` predicate):
- Event title — `Event.title` (`packages/domain/models/event.py:66`, part of `EventBase`).
- Event venue name — `Event.location_name` (`event.py:107-110`).
- Organizer display name — `Organizer.display_name` (`packages/domain/models/organizer.py:21`), via a join on `Event.organizer_id` (`event.py:187`, already FK-indexed).

Also filterable (not part of the `q` text predicate, separate params):
category, date range, location + radius.

**Excluded from Explore v1** (final, not merely deferred without reason):
- Event description (`Event.description`, `event.py:67`) — explicitly excluded from `q` matching per this contract, regardless of future relevance-ranking work.
- People search, standalone Place/Venue search, standalone Organizer search, universal grouped search — all out of scope per the canonical navigation document's Explore v1 rollout (§8 of that document) and this task's explicit non-goals.

## 8. Visibility and lifecycle rules

Every result row must satisfy the same visibility contract already enforced
by `/events/discovery` and reused verbatim via the existing
`public_event_filters()` helper (`apps/api/app/api/v1/events.py:16-21`):

- `status == EventStatus.live`
- `visibility == EventVisibility.public`
- `removed_at IS NULL`

This is a reuse decision, not a new rule — `EventRelationshipService` applies
the identical three-condition filter independently
(`apps/api/app/services/event_relationship_service.py:20-27`, `104-110`),
confirming this is the system-wide "is this event visible to a normal
client" contract, not something invented for search.

## 9. Date semantics

- `date_from` is **inclusive**.
- `date_to` is **exclusive**.
- Event-overlap semantics (final): an event matches the date range when

  ```
  COALESCE(Event.end_time, Event.start_time) >= date_from
  AND
  Event.start_time < date_to
  ```

  This allows an event that started before `date_from` but is still ongoing
  (has not reached its effective end) to correctly match a "today" or "this
  weekend" range, rather than only matching on `start_time` alone.
- When both `date_from` and `date_to` are given, `date_to` must be strictly
  later than `date_from` (§6).
- All datetimes in the request and in stored data are timezone-aware —
  consistent with `CORE_RULES.md`'s "Store all timestamps as UTC" and with
  `Event.start_time`/`end_time` already being timezone-aware columns
  (`event.py:73-80`, `216-219`).

### Upcoming behavior (final — no request parameter)

Explore v1 has **no `upcoming_only` parameter.** It unconditionally excludes
events that have already ended:

```
COALESCE(Event.end_time, Event.start_time) >= now()
```

This is applied on every `/events/search` call regardless of other filters.
**This is a new rule relative to `/events/discovery`**, which has no time
filter of any kind today (confirmed by reading `events.py:24-48` — the
discovery query applies only the spatial predicate and
`public_event_filters()`). Explore is explicitly a "find something to
attend" surface, not a history browser, and this exclusion is not
configurable in v1.

## 10. Text-match semantics

Normalization pipeline (final, applied in handler code before any query is
built):

1. Strip leading and trailing whitespace from the raw `q` value.
2. If the stripped value is empty, treat it as `None` (i.e., no text
   predicate — the request falls back to whatever other criteria are
   present, per §5).
3. If the stripped value is not `None` and its length is less than 2
   characters, return **HTTP 422**.
4. The normalized value is matched, case-insensitively, against:
   - `Event.title`
   - `Event.location_name`
   - `Organizer.display_name` (via the join described in §7)
5. `Event.description` is never matched in Explore v1 (§7).
6. Matching is case-insensitive by design intent. The mechanism is an
   explicit `lower(column) LIKE lower(:q)`-style comparison rather than a
   bare `ILIKE` operator, so that case-folding does not silently depend on
   whatever collation the operator happens to use.
7. **Greek and Unicode case-folding correctness is not claimed here.**
   `docker-compose.yml` does not set an explicit `POSTGRES_INITDB_ARGS`,
   `LC_COLLATE`, or locale (confirmed — no such setting exists in the file),
   so the effective database collation is whatever the base Postgres image's
   `initdb` default resolves to, which was not inspected against a live
   instance in this task. **This must be verified against a real running
   PostgreSQL instance before this behavior is claimed correct** — see §22.
   No claim in this document should be read as asserting Greek/Unicode
   case-insensitive matching already works; it is a requirement to verify,
   not a confirmed fact.

Partial (substring) matching is used, consistent with the only existing
precedent for free-text filtering in this codebase:
`PlaceModerationService.get_places`'s `Place.name.ilike(f"%{search_query}%")`
(`apps/api/app/services/moderation/place_service.py:123-124`).

## 11. Deterministic ordering

**Final — two-tier ordering, not a recommendation algorithm.**

### When `q` is present (normalized, non-`None`)

A simple, deterministic match-priority `CASE` expression orders results by
*how* the query matched, before falling through to the secondary keys:

1. exact title match (`lower(title) = lower(:q)`)
2. title prefix match (`lower(title) LIKE lower(:q) || '%'`)
3. title substring match (`lower(title) LIKE '%' || lower(:q) || '%'`)
4. `location_name` match
5. `organizer.display_name` match

This is explicitly **basic search ordering** — a fixed, explainable priority
list, not a scored/weighted relevance algorithm and not machine-ranked. No
`ts_rank`, `pg_trgm` similarity score, or custom weighting is introduced.

Then, within each priority tier:
- `ST_Distance(location, point) ASC` — only when `lat`/`lng` were supplied.
- `start_time ASC`
- `id ASC` — final deterministic tie-breaker in all cases.

### Filter-only search (`q` is `None`)

- `ST_Distance(location, point) ASC` when `lat`/`lng` are supplied,
  **otherwise**
- `start_time ASC`
- `id ASC` — final deterministic tie-breaker.

`id` (the event's UUID primary key) is included as the last sort key in
every branch specifically so that `limit`/`offset` pagination never produces
duplicate or skipped rows across pages when multiple events tie on every
other key.

## 12. Pagination

**Final:**

- `limit` — default `20`, minimum `1`, maximum `50`.
- `offset` — default `0`, minimum `0`.
- `has_more` is determined by fetching `limit + 1` rows from the database
  and checking whether the extra row exists, then trimming it before
  serializing `results`. **No `total` count is added** — a separate
  `COUNT(*)` query against the same filter predicate would roughly double
  the query cost per search request for a value nothing in the current
  Explore UI requirements (`docs/product/mobile-navigation-information-architecture.md`)
  asks for.

No prior pagination convention exists elsewhere in this backend to be
consistent with — confirmed by inspection: `/events/discovery`
(`events.py:24-48`), `/me/events` and `/me/event-relationships`
(`apps/api/app/api/v1/me.py:60-96`), `/admin/users`
(`apps/api/app/api/v1/admin.py:65-104`), and `/moderation/pending-events` /
`/moderation/places` (`apps/api/app/api/v1/moderation.py:28-48`, `143-150`)
all return complete, unbounded lists today. `limit`/`offset` pagination for
Explore is new, not a reuse of an existing pattern.

## 13. Response contract

Each result item reuses `EventDiscoveryResponse`
(`packages/domain/schemas/event.py:9-31`) **unchanged** — every field an
Explore result card or the shared `EventDetails` sheet needs (`title`,
`startTime`, `endTime`, `locationName`, `lat`/`lng`, `category`, `hypeScore`,
`photoUrl`, `ticketUrl`, `sourceUrl`, `provenance`, `trust_level`, `place_id`,
`organizer_id`) already exists there. No event-specific schema is created for
search results.

A new wrapper schema carries pagination metadata only:

```json
{
  "results": "EventDiscoveryResponse[]",
  "limit": "number",
  "offset": "number",
  "has_more": "boolean"
}
```

Distance is not a response field, matching `/events/discovery`'s existing
contract — the mobile client computes it client-side from `lat`/`lng` using
the same `haversineKm`/`formatDistanceKm` utilities Discover already uses
(`apps/mobile/utils/geo.ts`, consumed in `apps/mobile/app/(tabs)/index.tsx:115-124`).

## 14. Database/indexing strategy

**Confirmed by direct inspection, not assumed:**

- No full-text search (`tsvector`/GIN) is configured anywhere in
  `packages/domain/models/` or `apps/api/migrations/versions/` — zero matches
  on search across the migration history.
- No `pg_trgm` extension or trigram index exists anywhere in the migrations.
- `PlaceModerationService.get_places` already uses plain `ILIKE` in
  production-facing (moderator/admin) code with no supporting trigram index
  (`place_service.py:123-124`) — this is the existing precedent for
  "plain substring matching is acceptable at current scale" in this
  codebase, not a new risk class introduced by Explore.
- Reusable indexes: `ix_events_status_visibility_start_time`
  (`event.py:241`) covers the `public_event_filters()` + date-range query
  path directly; `idx_events_location` (GiST,
  `apps/api/migrations/versions/ca8a542b4fd7_add_spatial_index_to_events.py`)
  is reused verbatim for the `ST_DWithin` radius filter, identical to
  `/events/discovery`'s existing pattern (`events.py:36-44`); `organizer_id`
  and individual `title`/`category`/`location_name` btree indexes already
  exist (`event.py:81-110`, `187`) but do not accelerate a leading-wildcard
  `LIKE`/`ILIKE` predicate — they remain useful for the exact-match
  `category` filter and the organizer join.
- **No new index is added in Phase 1.** Plain substring matching without a
  trigram index is the final decision for v1, chosen for consistency with
  existing precedent and because it requires no new Postgres-only test
  infrastructure (the backend test suite runs against SQLite with hand-mocked
  `ST_*` functions — `apps/api/tests/api/test_discovery.py:32-46` — and
  `pg_trgm`/`tsvector` have no SQLite equivalent to mock).
- **Future optimization trigger (not designed here, recorded as an open
  issue in §22):** if measured query latency at production scale later
  shows plain substring matching is too slow, the smallest additive change
  is `CREATE EXTENSION pg_trgm` plus a GIN trigram index on `title` and
  `location_name` — this does not require changing the endpoint contract
  defined in this document.
- No evidence in this repository justifies Elasticsearch, OpenSearch, or any
  external search platform for Explore v1.

## 15. Mobile request lifecycle

No `AbortController` exists anywhere in `apps/mobile/utils/api-client.ts`
(confirmed by inspection) and no debounce utility exists in
`apps/mobile/utils/` — the existing hooks (`use-discovery.ts`,
`use-event-relationships.ts`) both solve request supersession with a plain
`cancelled` closure-flag effect pattern. Explore's search hook must follow
the same pattern; no new state-management or data-fetching library is
introduced.

Final mobile behavior:

- Minimum normalized query length: **2** characters, mirroring the backend
  rule in §10 — below this, no request is fired at all.
- Debounce interval: **~350–400 ms** after the last keystroke/filter change.
- Stale-response protection: the same `cancelled`-flag pattern already used
  by `use-discovery.ts` and `use-event-relationships.ts` — a new request
  supersedes any in-flight one.
- No request fires for a completely empty, filter-less screen state — this
  mirrors the backend's at-least-one-criterion rule (§5) on the client side,
  so Explore never issues (and the backend never has to reject) a
  no-criteria call.
- Loading state distinguishes first-ever load (full loading state) from a
  subsequent search/filter change (previous results remain visible until the
  new results arrive) — same distinction already implemented for My Events
  (`isInitialLoading`, `apps/mobile/app/(tabs)/saved.tsx:271-272`).
- Result list is a virtualized `FlatList`, reusing the existing `EventCard`
  component (`apps/mobile/components/fomo/event-card.tsx`) unchanged.
- Tapping a result opens the existing shared `EventDetails` sheet
  (`apps/mobile/components/fomo/event-details.tsx`) unchanged.
- Loading/empty/error states reuse `FomoLoadingState`, `FomoEmptyState`,
  `FomoErrorState` (`apps/mobile/components/ui/`) unchanged.
- `/events/search` is public — no authentication is required, mirroring
  `/events/discovery`, which has no auth dependency today
  (`events.py:24-30`). Explore must work for unauthenticated users.
- Relationship (Interested/Going) overlays on results only render when an
  `accessToken` is present, identical to Discover's existing
  `accessToken ? selectedIntent : null` pattern (`apps/mobile/app/(tabs)/index.tsx:418-419`).

## 16. Explore UI boundary

- The user-facing tab label is **"Explore."**
- The internal route file **may remain `apps/mobile/app/(tabs)/search.tsx`**
  — this document does not require a route rename, consistent with the
  canonical navigation document's non-goal of renaming routes in a
  documentation/design phase.
- **No inactive entity-type tabs** — only Events exist as a searchable
  entity in v1 (per §3/§7); a tab row with three non-functional tabs
  (People/Places/Organizers) is explicitly disallowed.
- No request is made for an empty, filter-less screen state (§15).

## 17. Discover handoff

The Discover `SearchBar` (`apps/mobile/components/fomo/search-bar.tsx`)
becomes a **launcher into Explore**, not a second, independent text-search
system. Its own local controls remain Discover-owned:

- map/calendar presentation (`FomoMap`, `CalendarView`)
- local category/date/radius controls
- selected event state
- nearby carousel

The initial handoff payload is limited to serializable primitives — no
`Event` objects, no arrays of events, nothing non-serializable:

```ts
interface ExploreHandoffParams {
  q?: string;
  lat?: number;
  lng?: number;
  radiusKm?: number;
  category?: string;   // a single canonical backend EventCategory value
  // date context: not included until Discover has a real date-filter
  // state to hand off — Discover's Calendar view today is a presentation
  // mode, not a filter parameter (apps/mobile/components/fomo/calendar-view.tsx)
}
```

After the initial navigation, **Explore owns all subsequent search
behavior** — Discover does not continue to influence or re-trigger Explore's
state once the handoff completes. This design is specified here as the final
shape for the future handoff implementation; **implementing this navigation
is not part of this document** (see §21).

## 18. Category-taxonomy dependency

**Final: the backend `EventCategory` enum is the sole wire-contract source
of truth for the `category` parameter. No fourth category vocabulary is
introduced.**

Confirmed, existing mismatch between three vocabularies already present in
this repository (not created by this contract):

| Vocabulary | Values | Location |
|---|---|---|
| Backend `EventCategory` (wire contract) | `Music, Art, Tech, Food, Nightlife, Sports, Business, Community, Other` | `packages/domain/models/event.py:17-26` |
| Mobile `UiEventCategory` (display buckets) | `Music, Arts, Theater, Sports, Comedy, Festival` | `apps/mobile/types/ui.ts:41-47`, mapped from the backend enum via `apiCategoryToUi` (`ui.ts:50-60`) |
| `SearchBar` chip ids (Discover's local filter UI) | `music, arts, theater, sports, comedy, festival` (lowercase) | `apps/mobile/components/fomo/search-bar.tsx:33-40` |

The `SearchBar` chip vocabulary does not match either the backend enum or
the `apiCategoryToUi` mapping's output values exactly (case and set differ),
and neither the mobile `UiEventCategory` set nor the `SearchBar` chip set is
a subset of the backend enum's exact string values.

**This contract requires the `category` request parameter to carry exact
backend `EventCategory` values only** (§5, §6). Any Explore filter UI that
lets a user pick a category **must** translate its own display labels to
the exact backend enum value before calling `/events/search` — it must
**not** send `Theater`, `Comedy`, or `Festival` (or their lowercase chip-id
forms) directly to the backend, since none of those three exist in
`EventCategory`. **Category-taxonomy alignment between the three
vocabularies above must happen before Explore's filter UI ships** — this is
a precondition for Phase 4 (§19), not something this contract resolves by
inventing a translation layer here.

## 19. Implementation phases

1. **Backend `/events/search` endpoint and tests** — new route (registered
   before `/{event_id}`, §4), new `EventSearchResponse` schema, tests
   covering §5–§13 rules against the existing SQLite-backed test harness
   pattern (`apps/api/tests/api/test_discovery.py`).
2. **Generated OpenAPI and TypeScript contracts** — `pnpm --filter
   @fomo/api-spec build` regenerates `packages/api-spec/openapi.json`,
   `apps/mobile/types/api.generated.ts`, and
   `apps/harvester-dashboard/types/api.generated.ts`; `pnpm --filter
   @fomo/api-spec verify-schema` confirms zero drift.
3. **Explore event-search screen** — replace the `search.tsx` placeholder
   with real text-query search only (no filters yet), reusing `EventCard`/
   `EventDetails`/loading-empty-error primitives per §15–§16.
4. **Category/date/radius filters and Discover handoff** — filter UI
   (blocked on §18's taxonomy alignment) plus the `ExploreHandoffParams`
   navigation from Discover's `SearchBar` per §17.
5. **Android, performance, and regression validation** — physical-device
   pass; confirm Discover/My Events/Profile show no behavioral regression
   per the canonical navigation document's product invariants.

## 20. Tests and validation

- Backend: `pnpm --filter @fomo/api test`
  (`cross-env PYTHONPATH=../../ uv run pytest tests --cov=app --cov-fail-under=95`).
- Backend lint: `pnpm --filter @fomo/api lint` (`uv run ruff check .`).
- Contract drift: `pnpm --filter @fomo/api-spec verify-schema`
  (`uv run python tooling/verify-generated-api-artifacts.py`).
- Full schema/mobile-coherence gate: root `uv run python
  tooling/verify-schema-sync.py` — this is also the check that already
  validates mobile category-alias coherence against the backend enum
  (`tooling/verify-schema-sync.py:332-357`), directly relevant to §18.
- Mobile: `pnpm --filter @fomo/mobile lint` (`expo lint`), `pnpm --filter
  @fomo/mobile exec tsc --noEmit`. **No automated mobile test suite exists**
  (`apps/mobile/package.json` — `"test": "echo 'No tests yet'"`); this is a
  pre-existing gap, not one introduced by Explore (see §22).
- Full local CI equivalent: `pnpm turbo run check-quality --force`.

## 21. Explicit non-goals

This document does not implement:
- The `/events/search` endpoint, its tests, or any schema code.
- The generated OpenAPI/TypeScript artifacts.
- The Explore screen, its hook, or any filter UI.
- The Discover-to-Explore handoff navigation.
- People search, standalone Place/Venue search, standalone Organizer search,
  or universal grouped search.
- Full-text search infrastructure (`pg_trgm`, `tsvector`) or any external
  search platform.
- A relevance-ranking/recommendation algorithm beyond the fixed
  match-priority ordering in §11.
- Any change to `/events/discovery`'s existing behavior, response shape, or
  tests.
- Any change to route files, generated artifacts, or the tab bar.

No production code, migration, or generated API artifact is modified by this
task.

## 22. Open risks

Recorded without resolution — these require product/engineering decisions
or live-environment verification, not invention:

- **Actual PostgreSQL collation and Greek case-search behavior**: not
  verified against a live database in this task. `docker-compose.yml` sets
  no explicit locale/collation. Must be confirmed with a real PostgreSQL
  instance (e.g. `SHOW lc_collate;` / `SELECT datcollate FROM pg_database
  WHERE datname = current_database();`, plus an actual Greek-text search
  query) before §10 point 7's case-folding behavior can be claimed correct.
- **Category-taxonomy alignment** (§18): three divergent vocabularies exist
  today; which one Explore's filter UI displays to users, and how it maps
  to the backend `EventCategory` wire values, is unresolved and must be
  decided before Phase 4.
- **Future trigger for `pg_trgm` or another measured optimization**: no
  threshold (row count, p95 latency, etc.) is defined in this document for
  when plain substring matching should be replaced with a trigram index —
  intentionally left open pending real usage data, not invented here.
- **Lack of automated mobile tests**: `apps/mobile` has no test runner
  configured at all; Explore's search hook (debounce/cancel/pagination
  logic) will ship without automated coverage under the current mobile
  tooling, relying on manual QA (§19 Phase 5) — a pre-existing repository
  gap, not something this contract can resolve.

## 23. Decision record

**Endpoint**: `GET /api/v1/events/search`, new and separate from
`/events/discovery` (unchanged). Registered before `/{event_id}`.

**Criteria requirement**: at least one of `q` (normalized), `category`,
date range, or `lat`/`lng` must be present; otherwise 422.

**Text query**: optional, raw max 200 chars, normalized (trim → empty
becomes `None`) before a 2-character minimum is enforced in code, not via
`Query(min_length=...)`. Matches title, location_name, organizer
display_name only — never description. Case-insensitive by design; Greek/
Unicode correctness requires live-database verification, not claimed here.

**Location**: `lat`/`lng` optional but paired; `radius_km` optional
(default 10 km, bounds `0 < r <= 200`), reusing the existing `ST_DWithin` +
GiST index pattern unchanged from `/events/discovery`.

**Categories**: backend `EventCategory` enum values only, repeated query
param. No fourth vocabulary introduced. Alignment across the three existing
vocabularies is a precondition for shipping filter UI, not resolved here.

**Dates**: `date_from` inclusive, `date_to` exclusive, overlap semantics via
`COALESCE(end_time, start_time) >= date_from AND start_time < date_to`,
timezone-aware throughout.

**Upcoming behavior**: no request parameter; always excludes events whose
effective end has passed. Not configurable in v1.

**Visibility**: reuses `public_event_filters()` unchanged (live, public,
not removed).

**Ordering**: match-priority `CASE` (exact → prefix → substring → venue →
organizer) when `q` is present, then distance (if location given) → start
time → id. Filter-only search: distance (if location given) → start time →
id. Not a recommendation algorithm.

**Pagination**: `limit` (default 20, 1–50) / `offset` (default 0, ≥0);
`has_more` via a `limit + 1` fetch; no `total` count.

**Response**: reuses `EventDiscoveryResponse` per result item unchanged;
only a new pagination-metadata wrapper is added.

**Mobile**: debounce ~350–400 ms, minimum 2-char query, existing
cancellation-flag pattern (no new library), reuse of `EventCard`/
`EventDetails`/loading-empty-error primitives, public unauthenticated
access with authenticated relationship overlays.

**Discover handoff**: primitive-only param shape (`q`, `lat`, `lng`,
`radiusKm`, canonical `category`, future date context); Explore owns all
behavior after the hop. Not implemented by this document.
