import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { apiFetch } from '../utils/api-client';
import { apiEventToUiEvent } from '../utils/mappers';
import {
  DEFAULT_EXPLORE_FILTERS,
  hasActiveFilters,
  type ExploreActiveFilters,
} from '../utils/explore-filters';
import type { components } from '../types/api.generated';
import type { UiEvent } from '../types/ui';

type EventSearchResponse = components['schemas']['EventSearchResponse'];

const SEARCH_LIMIT = 20;
const MIN_QUERY_LENGTH = 2;
const DEBOUNCE_MS = 380;

export type ExploreSearchStatus =
  | 'idle'
  | 'too-short'
  | 'loading'
  | 'results'
  | 'empty'
  | 'error';

/**
 * A UiEvent plus the untranslated backend category value, so the screen can
 * show the true backend-aligned category label on the result card without
 * the shared apiEventToUiEvent mapper (used by Discover too) ever needing to
 * change — see event-card.tsx's `categoryLabel` prop doc comment.
 */
export interface ExploreEvent extends UiEvent {
  rawCategory: string;
}

export interface UseExploreSearchResult {
  /** Exactly what the user typed — never mutated/trimmed for display. */
  query: string;
  setQuery: (text: string) => void;
  activeFilters: ExploreActiveFilters;
  /** Replaces the active filter snapshot and starts a fresh, offset-0 search. */
  applyFilters: (next: ExploreActiveFilters) => void;
  status: ExploreSearchStatus;
  events: ExploreEvent[];
  error: string | null;
  hasMore: boolean;
  loadingMore: boolean;
  loadMore: () => void;
  retry: () => void;
}

type FetchMode = 'replace' | 'append';

function buildSearchPath(
  searchQuery: string | null,
  filters: ExploreActiveFilters,
  limit: number,
  offset: number,
): string {
  const params = new URLSearchParams();
  if (searchQuery) params.append('q', searchQuery);
  for (const category of filters.categories) params.append('category', category);
  if (filters.dateBounds.dateFrom) params.append('date_from', filters.dateBounds.dateFrom);
  if (filters.dateBounds.dateTo) params.append('date_to', filters.dateBounds.dateTo);
  if (filters.nearMe && filters.location) {
    params.append('lat', String(filters.location.lat));
    params.append('lng', String(filters.location.lng));
    params.append('radius_km', String(filters.radiusKm));
  }
  params.append('limit', String(limit));
  params.append('offset', String(offset));
  return `/api/v1/events/search?${params.toString()}`;
}

