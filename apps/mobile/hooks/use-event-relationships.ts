import { useCallback, useEffect, useState } from 'react';

import { fetchEventIntents } from '../utils/event-relationships-api';
import { perfLog } from '../utils/performance-debug';
import type { EventIntent } from '../types/ui';

export function useEventRelationships(
  eventIds: string[],
  accessToken: string | null,
): {
  intents: Record<string, EventIntent>;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
} {
  const [intents, setIntents] = useState<Record<string, EventIntent>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  // Stable key avoids re-running the effect on every render when the array
  // reference changes but the contents are identical.
  const idsKey = eventIds.join(',');

  useEffect(() => {
    if (!accessToken || eventIds.length === 0) {
      setIntents({});
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    perfLog('intents-fetch', { phase: 'start', count: eventIds.length, tick });

    fetchEventIntents(eventIds, accessToken)
      .then((data) => {
        if (!cancelled) setIntents(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load intents');
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
    intents,
    isLoading,
    error,
    refetch: useCallback(() => setTick((n) => n + 1), []),
  };
}
