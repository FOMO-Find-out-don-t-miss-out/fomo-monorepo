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
