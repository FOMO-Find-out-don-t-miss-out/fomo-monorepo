# FOMO-164: Moderation Dashboard UX Consistency

## Purpose

`apps/harvester-dashboard` is the internal moderator/admin tool used to review
ingested signals, manage canonical place records, and administer user roles.
It is distinct from the end-user mobile app. This pass cleaned up naming,
removed non-functional UI actions, added useful Places filtering/sorting, and
brought the User Management page in line with the rest of the dashboard's
visual language. No backend behavior, API contracts, or RBAC rules changed.

## Terminology decisions

The dashboard now uses moderator-facing language consistently in the UI:

| UI term            | Meaning                                                        |
|---------------------|-----------------------------------------------------------------|
| Pending Signals     | Raw/ingested events awaiting moderation (`/`)                  |
| Published Signals   | Live, published events (`/published`)                          |
| Places              | Canonical location records, formerly "Venues" (`/places`)      |
| User Management     | Admin-only user/role management (`/admin/users`)               |

"Venue"/"Venues" no longer appears anywhere in rendered UI text. Backend
entities, API routes (`/moderation/venues*`), function names
(`getVenues`, `updateVenue`, `mergeVenues`), and component file names
(`venue-list.tsx`, `venue-card.tsx`, `venue-inspector.tsx`) were intentionally
left unchanged — renaming them was out of scope and not necessary for the UX
goal. The route folder `app/venues` was renamed to `app/places` since the URL
is user-(moderator-)facing.

## Published Signal detail actions

In the event inspector (`components/dashboard/event-inspector.tsx`):

- **Approve/Reject** remain visible only for `pending` events — this logic
  already existed and was preserved as-is.
- **Unpublish Event** is the only action shown for `published` events. There
  is no "Approve" action for already-published items, since approving a live
  item is semantically meaningless.
- The **"Merge Venue"** button was removed. It was a non-functional stub
  (`toast.info('Merge feature coming soon')`) and violated the project rule
  against faking destructive/state-changing UI actions. Real, working merge
  functionality already exists at the Place level in
  `components/dashboard/venue-inspector.tsx`, gated behind a confirmation
  `AlertDialog`. Merging belongs conceptually to Places, not individual
  signals, so no replacement action was added to the event inspector.

## Places filters and sorting

`app/places/page.tsx` and `components/dashboard/venue-list.tsx` now support,
entirely client-side (no backend API changes):

- **Search by name/city** — existing server-side search query param, unchanged.
- **Filter by verification status** — `all | unverified | system_matched | manually_verified`,
  matching the backend `PlaceVerificationStatus` enum exactly.
- **Missing coordinates filter** — a checkbox that shows only places with a
  null `lat` or `lng`.
- **Sort by match confidence** (`relevance`, descending) or **recently
  updated** (`updated_at` falling back to `created_at`, descending).

These are derived in-memory from the already-fetched list (`useMemo` in
`app/places/page.tsx`); no new query params were introduced.

### Verification status bug fix

While wiring up the verification filter, found that the frontend `Venue`/
`VenueUpdate` types declared an `is_manually_verified: boolean` field that the
backend (`PlaceResponse`/`PlaceUpdate` in `apps/api/app/schemas/moderation.py`)
never sends or accepts — only `verification_status` exists. This made the
"Manual Verified" toggle and verified/unverified filtering silently no-op.
Fixed by adding `isPlaceVerified()` in `lib/utils.ts`, which derives the
boolean from `verification_status === 'manually_verified'`, and rewiring all
read/write sites (`venue-card.tsx`, `venue-inspector.tsx`, `app/places/page.tsx`)
to use it instead of the phantom field.

## Sidebar

`components/dashboard/dashboard-layout.tsx` wraps every sidebar icon (nav
items, user identity, settings, logout) in a Radix `Tooltip` that shows the
full label on hover, in addition to the existing native `title` attribute.
The sidebar stays icon-only/compact; no layout or navigation behavior changed.

## User Management styling

`app/admin/users/page.tsx` was restyled to use the same primitives and neon
dark theme utility classes as the rest of the dashboard (`Button`, `Badge`,
`Input`, `Select`, `Dialog`, `card-neon`, `input-neon`, `badge-neon*`,
`text-neon-glow-blue`, `scrollbar-neon`) instead of raw HTML elements with
plain Tailwind classes. All existing functionality and RBAC behavior are
unchanged:

