import { useCallback, useEffect, useState } from 'react';

import { fetchEventRelationshipState, type RelationshipType } from '../utils/event-relationships-api';

export interface UseEventRelationshipsResult {
  relationships: Record<string, RelationshipType[]>;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Batch-fetches relationship state for the given event IDs.
 * Only runs when accessToken is available and eventIds is non-empty.
 * Re-fetches when eventIds or tick changes.
 */
export function useEventRelationships(
  eventIds: string[],
  accessToken: string | null,
): UseEventRelationshipsResult {
  const [relationships, setRelationships] = useState<Record<string, RelationshipType[]>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  // Join into a stable key so the effect doesn't fire on every render
  const idsKey = eventIds.join(',');

  useEffect(() => {
    if (!accessToken || eventIds.length === 0) {
      setRelationships({});
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchEventRelationshipState(eventIds, accessToken)
      .then((data) => {
        if (!cancelled) setRelationships(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load relationship state');
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey, accessToken, tick]);

  return {
    relationships,
    isLoading,
    error,
    refetch: useCallback(() => setTick((n) => n + 1), []),
  };
}