export function useExploreSearch(): UseExploreSearchResult {
  const [query, setQueryState] = useState('');
  const [normalizedQuery, setNormalizedQuery] = useState<string | null>(null);
  const [tooShort, setTooShort] = useState(false);
  const [activeFilters, setActiveFilters] = useState<ExploreActiveFilters>(
    DEFAULT_EXPLORE_FILTERS,
  );

  const [events, setEvents] = useState<ExploreEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);

  // True until unmount. A response resolving after unmount must never call a
  // state setter — mirrors the `cancelled` flag already used for this exact
  // purpose in use-discovery.ts / use-event-relationships.ts.
  const mountedRef = useRef(true);
  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Monotonic generation counter: every new fetch (a new identity's first
  // page, a retry, or a load-more page) increments this before the request
  // starts. A response is only applied if it's still the latest generation
  // when it resolves — supersedes a slower older response and guarantees a
  // stale previous-identity page can never append to the current identity's
  // results. Mirrors the sessionGenerationRef pattern in
  // providers/auth-provider.tsx.
  const generationRef = useRef(0);

  // Wraps the raw setter so every keystroke (including clearing) invalidates
  // any in-flight request immediately — not just once the debounce settles.
  // Without this, a slow response for the pre-edit query could still land
  // and populate results during the ~380ms debounce window after the user
  // has already changed or cleared the input.
  const setQuery = useCallback((text: string) => {
    generationRef.current += 1;
    setQueryState(text);
  }, []);

  // Applying a new filter snapshot has no debounce window to worry about
  // (unlike the text query), but invalidating in-flight requests immediately
  // here too keeps both mutation paths consistent and defensive.
  const applyFilters = useCallback((next: ExploreActiveFilters) => {
    generationRef.current += 1;
    setActiveFilters(next);
  }, []);

  // Debounce: settle the raw `query` into a normalized value ~380ms after the
  // user stops typing. This effect only decides *whether/what* to search —
  // it never writes back into `query`, so the visible input always reflects
  // exactly what the user typed.
  useEffect(() => {
    const handle = setTimeout(() => {
      const trimmed = query.trim();
      if (trimmed.length === 0) {
        setNormalizedQuery(null);
        setTooShort(false);
      } else if (trimmed.length < MIN_QUERY_LENGTH) {
        setNormalizedQuery(null);
        setTooShort(true);
      } else {
        setTooShort(false);
        setNormalizedQuery(trimmed);
      }
    }, DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [query]);

  const fetchPage = useCallback(
    async (
      searchQuery: string | null,
      filters: ExploreActiveFilters,
      offset: number,
      mode: FetchMode,
    ) => {
      const myGeneration = ++generationRef.current;
      if (mode === 'replace') {
        setLoading(true);
        setError(null);
      } else {
        setLoadingMore(true);
      }

      const stillCurrent = () => mountedRef.current && generationRef.current === myGeneration;

      try {
        const path = buildSearchPath(searchQuery, filters, SEARCH_LIMIT, offset);
        const data = await apiFetch<EventSearchResponse>(path);
        if (!stillCurrent()) return; // superseded or unmounted

        const mapped: ExploreEvent[] = data.results.map((raw) => ({
          ...apiEventToUiEvent(raw),
          rawCategory: raw.category,
        }));
        setEvents((prev) => {
          if (mode === 'replace') return mapped;
          // Defensive de-dup: never append an id already present.
          const seen = new Set(prev.map((e) => e.id));
          return [...prev, ...mapped.filter((e) => !seen.has(e.id))];
        });
        setHasMore(data.has_more);
      } catch (err) {
        if (!stillCurrent()) return; // superseded or unmounted
        if (mode === 'replace') {
          // Only a first-page/retry failure becomes the full-screen error
          // state — a failed load-more silently stops and leaves existing
          // results + hasMore in place so the next scroll-to-bottom retries.
          setError(err instanceof Error ? err.message : 'Search failed');
          setEvents([]);
          setHasMore(false);
        }
      } finally {
        if (mountedRef.current && generationRef.current === myGeneration) {
          setLoading(false);
          setLoadingMore(false);
        }
      }
    },
    [],
  );

  // A too-short query blocks everything, even with active filters — it must
  // never be silently ignored in favor of a filter-only search. Otherwise,
  // an empty/absent query is fine as long as at least one filter is active.
  const eligible = !tooShort && (normalizedQuery !== null || hasActiveFilters(activeFilters));

  // Deterministic identity for "what should the current results be". Two
  // renders with the same normalizedQuery + activeFilters content produce the
  // same key, so this only changes when the actual search identity changes —
  // used as the sole effect dependency below instead of listing
  // normalizedQuery/activeFilters directly (object/array equality would
  // otherwise retrigger on every unrelated render).
  const identityKey = useMemo(
    () => JSON.stringify({ q: normalizedQuery, f: activeFilters }),
    [normalizedQuery, activeFilters],
  );

  // Fire the first page whenever the search identity (query + filters)
  // settles into a new, eligible combination.
  useEffect(() => {
    if (!eligible) {
      generationRef.current += 1; // supersede any in-flight request
      setEvents([]);
      setHasMore(false);
      setLoading(false);
      setLoadingMore(false);
      setError(null);
      return;
    }
    setEvents([]);
    setHasMore(false);
    fetchPage(normalizedQuery, activeFilters, 0, 'replace');
    // identityKey deterministically captures {normalizedQuery, activeFilters};
    // eligible is derived from the same two values plus tooShort.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [identityKey, eligible, fetchPage]);

  const loadMore = useCallback(() => {
    if (!eligible) return;
    // Never load more while the first page is still loading, and never run
    // two load-more requests concurrently.
    if (loading || loadingMore || !hasMore) return;
    fetchPage(normalizedQuery, activeFilters, events.length, 'append');
  }, [eligible, normalizedQuery, activeFilters, loading, loadingMore, hasMore, events.length, fetchPage]);

  const retry = useCallback(() => {
    if (!eligible) return;
    setEvents([]);
    setHasMore(false);
    fetchPage(normalizedQuery, activeFilters, 0, 'replace');
  }, [eligible, normalizedQuery, activeFilters, fetchPage]);

  const status: ExploreSearchStatus = tooShort
    ? 'too-short'
    : !eligible
      ? 'idle'
      : loading
        ? 'loading'
        : error
          ? 'error'
          : events.length === 0
            ? 'empty'
            : 'results';

  return {
    query,
    setQuery,
    activeFilters,
    applyFilters,
    status,
    events,
    error,
    hasMore,
    loadingMore,
    loadMore,
    retry,
  };
}
