import { useCallback, useEffect, useRef, useState } from 'react';

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
  refetch: (reason?: string) => void;
} {
  const [intents, setIntents] = useState<Record<string, EventIntent>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  // Canonical signature for the loaded event-ID SET (sorted, not just
  // joined) — an identical set in a different array order must not look
  // like a change (FOMO-177).
  const idsKey = [...eventIds].sort().join(',');

  // Reason bookkeeping (FOMO-177 — see requirement to tag each fetch):
  // idsKey/accessToken transitions are classified automatically; explicit
  // refetch() calls carry their own reason.
  const explicitReasonRef = useRef<string | null>(null);
  const hasFetchedOnceRef = useRef(false);
  const prevIdsKeyRef = useRef<string | null>(null);
  const prevAccessTokenRef = useRef<string | null>(null);

  useEffect(() => {
    // A different, non-null access token than last render means the
    // authenticated identity changed (sign-out then sign back in as a
    // different user) — the same events can carry a different user's
    // relationships, so drop stale state immediately rather than waiting
    // for the next fetch to overwrite it.
    if (prevAccessTokenRef.current !== null && accessToken !== prevAccessTokenRef.current) {
      setIntents({});
      hasFetchedOnceRef.current = false;
      prevIdsKeyRef.current = null;
    }
    prevAccessTokenRef.current = accessToken;

    if (!accessToken || eventIds.length === 0) {
      setIntents({});
      hasFetchedOnceRef.current = false;
      prevIdsKeyRef.current = null;
      return;
    }

    const reason =
      explicitReasonRef.current ??
      (!hasFetchedOnceRef.current
        ? 'initial'
        : idsKey !== prevIdsKeyRef.current
          ? 'event-set-changed'
          : 'unknown');
    explicitReasonRef.current = null;
    hasFetchedOnceRef.current = true;
    prevIdsKeyRef.current = idsKey;

    let cancelled = false;
    setIsLoading(true);
    setError(null);
    perfLog('intents-fetch', { phase: 'start', count: eventIds.length, tick, reason });

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
    refetch: useCallback((reason?: string) => {
      explicitReasonRef.current = reason ?? 'manual-refresh';
      setTick((n) => n + 1);
    }, []),
  };
}
