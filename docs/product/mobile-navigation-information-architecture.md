# FOMO Mobile — Navigation & Information Architecture

## 1. Title and status

**Status:** Canonical (recommended architecture for the current product stage).
**Scope:** `apps/mobile` navigation and information architecture only.
**Prepared for:** FOMO-172 scoping and all subsequent mobile navigation work.
**Does not implement code.** This document formalizes an already-agreed product
direction, validates it against the current repository, and defines
implementation boundaries and follow-up scope.

---

## 2. Decision summary

FOMO mobile adopts a **four-tab canonical navigation**:

1. **Discover** — serendipitous, map-first, hyper-local discovery.
2. **Explore** — intentional, entity-based search.
3. **My Events** — planning and attendance (events already related to the user).
4. **You** — identity, account, and personal network hub.

This replaces the current three-implemented-plus-one-placeholder tab set
(`Discover`, `Search` [placeholder], `My Events`, `Profile`) by giving the
placeholder tab a real, bounded purpose (Explore) and renaming/reframing
`Profile` conceptually to `You` (see §10 for the current-vs-target label
distinction). No route files are renamed and no tab bar code changes as part
of this task (see §17 Non-goals).

---

## 3. Product principles

- Each top-level tab represents a **distinct, high-frequency user intent** —
  not a domain object, not a feature flag, not a data source.
- **Serendipity and intent are different mental modes** and must not be
  collapsed into one search/browse surface (this is the core Discover/Explore
  boundary — see §7).
- **Planning is a distinct destination from discovery.** Events a user has
  already related to (Interested/Going) deserve a stable home independent of
  the spatial/temporal discovery feed.
- **Identity and account concerns are nested, not scattered.** Wallet,
  connections, following, notifications-settings all belong under one
  identity destination rather than each claiming a tab.
- **No tab may be justified by the existence of a domain concept alone.** A
  migration, an enum, or a schema table is not evidence of a user-facing
  capability (see §4 for what this repository actually proves is
  implemented vs. schema-only vs. absent).
- **Progressive disclosure over premature breadth.** Ship the entity types
  that have real backend support; document the rest as deferred, not as
  missing UI polish.

---

## 4. Current application state

### 4.1 Tab bar (as implemented today)

`apps/mobile/app/(tabs)/_layout.tsx` defines a custom `Tabs` bar with exactly
four routes, in this order:

| Route file | Current label | Icon | Status |
|---|---|---|---|
| `index.tsx` | Discover | `Map` | ✅ Production |
| `search.tsx` | Search | `Search` | ⏳ Placeholder |
| `saved.tsx` | My Events | `Heart` | ✅ Production |
| `profile.tsx` | Profile | `User` | ✅ Production |

(`docs/design/mobile-global-ui-audit.md` §"Screen inventory" independently
confirms this same four-screen inventory and status classification.)

### 4.2 Discover (`apps/mobile/app/(tabs)/index.tsx`)

Confirmed implemented and API-backed:
- `useDiscovery()` (`apps/mobile/hooks/use-discovery.ts`) — fetches
  `GET /api/v1/events/discovery?lat&lng&radius_km` (`apps/api/app/api/v1/events.py:24-48`),
  gated on device-location readiness.
- `useDeviceLocation()` (`apps/mobile/hooks/use-device-location.ts`) — GPS
  permission flow with a bounded fallback to default coordinates.
- `useEventRelationships()` (`apps/mobile/hooks/use-event-relationships.ts`) —
  batch-fetches Interested/Going state for events currently loaded.
- `FomoMap` (`apps/mobile/components/fomo/fomo-map.tsx`) — Mapbox pins, one
  purple circle layer for all events, one larger circle for the selected
  event; camera `flyTo`/`easeTo` on locate/selection.
