import { useCallback, useEffect, useState } from 'react';

import {
  fetchEventRelationshipState,
  fetchMyEvents,
} from '../utils/event-relationships-api';
import type { RelationshipType } from '../utils/event-relationships-api';
import { apiEventToUiEvent } from '../utils/mappers';
import type { UiEvent } from '../types/ui';

export interface UseMyEventsResult {
  events: UiEvent[];
  /** Full relationship state for every loaded event, keyed by event id. */
  relationships: Record<string, RelationshipType[]>;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Fetches the current user's events for a given relationship type, then
 * batch-fetches the full relationship state for those events so the detail
 * sheet can show all active relationship types (not just the tab's type).
 *
 * Call refetch() on screen focus to keep the list fresh after mutations
 * in other screens (e.g. saving from Discover).
 */
export function useMyEvents(
  relationshipType: RelationshipType,
  accessToken: string | null,
): UseMyEventsResult {
  const [events, setEvents] = useState<UiEvent[]>([]);
  const [relationships, setRelationships] = useState<Record<string, RelationshipType[]>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  // Primary fetch: events by relationship type
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

        // Secondary fetch: full relationship state for these event ids.
        // Runs inside the same cancelled-scope so we don't update state
        // after the component unmounts or the effect re-runs.
        const ids = uiEvents.map((e) => e.id);
        if (ids.length === 0) {
          setRelationships({});
          return;
        }
        return fetchEventRelationshipState(ids, accessToken).then((rels) => {
          if (!cancelled) setRelationships(rels);
        });
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