- Still gated by `RequireRole roles={['admin']}` inside `DashboardLayout`
  (which itself requires `MODERATOR_AND_ABOVE`).
- Role changes still go through `adminApi.updateUserRole`; self-demotion is
  still blocked by disabling the role selector for the current user.
- Invite flow still calls `adminApi.inviteUser` with the same payload and
  success/error handling; it's now a proper `Dialog` instead of a hand-rolled
  fixed-position overlay.

## Known follow-ups

- There is no dedicated "Move back to pending" backend action distinct from
  "Unpublish" — the existing unpublish mutation in `venue-inspector.tsx`/
  `event-inspector.tsx` is used as-is. If product wants these to be
  semantically distinct in the future, that requires a backend API addition
  first; the frontend should not fake the distinction.
- No automated tests were added for `app/admin/users/page.tsx` (none existed
  before this change either). Consider adding component tests if this page
  sees further changes.

## FOMO-16 follow-up: dedupe status in Pending Signals

FOMO-16 added collision detection on the backend
(`dedupe_status`/`candidate_event_id` on `PendingEventResponse`, plus a
`dedupe_status` query filter on `GET /api/v1/moderation/pending-events`). This
follow-up surfaces that data in the Pending Signals view (`app/page.tsx`) —
it does not add any merge or collision-resolution workflow.

### Where it appears

- **Sidebar filter** (`components/dashboard/filter-sidebar.tsx`) — a new
  "Collision Status" radio group, shown only in `mode="pending"`, alongside
  the existing "Verification Protocol" (geocoding status) filter. Options:
  All Signals, Not Checked, Possible Match, Duplicate Confirmed. The count
  badge next to each option reflects only the currently loaded result set
  for the active filters — it is **not** a global database count.
- **Event card** (`components/dashboard/event-card.tsx`) — every pending
  signal card shows a small dedupe status badge under the title (label via
  `dedupeStatusLabel()` in `lib/utils.ts`), plus a "Candidate linked" badge
  when `candidate_event_id` is set.
- **Event inspector** (`components/dashboard/event-inspector.tsx`) — the
  Source Info panel shows the same dedupe status label/icon and, if present,
  a "Candidate linked" badge (hover title shows the linked event id). This
  is read-only; there is no action to act on the linked candidate from here.

### Filter behavior

The radio selection drives a new optional third parameter on
`moderationApi.getPendingEvents(locationName?, geocodingStatus?, dedupeStatus?)`
(`lib/api.ts`), which appends `dedupe_status` query params exactly like the
existing `geocoding_status` filter does. It is wired into the same
`useQuery` key as the other Pending Signals filters in `app/page.tsx`, so
switching it re-fetches from the backend rather than filtering client-side.

### What each status means for moderators

| `dedupe_status`         | Meaning                                                                 |
|--------------------------|--------------------------------------------------------------------------|
| `not_checked`            | No collision was detected against another live/pending event.          |
| `possible_match`         | Some signal (place/time/title) overlaps with another event, but not enough to auto-merge. Needs a manual look — approve/reject as normal, but check it isn't a duplicate first. |
| `duplicate_confirmed`    | High-confidence or exact-source match against another record. Ingestion already claimed/linked this row instead of creating a duplicate; this status is informational, not an action item. |

`no_match`/`merged` are valid backend enum values not currently produced by
ingestion's collision detector, but `dedupeStatusLabel()` has a readable
fallback for any value it doesn't explicitly know about (title-cases the
raw enum string), so the UI never shows a raw/blank value if the backend
adds a new status later.

### Known follow-up

This is intentionally a small surfacing change, not a collision-resolution
UI. There is still no way to act on a `possible_match`/`duplicate_confirmed`
row beyond the existing approve/reject actions, and no merge UI for events
(only Places have one). A richer review flow — e.g. showing the linked
candidate event's own details inline, or a dedicated moderator action for
confirming/dismissing a possible match — is a reasonable next step if dedupe
volume warrants it, but is out of scope here.