- `SearchBar` (`apps/mobile/components/fomo/search-bar.tsx`) — floating input
  with **client-side only** text filtering (`searchText` state on the
  Discover screen, `index.tsx:206-218`, matched against `title`/`venue`
  substrings of the already-fetched events — no network request), a category
  filter chip panel (6 hardcoded categories, `search-bar.tsx:33-40`), a
  calendar/map view toggle, and a non-functional bell icon (renders a dot,
  has no `onPress`, `search-bar.tsx:239-246`).
- `CalendarView` (`apps/mobile/components/fomo/calendar-view.tsx`) —
  date-strip + compact list, alternate presentation of the same
  already-fetched event set.
- `FlatList` carousel — virtualized (FOMO-175), memoized `EventCard`.
- `EventDetails` — bottom-sheet modal shared with My Events, holds
  `IntentSelector` (Interested/Going toggle).

**The backend `/discovery` endpoint itself takes only `lat`, `lng`, and
`radius_km`** (`apps/api/app/api/v1/events.py:26-29`) — category and text
filtering happen entirely client-side over the radius result set. There is
no server-side text-search or category-query parameter on this endpoint.

### 4.3 Search (`apps/mobile/app/(tabs)/search.tsx`)

Confirmed placeholder — verbatim current content:

```tsx
<FomoEmptyState
  icon={<Search size={48} color={Colors.purple} strokeWidth={1.2} />}
  message="Search is coming soon"
  sub="Browse events from the Discover tab for now."
/>
```

