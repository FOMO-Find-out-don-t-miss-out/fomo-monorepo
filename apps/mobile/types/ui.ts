/**
 * UI-level types for the mobile app.
 *
 * These are NOT direct API types. They represent what the UI renders, which
 * includes display-only fields computed from (or not yet present in) the API.
 *
 * API-aligned types live in api.generated.ts.
 * Import UI types from here for anything that goes into components.
 */
import type { components } from './api.generated';

// ── API-aligned types ────────────────────────────────────────────────────────

/** Event as returned by the discovery endpoint. Use when calling the API. */
export type ApiEvent = components['schemas']['EventDiscoveryResponse'];

/**
 * Category values as defined in the backend domain model
 * (packages/domain/models/event.py :: EventCategory).
 * Use when mapping raw API data.
 */
export type ApiEventCategory =
  | 'Music'
  | 'Art'
  | 'Tech'
  | 'Food'
  | 'Nightlife'
  | 'Sports'
  | 'Business'
  | 'Community'
  | 'Other';

// ── UI display types (mobile-specific, NOT from API) ─────────────────────────

/**
 * Display category labels used in mobile UI components.
 * These are intentionally different from ApiEventCategory — they represent
 * the visual buckets the mobile app shows to users.
 * When rendering real API data, convert with apiCategoryToUi().
 */
export type UiEventCategory =
  | 'Music'
  | 'Arts'
  | 'Theater'
  | 'Sports'
  | 'Comedy'
  | 'Festival';

/** Maps API category values to mobile UI display buckets. */
export const apiCategoryToUi: Record<ApiEventCategory, UiEventCategory> = {
  Music:     'Music',
  Art:       'Arts',
  Tech:      'Arts',
  Food:      'Festival',
  Nightlife: 'Comedy',
  Sports:    'Sports',
  Business:  'Theater',
  Community: 'Festival',
  Other:     'Music',
};

/**
 * UI-only fields that have no direct API counterpart.
 * Computed from API data or provided by future integrations.
 */
export interface UiEventFields {
  /** Venue display name. Derived from API's location_name. */
  venue: string;
  /** Formatted date string. Derived from API's start_time. */
  date: string;
  /** Formatted time string (HH:MM). Derived from API's start_time. */
  time: string;
  /** Raw ISO start time string. Kept for chronological sorting and date grouping. */
  startTime?: string;
  /** Intensity bucket. Derived from API's hype_score (high ≥ 70, medium ≥ 40, low otherwise). */
  hypeLevel: 'high' | 'medium' | 'low';
  /** Image URI. Maps to API's photo_url. */
  imageUri?: string | null;
  /** Specific ticket purchase URL. Maps to API's ticket_url. */
  ticketUrl?: string | null;
  /** Original event source URL. Maps to API's source_url. */
  sourceUrl?: string | null;
  /** Latitude from the geocoded event location. Used for directions. */
  lat?: number;
  /** Longitude from the geocoded event location. Used for directions. */
  lng?: number;
  /** Human-readable distance. Computed client-side — requires device location (not yet implemented). */
  distance?: string;
  /** Formatted price string. Not available from the API — reserved for future use. */
  price?: string;
}

/**
 * Full UI event type used by mobile components.
 * Combines the API-sourced identity fields with UI display fields.
 */
export interface UiEvent extends UiEventFields {
  id: string;
  title: string;
  category: UiEventCategory;
  hypeScore?: number;
}

/**
 * Mobile intent model. A user can have exactly one intent per event.
 * Maps backend RelationshipType[] at the API boundary:
 *   going      → 'going'
 *   interested → 'interested'
 *   (no intent or only saved) → null
 * `saved` is dormant in mobile MVP and is ignored here.
 */
export type EventIntent = 'interested' | 'going' | null;

// Re-export EventCategory under the legacy name so existing components
// don't need to be updated beyond their import path.
export type { UiEventCategory as EventCategory };
export type { UiEvent as Event };
