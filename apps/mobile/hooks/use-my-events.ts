import { useCallback, useEffect, useRef, useState } from 'react';

import { fetchMyEvents, type RelationshipType } from '../utils/event-relationships-api';
import { apiEventToUiEvent } from '../utils/mappers';
import { perfLog } from '../utils/performance-debug';
import type { UiEvent } from '../types/ui';

export interface UseMyEventsResult {
  events: UiEvent[];
  /**
   * True only until this hook's first fetch (for the current identity) has
   * settled — success or failure. Never true again afterward, even during a
   * background refresh, so previously loaded rows stay visible (FOMO-178).
   * Drives the full-screen loading state.
   */
  isInitialLoading: boolean;
  /** True while a fetch is in flight after the initial load already settled. */
  isRefreshing: boolean;
  error: string | null;
  refetch: (reason?: string) => void;
  /**
   * Apply a locally-known result without a network round trip — used after a
   * My-Events-originated mutation, where the affected event is already fully
   * known (it's already rendered in one of the two lists) so no refetch is
   * needed (FOMO-178).
   */
  setEvents: React.Dispatch<React.SetStateAction<UiEvent[]>>;
}

export function useMyEvents(
  relationshipType: RelationshipType,
  accessToken: string | null,
): UseMyEventsResult {
  const [events, setEvents] = useState<UiEvent[]>([]);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const hasLoadedOnceRef = useRef(false);
  const explicitReasonRef = useRef<string | null>(null);
  const prevAccessTokenRef = useRef<string | null>(null);

  useEffect(() => {
    // A different, non-null access token than last render means the
    // authenticated identity changed — drop stale user-scoped rows
    // immediately rather than waiting for the next fetch to overwrite them
    // (mirrors the FOMO-177 fix for Discover's relationship state).
    if (prevAccessTokenRef.current !== null && accessToken !== prevAccessTokenRef.current) {
      setEvents([]);
      hasLoadedOnceRef.current = false;
      setIsInitialLoading(true);
    }
    prevAccessTokenRef.current = accessToken;

    if (!accessToken) {
      setEvents([]);
      setIsInitialLoading(true);
      setIsRefreshing(false);
      hasLoadedOnceRef.current = false;
      return;
    }

    let cancelled = false;
    const reason = explicitReasonRef.current ?? (hasLoadedOnceRef.current ? 'unknown' : 'initial');
    explicitReasonRef.current = null;

    if (hasLoadedOnceRef.current) {
      setIsRefreshing(true);
    } else {
      setIsInitialLoading(true);
    }
    setError(null);
    perfLog('my-events-fetch', { phase: 'start', type: relationshipType, tick, reason });

    fetchMyEvents(relationshipType, accessToken)
      .then((raw) => {
        if (cancelled) return;
        perfLog('my-events-fetch', {
          phase: 'done',
          type: relationshipType,
          count: raw.length,
          tick,
          reason,
        });
        setEvents(raw.map(apiEventToUiEvent));
        hasLoadedOnceRef.current = true;
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load events');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsInitialLoading(false);
          setIsRefreshing(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [accessToken, relationshipType, tick]);

  return {
    events,
    isInitialLoading,
    isRefreshing,
    error,
    refetch: useCallback((reason?: string) => {
      explicitReasonRef.current = reason ?? 'manual-refresh';
      setTick((n) => n + 1);
    }, []),
    setEvents,
  };
}
