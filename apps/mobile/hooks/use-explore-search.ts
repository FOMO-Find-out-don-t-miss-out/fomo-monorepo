import { useCallback, useEffect, useRef, useState } from 'react';

import { apiFetch } from '../utils/api-client';
import { apiEventToUiEvent } from '../utils/mappers';
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

export interface UseExploreSearchResult {
  /** Exactly what the user typed — never mutated/trimmed for display. */
  query: string;
  setQuery: (text: string) => void;
  status: ExploreSearchStatus;
  events: UiEvent[];
  error: string | null;
  hasMore: boolean;
  loadingMore: boolean;
  loadMore: () => void;
  retry: () => void;
}

type FetchMode = 'replace' | 'append';

export function useExploreSearch(): UseExploreSearchResult {
  const [query, setQueryState] = useState('');
  const [normalizedQuery, setNormalizedQuery] = useState<string | null>(null);
  const [tooShort, setTooShort] = useState(false);

  const [events, setEvents] = useState<UiEvent[]>([]);
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

  // Monotonic generation counter: every new fetch (a new query's first page,
  // a retry, or a load-more page) increments this before the request starts.
  // A response is only applied if it's still the latest generation when it
  // resolves — supersedes a slower older response and guarantees a stale
  // previous-query page can never append to the current query's results.
  // Mirrors the sessionGenerationRef pattern in providers/auth-provider.tsx.
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
    async (searchQuery: string, offset: number, mode: FetchMode) => {
      const myGeneration = ++generationRef.current;
      if (mode === 'replace') {
        setLoading(true);
        setError(null);
      } else {
        setLoadingMore(true);
      }

      const stillCurrent = () => mountedRef.current && generationRef.current === myGeneration;

      try {
        const path =
          `/api/v1/events/search?q=${encodeURIComponent(searchQuery)}` +
          `&limit=${SEARCH_LIMIT}&offset=${offset}`;
        const data = await apiFetch<EventSearchResponse>(path);
        if (!stillCurrent()) return; // superseded or unmounted

        const mapped = data.results.map(apiEventToUiEvent);
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

  // Fire the first page whenever the settled, normalized query changes.
  useEffect(() => {
    if (normalizedQuery === null) {
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
    fetchPage(normalizedQuery, 0, 'replace');
  }, [normalizedQuery, fetchPage]);

  const loadMore = useCallback(() => {
    if (normalizedQuery === null) return;
    // Never load more while the first page is still loading, and never run
    // two load-more requests concurrently.
    if (loading || loadingMore || !hasMore) return;
    fetchPage(normalizedQuery, events.length, 'append');
  }, [normalizedQuery, loading, loadingMore, hasMore, events.length, fetchPage]);

  const retry = useCallback(() => {
    if (normalizedQuery === null) return;
    setEvents([]);
    setHasMore(false);
    fetchPage(normalizedQuery, 0, 'replace');
  }, [normalizedQuery, fetchPage]);

  const status: ExploreSearchStatus =
    normalizedQuery === null
      ? tooShort
        ? 'too-short'
        : 'idle'
      : loading
        ? 'loading'
        : error
          ? 'error'
          : events.length === 0
            ? 'empty'
            : 'results';

  return { query, setQuery, status, events, error, hasMore, loadingMore, loadMore, retry };
}
