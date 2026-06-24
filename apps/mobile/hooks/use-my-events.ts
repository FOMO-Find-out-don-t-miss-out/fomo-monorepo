import { useCallback, useEffect, useState } from 'react';

import { fetchMyEvents } from '../utils/event-relationships-api';
import type { RelationshipType } from '../utils/event-relationships-api';
import { apiEventToUiEvent } from '../utils/mappers';
import type { UiEvent } from '../types/ui';

export interface UseMyEventsResult {
  events: UiEvent[];
  /**
   * Seed data for useRelationshipState.syncFromServer.
   * All returned events have intent = the requested relationship type.
   * No secondary batch fetch is needed because the backend list endpoint
   * already guarantees this invariant.
   */
  relationships: Record<string, RelationshipType[]>;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useMyEvents(
  relationshipType: RelationshipType,
  accessToken: string | null,
): UseMyEventsResult {
  const [events, setEvents] = useState<UiEvent[]>([]);
  const [relationships, setRelationships] = useState<Record<string, RelationshipType[]>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!accessToken) {
      setEvents([]);
      setRelationships({});
      setIsLoading(false);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchMyEvents(relationshipType, accessToken)
      .then((raw) => {
        if (cancelled) return;
        const uiEvents = raw.map(apiEventToUiEvent);
        setEvents(uiEvents);

        // Seed intent directly from the tab type — every event returned here
        // has exactly this relationship type (backend exclusivity guarantees it).
        const seeds: Record<string, RelationshipType[]> = {};
        for (const e of uiEvents) {
          seeds[e.id] = [relationshipType];
        }
        setRelationships(seeds);
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

  return { events, relationships, isLoading, error, refetch };
}
