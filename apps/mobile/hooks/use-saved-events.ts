import { useCallback, useEffect, useState } from 'react';

import { apiEventToUiEvent } from '../utils/mappers';
import { fetchSavedEvents, removeEventRelationship } from '../utils/event-relationships-api';
import type { UiEvent } from '../types/ui';

export interface UseSavedEventsResult {
  events: UiEvent[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
  unsave: (eventId: string) => Promise<void>;
}

export function useSavedEvents(accessToken: string | null): UseSavedEventsResult {
  const [events, setEvents] = useState<UiEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!accessToken) {
      setEvents([]);
      setIsLoading(false);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchSavedEvents(accessToken)
      .then((raw) => {
        if (!cancelled) setEvents(raw.map(apiEventToUiEvent));
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load saved events');
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [accessToken, tick]);

  const refetch = useCallback(() => setTick((n) => n + 1), []);

  const unsave = useCallback(
    async (eventId: string) => {
      if (!accessToken) return;
      // Optimistic remove
      setEvents((prev) => prev.filter((e) => e.id !== eventId));
      try {
        await removeEventRelationship(eventId, 'saved', accessToken);
      } catch {
        // Rollback via refetch
        setTick((n) => n + 1);
      }
    },
    [accessToken],
  );

  return { events, isLoading, error, refetch, unsave };
}
