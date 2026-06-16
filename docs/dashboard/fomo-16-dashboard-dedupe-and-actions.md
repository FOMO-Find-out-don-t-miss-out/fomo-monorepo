# FOMO-16: Dedupe status visibility and state-aware moderation actions

This documents a small dashboard UI follow-up to FOMO-16 (collision detection)
and FOMO-164 (moderation dashboard UX). It does not change backend behavior
except where noted, and does not add a collision-resolution or merge-review
workflow.

## Actions shown for Pending Signals

In `components/dashboard/event-inspector.tsx` and `event-list.tsx`, a pending
event (`status === 'pending'`) shows:

- **Approve** — calls `POST /pending-events/{id}/approve`, publishes the event.
- **Reject** — calls `POST /pending-events/{id}/reject`, deletes the pending row.
- **Save Changes** — calls `PATCH /pending-events/{id}` (`updateEvent`).
- Bulk **Execute** (approve) / **Abort** (reject) in the list header, when one
  or more cards are checked.
- A dedupe status badge on every card and in the inspector's Source Info
  panel (see below).

## Actions shown for Published Signals

A published event (`status === 'published'`) shows:

- **Unpublish Event** only — no **Approve** (a live item is already approved;
  showing Approve again is meaningless) and no separate **Reject** (rejecting
  an already-published item has no clear distinct meaning from unpublishing
  it, so it is not shown as a separate action).
- **Save Changes**, since published event editing is genuinely supported —
  it calls `PATCH /moderation/events/{id}` (`updatePublishedEvent`), a real
  backend endpoint distinct from the pending update endpoint.
- No bulk actions and no per-row selection checkboxes. The list previously
  rendered the same "Execute"/"Abort" bulk buttons used by Pending Signals,
  wired to no-op handlers — selecting published cards and clicking them did
  nothing. There is no batch-unpublish backend endpoint, so this was a fake
  action and has been removed (`components/dashboard/event-list.tsx`,
  `event-card.tsx`) rather than wired to fake behavior.

### Is `Unpublish` equivalent to `Move back to pending`?

**Not always.** `ModerationService.unpublish_event` (in
`apps/api/app/services/moderation/moderation_service.py`) deletes the row
from `events`, then looks for a `pending_events` row with a matching
`title`/`start_time` and, only if found, flips its status back to
`pending`. If no matching pending row exists (e.g. it was already cleaned
up, or the event was created some other way), unpublishing simply deletes
the live event with nothing left behind.

Because of this, the dashboard intentionally labels the action **"Unpublish
Event"**, not "Move back to pending" — the latter would overstate a
guarantee the backend doesn't make. The confirmation dialog added in this
change explains both outcomes in the description text, and the success
toast was changed from "Event moved to pending" (inaccurate) to "Event
unpublished" (accurate regardless of which branch the backend takes).

The unpublish action is destructive (removes the live record, with no
guaranteed undo) and now requires confirmation via an `AlertDialog` before
it fires — it previously fired immediately on click.

### Does a true `Delete` for published events exist?

**No.** There is no `DELETE /moderation/events/{id}` endpoint — only
`/moderation/places/{id}` (and the legacy `/moderation/venues/{id}`) support
deletion. No delete button was added for published events; this remains a
backend follow-up if moderators need to permanently remove a published
event that has no pending counterpart to fall back to.

### `Merge Venue` / `Merge Place`

There is no `Merge Venue` (or `Merge Place`) action on events — merge only
exists at the Place level (`components/dashboard/venue-inspector.tsx`), and
its UI text already says "Merge Protocol" / "Execute Merge", not "Merge
Venue". The non-functional `Merge Venue` stub that used to appear on the
event inspector was removed in FOMO-164 and stays removed; no merge action
was reintroduced here.

## Dedupe status visibility (Pending Signals)

FOMO-16 added `dedupe_status` and `candidate_event_id` to
`PendingEventResponse`, plus a `dedupe_status` filter on
`GET /moderation/pending-events`. The dashboard surfaces this only on
Pending Signals (published events are already resolved, so collision state
is no longer relevant there):

- **Sidebar filter** (`components/dashboard/filter-sidebar.tsx`) — a
  "Collision Status" radio group: All Signals / Not Checked / Possible
  Match / Duplicate Confirmed, wired to the `dedupe_status` query param via
  `moderationApi.getPendingEvents(locationName?, geocodingStatus?,
  dedupeStatus?)`. Count badges reflect only the currently loaded result
  set, not global database totals.
- **Event card** (`event-card.tsx`) — a status badge on every card, plus a
  "Candidate linked" badge when `candidate_event_id` is set.
- **Event inspector** (`event-inspector.tsx`) — the same status/icon and an
  optional "Candidate linked" badge in the Source Info panel. This is
  read-only; there is no action to act on the linked candidate.

### What each status means for moderators

| `dedupe_status`       | Meaning                                                                                          |
|------------------------|---------------------------------------------------------------------------------------------------|
| `not_checked`          | No collision was detected against another live/pending event.                                   |
| `possible_match`       | Overlapping signal found, but not confident enough to auto-merge — look closer before approving. |
| `duplicate_confirmed`  | High-confidence/exact-source match; ingestion already claimed/linked this row instead of creating a duplicate. Informational, not an action item. |

`no_match`/`merged` are valid enum values not currently produced by the
collision detector; `dedupeStatusLabel()` in `lib/utils.ts` has a
title-cased fallback for any value it doesn't explicitly recognize.

## Known follow-ups

- **True delete for published events** does not exist on the backend. If
  moderators need to permanently remove a live event that has no matching
  pending row (so unpublish alone won't resurrect it anywhere), a real
  `DELETE` endpoint would need to be added first.
- **True "move back to pending"** is not guaranteed by the current
  `unpublish` endpoint — see above. If this guarantee is needed, the
  backend would need an explicit endpoint that always recreates (or
  preserves) the pending row rather than relying on a title/start_time
  match against on existing one.
- **Richer collision review/merge UI** — there is still no way to act on a
  `possible_match`/`duplicate_confirmed` row beyond the existing
  approve/reject actions, and no UI to inspect the linked candidate event's
  own details inline. A dedicated review flow is a reasonable next step if
  dedupe volume warrants it, but is out of scope here.
