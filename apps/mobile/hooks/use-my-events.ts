import { useCallback, useEffect, useState } from 'react';

import { fetchMyEvents, type RelationshipType } from '../utils/event-relationships-api';
import { apiEventToUiEvent } from '../utils/mappers';
import { perfLog } from '../utils/performance-debug';
import type { UiEvent } from '../types/ui';

export interface UseMyEventsResult {
  events: UiEvent[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useMyEvents(
  relationshipType: RelationshipType,
  accessToken: string | null,
): UseMyEventsResult {
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

    fetchMyEvents(relationshipType, accessToken)
      .then((raw) => {
        if (cancelled) return;
        perfLog('my-events-fetch', { type: relationshipType, count: raw.length, tick });
        setEvents(raw.map(apiEventToUiEvent));
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load events');
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [accessToken, relationshipType, tick]);

  const refetch = useCallback(() => setTick((n) => n + 1), []);

  return { events, isLoading, error, refetch };
}