No data fetching, no input, no search behavior of any kind
(`docs/design/mobile-global-ui-audit.md` §4 independently confirms: "the
only placeholder screen").

### 4.4 My Events (`apps/mobile/app/(tabs)/saved.tsx`)

Confirmed implemented and API-backed. Two states are surfaced as tabs:

```ts
const TABS = ['Interested', 'Going'] as const;
```

(`saved.tsx:37`). Each tab is backed by an independent `useMyEvents()` call
against `GET /api/v1/me/events?relationship_type=interested|going`
(`apps/api/app/api/v1/me.py:60-73`). Local-intent application (FOMO-178)
moves an event between the two lists on a successful mutation without a
refetch. Date-grouped sections (Today/Tomorrow/future dates). Revision-counter
gating (FOMO-177/178) avoids redundant refetches on focus.

**"Saved" is not rendered as a third tab.** The backend defines a third
relationship type, `saved` (`packages/domain/models/event_relationship.py:11-14`,
`RelationshipType.saved`), with its own dedicated endpoint
`GET /api/v1/me/saved-events` (`apps/api/app/api/v1/me.py:76-83`) — this is
schema **and** API-level support, not merely a migration artifact — but no
mobile screen currently reads or writes it. This is a real,
already-production-ready backend capability that the client simply does not
surface yet.

### 4.5 Profile (`apps/mobile/app/(tabs)/profile.tsx`)

Confirmed implemented and auth-backed. Current sections, in render order:
avatar ring, username, email, divider, `InfoRow` "Role", `InfoRow` "Member
since", error/retry state, Log Out button. No connections, following,
wallet, or notification-settings sections exist today (`profile.tsx:68-104`).
Profile state comes from `useAuth()` with no dedicated data hook — background
sync per FOMO-179 (`profile.tsx:14-26`).

### 4.6 Cross-cutting

- Navigation: custom `BlurView`-backed tab bar, purple active state,
  measured 45–90 ms tap→focus (`docs/mobile/mobile-performance-baseline.md`
  §4 "Navigation / My Events / Discover refocus").
- No screen in the app currently issues a network request keyed on free-text
  search, username, organizer name, or place name.

---

## 5. Canonical four-tab navigation

```
Mobile navigation
├── Discover                          [current — production]
│   ├── Map
│   ├── Nearby carousel
│   ├── Local filters (category, client-side text match)
│   ├── Calendar view
│   └── EventDetails
├── Explore                           [target — replaces placeholder Search]
│   ├── Events                        [MVP — see §8]
│   ├── Places / Venues               [deferred — no backend API today]
│   ├── People                        [deferred — no backend API today]
│   └── Organizers                    [deferred — no backend API today]
├── My Events                         [current — production]
│   ├── Interested
│   └── Going
│       (Saved relationship type exists in the API but is not
│        surfaced as a UI section today — see §4.4, §9)
└── You                                [target — reframes current Profile]
    ├── Profile (current)
    ├── Connections                   [deferred — schema only, no API]
    ├── Following (organizers)        [deferred — schema only, no API]
    ├── Wallet                        [deferred — schema only, no API]
    ├── Notifications                 [deferred — no domain model exists]
    └── Settings (current: Log Out only)
```

---

## 6. Discover responsibilities

Discover is the **map-first, hyper-local discovery experience**. Its
governing question: **"What is happening near me?"**

It owns:
- Current-location discovery, nearby events, configurable radius (currently
  a fixed `DEFAULT_DISCOVERY_RADIUS`, `apps/mobile/utils/location-config.ts`,
  passed to `/events/discovery`).
- Map (`FomoMap`), event pins, selected-event state.
- Nearby event carousel (virtualized `FlatList`, `EventCard`).
- Date selection / calendar view (`CalendarView`).
- Local category/date/radius filters — client-side only today.
- Opening `EventDetails`.

**Ranking bias (as implemented, not as an algorithm claim):** results are
ordered by the backend `ORDER BY ST_Distance(...)` (`events.py:44`) — nearest
first, from the current or last-resolved device location, constrained by the
radius parameter sent to `/discovery`. Category and date/text filters are
applied client-side over that already-distance-sorted set. **No claim is
made of a ranking algorithm beyond distance ordering** — there is no hype,
recency, or personalization weighting in the discovery query today.

Discover must remain focused on spatial/serendipitous discovery and must not
gradually absorb universal entity search — that responsibility belongs to
Explore (§7).

---

## 7. Discover vs Explore boundary

**Discover = serendipity. Explore = intent.**

These are separate top-level user intents because they have opposite
triggers and opposite success conditions:

| | Discover | Explore |
|---|---|---|
| Trigger | "show me what's around" | "I know roughly what/whom I want" |
| Input | none required (location is ambient) | a query, a name, a filter set |
| Success | serendipitous surprise | a specific, found result |
| Scope | spatially bounded (radius) | entity-bounded (event/person/place/organizer) |

Conflating them either turns Discover into a generic search box (destroying
its map-first identity) or turns Explore into "Discover with more filters"
(destroying its intent-driven identity). Each deserves persistent navigation
because each is used on a different footing — Discover on open/idle browsing,
Explore on a specific need.

### SearchBar boundary

The `SearchBar` component rendered inside Discover
(`apps/mobile/components/fomo/search-bar.tsx`) must not become a second,
independent search system. Its long-term role is a **launcher into Explore**,
not a parallel query engine. Desired conceptual flow:

1. User is viewing Discover.
2. User taps the Discover search field.
3. The application navigates to Explore.
4. Explore starts with a nearby scope derived from Discover context (current
   or selected location, current radius, and date/category context where
   applicable).
5. Search and result behavior are owned entirely by Explore from that point.

This document does **not** prescribe the exact Expo Router navigation call
or param-passing mechanism — the current codebase has no existing
tab-to-tab deep-link pattern with pre-filled state to model this on
unambiguously, so that remains an implementation decision for FOMO-172 (see
§18).

Discover's own local controls — category filter chips, calendar/map toggle,
radius — **remain Discover-owned** and are not duplicated blindly inside
Explore; Explore has its own entity-scoped filters (§8).

---

## 8. Explore entity taxonomy

Governing question: **"I know roughly what or whom I want to find."**

Long-term taxonomy: **All, Events, People, Places/Venues, Organizers.**

### Events
Search dimensions: title, category, date/date-range, city/area,
distance/radius, venue, organizer.

### People
Search dimensions: username, display name, connection state, mutual
connections (only if supported later).

### Places / Venues
Search dimensions: place/venue name, area, city, upcoming events at the
place, follow state (only if supported).

### Organizers
Search dimensions: organizer name, verification status, upcoming events,
follow state.

### Scope rule (mandatory)

**Explore must expose only entities backed by real API and domain support.**
No inactive entity tabs, no fake result groups, no mock results, no
non-functional filters.

### Repository capability check — what actually exists today

| Entity | Domain/schema support | API support | Verdict |
|---|---|---|---|
| Events (by radius) | `Event` model (`packages/domain/models/event.py`) | `GET /api/v1/events/discovery` (`events.py:24`) — lat/lng/radius only | **Real, partial.** No text/category/date server-side query param exists yet. |
| Events (by text/title/category/date/venue/organizer) | same `Event` model | **none** — no query endpoint beyond discovery-by-radius and get-by-id | **Not implemented server-side.** |
| Places/Venues | `Place` model (`packages/domain/models/place.py`, aliased `Venue`) | **no router** — not present in `apps/api/app/api/api.py`'s registered routers (`health, identity, users, me, admin, ingestion, moderation, events` only) | **Schema only. No API.** |
| Organizers | `Organizer` model (`packages/domain/models/organizer.py`) | **no router** | **Schema only. No API.** |
| People (users) | `User`/`Profile` models (`packages/domain/models/user.py`) | only `GET /api/v1/users/me` (`users.py:15`) — no listing/search endpoint | **Schema only for search purposes. No API.** |

### Progressive rollout (adjusted to actual repository capabilities)

**Explore v1:**
- **Events** — the only entity with any existing API surface, and even that
  surface (`/discovery`) supports radius only, not the fuller dimension list
  above. Explore v1 event search is real work, not a thin UI wrapper.
- **Places/Venues** — **not included in v1.** Unlike the instruction template's
  conditional ("only if production API support exists"), this repository has
  **no** place/venue API route at all — the `Place` table exists purely as
  domain/schema support consumed internally (event geocoding), not as a
  client-facing resource.

**Later (each requires new backend work, not just new mobile UI):**
- People — requires a user-search/listing endpoint (none exists) and a
  product decision on what "searchable" means for privacy (today only
  `/users/me` is exposed; there's no public user directory endpoint).
  `UserConnection` schema exists (§11) but has no API today either.
- Places/Organizers — requires read APIs for `Place`/`Organizer` (neither
  has a router today) plus, if follow-state search dimensions are wanted,
  the organizer-follow API (schema exists, no API — §11) and a place-follow
  model (does not exist at all — §11).
- Grouped universal "All" results — depends on all of the above existing
  first; there is nothing to group today beyond Events.

---

## 9. My Events responsibilities

Governing question: **"What have I shown interest in, and what am I planning
to attend?"**

Currently supported states (accurate to `apps/mobile/app/(tabs)/saved.tsx`):
- **Interested** — `GET /me/events?relationship_type=interested`
- **Going** — `GET /me/events?relationship_type=going`

**Saved is not included in the canonical immediate UI.** The `saved`
relationship type and its `GET /me/saved-events` endpoint exist and are
production-ready at the API layer (§4.4), but no mobile screen renders,
writes, or reads it today — there is no third tab, no save action anywhere
in the current UI. Per the task's explicit rule, a domain/API capability
that exists but has no client-facing entry point is not treated as
in-canonical-scope; adding a Saved tab is future scope, not this
architecture's immediate state.

Future capabilities to describe, not scope now: upcoming vs. past split,
list/calendar presentation, reminders, friends attending, event-change
notifications, attendance history.

Preserved boundary:
- Discover finds nearby events.
- Explore searches intentionally.
- My Events manages events the user has already related to.

### Label decision: "My Events" vs. "Plans"

**Canonical label: "My Events."** Rationale — this is the label already
implemented (`_layout.tsx:15`, `saved.tsx:336`) and it accurately describes
the current content (Interested + Going lists of *events*, not itinerary
items, reminders, or third-party plans). "Plans" implies a broader
scheduling/itinerary concept (multi-event day plans, external calendar
integration) that has no backend support and is not part of the current
product surface. Adopting "Plans" now would create a label/content mismatch;
revisit only if the screen's scope genuinely grows into itinerary planning.
This task does not rename the route or the label in code.

---

## 10. You responsibilities

Governing question: **"Who am I in FOMO, and what belongs to my account?"**

### Label decision: "You" vs. "Profile" vs. "Me"

**Canonical label: "You."** Rationale:
- "Profile" (the current label, `_layout.tsx:16`) accurately describes
  today's single-screen content but undersells the destination's long-term
  role as the umbrella for wallet, connections, following, and settings —
  all of which are account-level, not "profile" fields in the narrow sense.
- "Me" is a viable alternative but reads slightly more casual/social-network
  and is easily confused with the `/users/me` and `/me/*` API namespace
  already in the codebase (`apps/api/app/api/v1/me.py`,
  `apps/api/app/api/v1/users.py`) — using "Me" as the tab label risks
  implying those two things are the same concept when the tab is a UI
  destination and `/me` is an API prefix for the authenticated user's
  sub-resources (relationships, events).
- "You" is the more conventional umbrella label for an identity+account hub
  across four-tab mobile apps at this scale, and does not collide with
  existing naming.

This document recommends **"You"** as the target canonical label. **No
route or code label is renamed in this task** — `profile.tsx` and the
`Profile` tab label remain unchanged until a dedicated implementation
ticket does so deliberately.

### Current vs. next vs. future sections

**Current (implemented, `profile.tsx`):** avatar, username, email, role,
member-since, log out, error/retry state for profile sync.

**Next useful sections (real backend support exists at schema level, no
API yet — see §11 for exact gaps):** Connections, Following (organizers),
Wallet.

**Future/speculative (no domain model exists at all today):**
Followed places (no place-follow model), Notifications preferences (no
notification model), a general "Privacy" settings surface (no privacy
schema found).

This document does not imply any of the "next" or "future" sections are
implemented today.

---

## 11. Wallet and coins placement

Coins/wallet backend reality, precisely:

- `WalletAccount` (`packages/domain/models/wallet.py:19-29`) — one row per
  user, integer `balance`.
- `WalletTransaction` (`wallet.py:32-75`) — `spend`/`refund`/`grant`/
  `adjustment` types, optionally linked to an `event_id`.
- `HypeLedger` (`packages/domain/models/hype.py`) — links a user, an event,
  an `amount`, and an optional `wallet_transaction_id` — i.e., the
  "coin economy" today is specifically a **hype-boosting spend mechanism**
  tied to events, not a generic currency with arbitrary uses.
- **No wallet or hype API router is registered** in
  `apps/api/app/api/api.py` — the full registered set is `health, identity,
  users, me, admin, ingestion, moderation, events`. There is no
  `GET /me/wallet`, no transaction-history endpoint, no spend endpoint
  reachable from a client today.

**Conclusion: the wallet backend is schema-only. It is not production-ready
from a client-integration standpoint** — the tables and relationships exist,
but nothing in `apps/api` exposes them. This document explicitly does not
assume otherwise merely because the models and an Alembic-managed schema
exist (per the task's litmus test on distinguishing schema support from
production readiness).

### Recommended placement (once the API exists)

1. Compact wallet/balance indicator within You.
2. Dedicated Wallet screen nested under You.
3. Contextual balance display during coin-spending (hype) actions —
   current balance, proposed spend, resulting balance, confirmation.
4. Transaction history inside Wallet.
5. Wallet accounting remains a separate domain concern from profile data
   (already true at the schema level — `WalletAccount`/`WalletTransaction`
   are distinct tables from `User`/`Profile`).

**Coins do not become a top-level tab at this product stage** — regardless
of future API work, wallet usage alone does not meet the bar for a
persistent top-level destination (see §16 for what would).

This document does not design or implement the coin economy, and does not
claim the current wallet backend is production-ready.

---

## 12. Social graph placement

Three distinct relationship types exist or are implied — they must not be
merged into one vague "follow" model:

| Relationship | Model | API | Notes |
|---|---|---|---|
| User ↔ User connection | `UserConnection` (`packages/domain/models/social.py:18-54`) — `pending/accepted/rejected/blocked` status | **none registered** | Schema only. |
| User → Organizer follow | `OrganizerFollower` (`social.py:57-78`) | **none registered** | Schema only. |
| User → Place follow | — | — | **No model exists at all.** Not schema-only — genuinely absent from the domain layer. |

Recommended placement (once APIs exist):
- **People discovery** belongs in Explore (§8, deferred — no user-search API
  exists yet either).
- **Connections and organizer-following** belong under You (§10, "next"
  section — schema exists, API does not).
- **Social signals** (e.g., "3 connections going") belong contextually on
  events, once the underlying connection/attendance-visibility API exists —
  no such surface exists today.
- **Connection requests or activity** may later appear in notifications
  (§13) — no notification model exists today, so this is fully speculative.

Organizer following is a distinct relationship from mutual user-to-user
connections and must be presented as such if/when both ship — they have
separate tables, separate semantics (asymmetric follow vs. bidirectional
connection request), and likely separate UI treatments (a follow button vs.
a connection-request flow).

---

## 13. Notifications and activity placement

**No notification or activity domain model exists anywhere in
`packages/domain/models/`** (confirmed by search — no file, no class,
matches nothing). This is a full product/backend gap, not a schema-only
gap like wallet or social.

Per the task's constraint, no permanent Activity/Notifications tab is
recommended at this stage. Near-term placement to describe conceptually
(none of this is implemented):
- A notification entry point in existing global or account UI (e.g., a
  bell icon — one already exists visually in `SearchBar`,
  `search-bar.tsx:239-246`, but it is **non-functional today**: no
  `onPress`, no badge count wired to real data, purely decorative).
- Notification preferences nested under You.
- Notification/activity detail as a nested screen, not a tab.

### Future trigger for a persistent Activity tab

Justified only once there is genuine daily-relevant volume: connection
requests, followed-organizer activity, event changes, reminders, social
attendance signals, or wallet/hype events. None of these have a data source
today (no connections API, no organizer-follow API, no notification model,
no wallet API) — so this trigger condition cannot even be evaluated
currently, let alone met.

---

## 14. Route and information hierarchy

Current Expo Router structure (unchanged by this task):

```
apps/mobile/app/
├── _layout.tsx              (root — AuthProvider, AuthGate, font loading)
├── login.tsx
├── auth/callback.tsx
└── (tabs)/
    ├── _layout.tsx           (custom Tabs + CustomTabBar)
    ├── index.tsx             → Discover
    ├── search.tsx             → placeholder (target: Explore)
    ├── saved.tsx               → My Events
    └── profile.tsx              → Profile (target label: You)
```

Target hierarchy (conceptual — no files are renamed by this document):

```
(tabs)/
├── index.tsx        → Discover
├── search.tsx        → Explore   [FOMO-172 implements this]
├── saved.tsx          → My Events
└── profile.tsx         → You
```

Nested destinations described in this document (Wallet, Connections,
Following, Notifications settings) do not exist as routes today; when
implemented they belong as nested screens/stacks under the `profile.tsx`
(You) route tree, not as new top-level tabs.

---

## 15. MVP scope

The MVP for this architecture is the **navigation shape**, not a feature
buildout:

- Four tabs, in the order Discover → Explore → My Events → You.
- Discover: unchanged (already production).
- Explore: replaces the Search placeholder with **real event search**
  (title/category/date/venue/organizer dimensions over the existing `Event`
  data), scoped by FOMO-172 (§18). Places/People/Organizers are explicitly
  out of MVP because no backend API exists for any of them.
- My Events: unchanged (already production; Interested/Going only).
- You: unchanged content for now (current Profile screen), under the new
  conceptual label; nested Wallet/Connections/Following/Notifications are
  explicitly out of MVP pending their own backend work.

---

## 16. Deferred capabilities

Deferred, with the concrete blocker for each:

| Capability | Blocker |
|---|---|
| Explore: Places/Venues search | No `Place`/`Venue` API router exists. |
| Explore: People search | No user-search/listing API exists; `/users/me` is the only user endpoint. |
| Explore: Organizers search | No `Organizer` API router exists. |
| Explore: universal "All" grouped results | Depends on all of the above shipping first. |
| You: Wallet screen | No wallet API router exists (schema only). |
| You: Connections | No `UserConnection` API exists (schema only). |
| You: Following (organizers) | No `OrganizerFollower` API exists (schema only). |
| You: Followed places | No place-follow model exists at all (not even schema). |
| You: Notification preferences | No notification domain model exists at all. |
| Activity tab | No data source for any of its candidate triggers exists yet. |
| My Events: Saved section | API exists (`GET /me/saved-events`) but no UI reads/writes it; a genuine "add this" affordance is also undesigned. |
| Discover SearchBar → Explore handoff | No existing tab-to-tab context-passing pattern in the codebase to model the handoff on; needs a concrete design as part of FOMO-172 or a preceding ticket. |

---

## 17. Navigation anti-goals

- Do not add a tab for every domain capability that has a database table.
- Do not treat wallet usage alone as justification for a Wallet tab.
- Do not create a Social/Friends/Activity tab before real usage volume
  exists (§13, §16).
- Do not let the Discover SearchBar grow into a second, competing search
  system — it launches Explore, it does not own results.
- Do not let Explore render inactive entity tabs, mock results, or
  non-functional filters for entities without real API support (§8).
- Do not exceed five tabs without strong evidence of a missing
  high-frequency intent.
- Do not rename routes, change the tab bar, implement search, implement
  wallet/coins, implement notifications, or change backend contracts as
  part of this document (see §19).

---

## 18. Impact on FOMO-172

**Before this document:** FOMO-172 could be read as "fill the empty Search
tab with any search UI" — an open-ended, unscoped ticket.

**After this document:** FOMO-172 becomes the **first real Explore
implementation**, constrained by what the backend actually supports today.

**Recommended FOMO-172 scope:**

> Implement Explore v1 for real event search (title, category, date/date
> range, venue, organizer, distance/radius dimensions) against the `Event`
> domain model, replacing the `search.tsx` placeholder. Scope includes
> whatever backend query-endpoint work is required — **the current
> `/api/v1/events/discovery` endpoint only accepts `lat`/`lng`/`radius_km`
> (`apps/api/app/api/v1/events.py:24-48`) and has no text/category/date
> query support**, so FOMO-172 is not purely a client-side ticket; it likely
> requires a new or extended events-search endpoint. Location/place
> filtering is limited to whatever the events endpoint itself can support
> (radius from a point) — a dedicated Place/Venue entity search is
> explicitly out of scope (§16).

**Explicitly excluded from FOMO-172** (each needs its own follow-up ticket,
listed with its blocker):
- People search — needs a new user-search/listing API (§16).
- Places/Venues search — needs a new `Place` read/search API (§16).
- Organizers search — needs a new `Organizer` read/search API (§16).
- Universal "All" grouped search — needs all of the above first.
- The Discover SearchBar → Explore handoff mechanism (context pre-fill) —
  needs its own design decision since no existing pattern in the codebase
  covers cross-tab context passing (§7, §16); FOMO-172 may design this
  handoff as part of its own scope, but it is called out separately here
  because it is a navigation-architecture decision, not just a search
  feature, and should be reviewed as such.

---

## 19. Non-goals

This document does not:

- Implement FOMO-172.
- Add or rename routes.
- Change the tab bar.
- Implement user search.
- Implement venue search.
- Implement organizer search.
- Implement wallet or coins.
- Implement notifications.
- Change backend contracts.
- Create placeholder screens.
- Add mock data.
- Modify production code.

---

## 20. Future evolution triggers

The four-tab shape should be revisited only on concrete evidence, not
speculation:

- **High-volume social activity** (connection requests, organizer activity,
  attendance signals reaching daily-relevant volume) may justify a
  persistent Activity tab — currently unmeasurable, since none of the
  underlying APIs exist (§13).
- **Organizer tooling** (event creation/management workflows) may justify a
  separate creator-mode application or workspace rather than folding
  organizer tools into the consumer tab bar — no such tooling exists in
  `apps/mobile` today.
- **Wallet usage alone does not justify a Wallet tab** — even after the
  wallet API ships, placement stays nested under You unless spend frequency
  and screen-depth data later argue otherwise.
- **Ticketing or messaging**, if ever added, would likely require
  architectural reconsideration of the tab bar rather than nesting under an
  existing tab — neither exists in the domain layer today.

---

## 21. Open questions

1. **Explore backend scope for FOMO-172:** should the events-search endpoint
   be a new `/events/search` route, an extension of `/events/discovery`, or
   a query-parameter superset of both? Not decided by this document —
   `apps/api/app/api/v1/events.py` currently has no precedent for a
   multi-dimension query endpoint to extend.
2. **Discover → Explore handoff mechanism:** exact Expo Router
   params/navigation call to pre-fill Explore with Discover's location/
   radius/category context (§7, §18) — no existing cross-tab context-passing
   pattern exists in the codebase to model this on.
3. **"Saved" relationship exposure:** the backend already supports a third
   relationship type and endpoint (§4.4, §9) with zero mobile surface. Is
   there a product reason it was built but never wired to a UI, or is this
   simply unclaimed scope? Worth confirming before assuming it's low-effort
   follow-up work.
4. **User-search privacy model:** if/when a People search ships in Explore,
   what determines a user's discoverability (opt-in setting, connection-only
   visibility, fully public)? No privacy/visibility schema exists today to
   answer this.
5. **Label rollout timing:** when should `profile.tsx`'s tab label actually
   change from "Profile" to "You" in code — bundled with the first nested
   You sub-screen (e.g., Wallet) shipping, or independently as a
   pure-rename ticket? Not decided here (§17, §19 — out of scope for this
   task either way).

---

## Decision record

**Decision:**
Four tabs: Discover, Explore, My Events, You.

**Reason:**
Each tab represents a distinct high-frequency user intent: ambient
serendipity, intentional search, plan management, and identity/account.

**Key boundary:**
Discover is nearby serendipitous discovery. Explore is intentional
multi-entity search. The Discover `SearchBar` launches Explore; it does not
run a second search system.

**Coins:**
Nested under You (Wallet, once an API exists) and shown contextually during
spend actions — not a top-level tab. Current backend support is schema-only
(`WalletAccount`, `WalletTransaction`, `HypeLedger`) with no registered API
router.

**Social:**
People search belongs in Explore (deferred — no user-search API).
Connections and organizer-following belong under You (deferred — schema
exists via `UserConnection`/`OrganizerFollower`, no API). Social signals
appear contextually on events once supporting APIs exist. No place-follow
model exists at all.

**Notifications:**
Nested/entry-point experience until activity volume justifies a persistent
destination. No notification domain model exists in the repository today —
this is a full gap, not a schema-only gap.

**FOMO-172:**
Scoped as the first real Explore implementation: event search over title,
category, date, venue, organizer, and distance/radius, extending or
replacing the radius-only `/api/v1/events/discovery` endpoint. People,
Places/Venues, Organizers, and universal search are explicitly deferred to
their own follow-up tickets, each blocked on a currently-nonexistent API.
