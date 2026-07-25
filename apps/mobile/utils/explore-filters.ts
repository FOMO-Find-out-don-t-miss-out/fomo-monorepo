import type { components } from '../types/api.generated';

/**
 * Backend wire-contract category enum, reused directly from the generated
 * OpenAPI types rather than duplicating a handwritten string union.
 */
export type BackendEventCategory = components['schemas']['EventCategory'];

/**
 * Canonical mobile-facing label per backend category (FOMO-172 Phase 4A).
 * "Art" displays as "Arts"; every other value's label matches its wire value
 * verbatim. The wire VALUE sent to the API is always `value`, never `label`.
 */
export const EXPLORE_CATEGORY_OPTIONS: ReadonlyArray<{
  value: BackendEventCategory;
  label: string;
}> = [
  { value: 'Music', label: 'Music' },
  { value: 'Art', label: 'Arts' },
  { value: 'Tech', label: 'Tech' },
  { value: 'Food', label: 'Food' },
  { value: 'Nightlife', label: 'Nightlife' },
  { value: 'Sports', label: 'Sports' },
  { value: 'Business', label: 'Business' },
  { value: 'Community', label: 'Community' },
  { value: 'Other', label: 'Other' },
];

const CATEGORY_LABELS: Record<string, string> = Object.fromEntries(
  EXPLORE_CATEGORY_OPTIONS.map((option) => [option.value, option.label]),
);

/** Canonical display label for a raw backend category value. */
export function backendCategoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

// ── Date presets ──────────────────────────────────────────────────────────────

export type DatePreset = 'any' | 'today' | 'tomorrow' | 'weekend' | 'next7days';

export const DATE_PRESET_OPTIONS: ReadonlyArray<{ value: DatePreset; label: string }> = [
  { value: 'any', label: 'Any date' },
  { value: 'today', label: 'Today' },
  { value: 'tomorrow', label: 'Tomorrow' },
  { value: 'weekend', label: 'This weekend' },
  { value: 'next7days', label: 'Next 7 days' },
];

export function datePresetLabel(preset: DatePreset): string {
  return DATE_PRESET_OPTIONS.find((option) => option.value === preset)?.label ?? preset;
}

export interface DateBounds {
  dateFrom: string | null;
  dateTo: string | null;
}

function startOfLocalDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0);
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

/**
 * Computes concrete [start, end) UTC ISO bounds for a date preset, evaluated
 * against `referenceNow`. Day boundaries are derived from the device's local
 * calendar day, then serialized to UTC via Date#toISOString() — this is what
 * makes the bounds timezone-aware even though the API only sees UTC strings.
 *
 * Callers must compute this once at "Apply" time and reuse the same result
 * for pagination/retry — do not call this again per page (see
 * docs/product/explore-v1-event-search-contract.md, Phase 4A addendum).
 */
export function computeDateBounds(preset: DatePreset, referenceNow: Date = new Date()): DateBounds {
  switch (preset) {
    case 'any':
      return { dateFrom: null, dateTo: null };
    case 'today': {
      const start = startOfLocalDay(referenceNow);
      const end = addDays(start, 1);
      return { dateFrom: start.toISOString(), dateTo: end.toISOString() };
    }
    case 'tomorrow': {
      const start = addDays(startOfLocalDay(referenceNow), 1);
      const end = addDays(start, 1);
      return { dateFrom: start.toISOString(), dateTo: end.toISOString() };
    }
    case 'weekend': {
      const today = startOfLocalDay(referenceNow);
      const dayOfWeek = today.getDay(); // 0=Sun..6=Sat
      const saturdayOffset = dayOfWeek === 6 ? 0 : dayOfWeek === 0 ? -1 : 6 - dayOfWeek;
      const saturday = addDays(today, saturdayOffset);
      const monday = addDays(saturday, 2);
      return { dateFrom: saturday.toISOString(), dateTo: monday.toISOString() };
    }
    case 'next7days': {
      const end = addDays(referenceNow, 7);
      return { dateFrom: referenceNow.toISOString(), dateTo: end.toISOString() };
    }
    default:
      return { dateFrom: null, dateTo: null };
  }
}

// ── Location / radius ─────────────────────────────────────────────────────────

export const RADIUS_OPTIONS_KM: ReadonlyArray<number> = [5, 10, 25, 50, 100];
export const DEFAULT_RADIUS_KM = 10;

// ── Active filter snapshot ─────────────────────────────────────────────────────

export interface ExploreActiveFilters {
  categories: BackendEventCategory[];
  datePreset: DatePreset;
  /** Frozen at Apply time — see computeDateBounds's doc comment. */
  dateBounds: DateBounds;
  nearMe: boolean;
  radiusKm: number;
  /** Frozen at Apply time; null unless nearMe was on with a resolved location. */
  location: { lat: number; lng: number } | null;
}

export const DEFAULT_EXPLORE_FILTERS: ExploreActiveFilters = {
  categories: [],
  datePreset: 'any',
  dateBounds: { dateFrom: null, dateTo: null },
  nearMe: false,
  radiusKm: DEFAULT_RADIUS_KM,
  location: null,
};

export function hasActiveFilters(filters: ExploreActiveFilters): boolean {
  return filters.categories.length > 0 || filters.datePreset !== 'any' || filters.nearMe;
}

/** Categories count as one group regardless of how many are selected. */
export function activeFilterGroupCount(filters: ExploreActiveFilters): number {
  return (
    (filters.categories.length > 0 ? 1 : 0) +
    (filters.datePreset !== 'any' ? 1 : 0) +
    (filters.nearMe ? 1 : 0)
  );
}
