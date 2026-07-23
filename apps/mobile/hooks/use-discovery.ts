import { useEffect, useState } from 'react';

import { apiFetch } from '../utils/api-client';
import { apiEventToUiEvent } from '../utils/mappers';
import { perfLog } from '../utils/performance-debug';
import type { ApiEvent, UiEvent } from '../types/ui';

export interface DiscoveryParams {
  lat: number;
  lng: number;
  radiusKm?: number;
}

export interface UseDiscoveryResult {
  events: UiEvent[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useDiscovery(params: DiscoveryParams): UseDiscoveryResult {
  const [events, setEvents] = useState<UiEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
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
  }, [params.lat, params.lng, params.radiusKm, tick]);

  return {
    events,
    loading,
    error,
    refetch: () => setTick((n) => n + 1),
  };
}
