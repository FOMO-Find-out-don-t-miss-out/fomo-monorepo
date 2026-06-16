import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { PendingEvent } from '@/types/api'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * The backend's source of truth for place verification is verification_status
 * (unverified | system_matched | manually_verified) — there is no separate
 * boolean field. Derive the boolean here instead of trusting a phantom
 * is_manually_verified field that PlaceResponse never actually sends.
 */
export function isPlaceVerified(place: { verification_status?: string }): boolean {
  return place.verification_status === 'manually_verified'
}

/** FOMO-16: human-readable label for a pending event's dedupe_status, with an unknown-value fallback. */
export function dedupeStatusLabel(status: string): string {
  switch (status) {
    case 'not_checked':
      return 'Not checked'
    case 'duplicate_confirmed':
      return 'Duplicate confirmed'
    case 'possible_match':
      return 'Possible match'
    case 'no_match':
      return 'No match'
    case 'merged':
      return 'Merged'
    default:
      return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  }
}

/**
 * Resolves the related Place id for an event, if one exists. Pending signals only
 * have a candidate match (place_candidate_id) until approved; published events have
 * a confirmed place_id. Returns null when there is no related place to link to.
 */
export function relatedPlaceId(event: PendingEvent, mode: 'pending' | 'published'): string | null {
  return (mode === 'published' ? event.place_id : event.place_candidate_id) ?? null
}

/**
 * FOMO-166: canonical backend category values (packages/domain/models/event.py
 * :: EventCategory). The dashboard must filter/query/store using these exact
 * values — never an invented display label — to avoid mismatches with what
 * ingestion actually stores. Keep in sync with the backend enum.
 */
export const EVENT_CATEGORIES = [
  'Music',
  'Art',
  'Tech',
  'Food',
  'Nightlife',
  'Sports',
  'Business',
  'Community',
  'Other',
] as const

export type EventCategoryValue = (typeof EVENT_CATEGORIES)[number]

/**
 * Friendlier display label for a canonical category value. This is purely a
 * UI label — it never replaces the canonical value used for filtering or
 * editing. Most ingested events are concerts, so "Music" reads as
 * "Live Music" here, but the underlying filter/query value stays "Music".
 */
const CATEGORY_LABELS: Record<EventCategoryValue, string> = {
  Music: 'Live Music',
  Art: 'Art',
  Tech: 'Tech',
  Food: 'Food & Drink',
  Nightlife: 'Nightlife',
  Sports: 'Sports',
  Business: 'Business',
  Community: 'Community',
  Other: 'Other',
}

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category as EventCategoryValue] ?? category
}
