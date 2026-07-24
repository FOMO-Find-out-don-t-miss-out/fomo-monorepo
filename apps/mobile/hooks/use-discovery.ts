import { useEffect, useState } from 'react';

import { apiFetch } from '../utils/api-client';
import { apiEventToUiEvent } from '../utils/mappers';
import { perfLog } from '../utils/performance-debug';
import type { ApiEvent, UiEvent } from '../types/ui';

export interface DiscoveryParams {
  lat: number;
  lng: number;
  radiusKm?: number;
  /**
   * Gates the fetch — defaults to true. FOMO-176 passes false until initial
   * device-location resolution has settled, so Discover doesn't fire an
   * eager fetch against default coordinates that a real-location fetch would
   * immediately supersede (the original duplicate-request/stale-content-flash
   * cause). `loading` stays at its initial `true` while disabled, so the
   * existing loading UI covers the location-resolution wait with no change
   * in visible behavior.
   */
  enabled?: boolean;
}

export interface UseDiscoveryResult {
  events: UiEvent[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useDiscovery(params: DiscoveryParams): UseDiscoveryResult {
  const { enabled = true } = params;
  const [events, setEvents] = useState<UiEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    const radius = params.radiusKm ?? 10;
    const path = `/api/v1/events/discovery?lat=${params.lat}&lng=${params.lng}&radius_km=${radius}`;

    apiFetch<ApiEvent[]>(path)
      .then((raw) => {
        if (!cancelled) {
          perfLog('discover-events', { count: raw.length, tick });
          setEvents(raw.map(apiEventToUiEvent));
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unknown error');
          setEvents([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [params.lat, params.lng, params.radiusKm, tick, enabled]);

  return {
    events,
    loading,
    error,
    refetch: () => setTick((n) => n + 1),
  };
}
