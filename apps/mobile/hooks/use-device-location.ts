import { useEffect, useState } from 'react';
import {
  DEFAULT_DISCOVERY_LAT,
  DEFAULT_DISCOVERY_LNG,
} from '../utils/location-config';
import { perfLog, perfMark, perfSince } from '../utils/performance-debug';

// Bounded wait for the initial permission prompt + GPS fix (FOMO-176) — long
// enough for a warm getLastKnownPositionAsync or a typical fresh fix, short
// enough that Discover never stalls indefinitely on location. If resolution
// hasn't settled by then, fall back to defaults; a later resolution (if it
// ever arrives) is ignored rather than triggering a second, surprise update.
const LOCATION_TIMEOUT_MS = 4000;

export type LocationStatus =
  | 'pending'     // permission request in flight
  | 'granted'     // real device location available
  | 'denied'      // user refused; using defaults
  | 'unavailable' // location services off or Expo Go; using defaults
  | 'error';      // unexpected error; using defaults

export interface DeviceLocation {
  lat: number;
  lng: number;
  /** True when real location is unavailable and defaults are being used. */
  isDefault: boolean;
}

export interface UseDeviceLocationResult {
  location: DeviceLocation;
  status: LocationStatus;
  /** Re-request location / permission — safe to call multiple times. */
  requestLocation: () => void;
}

const DEFAULT_LOCATION: DeviceLocation = {
  lat: DEFAULT_DISCOVERY_LAT,
  lng: DEFAULT_DISCOVERY_LNG,
  isDefault: true,
};

// Module-level require mirrors the pattern used in fomo-map.tsx so that
// the hook degrades gracefully in Expo Go (no native location module).
let ExpoLocation: typeof import('expo-location') | null = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  ExpoLocation = require('expo-location') as typeof import('expo-location');
} catch {
  ExpoLocation = null;
}

/**
 * @param enabled Gates the permission/location-resolution flow, mirroring the
 *   `enabled` param on useDiscovery (FOMO-176). Defaults to true, preserving
 *   Discover's existing unconditional-on-mount behavior exactly. Callers that
 *   want location only after an explicit opt-in (e.g. Explore's "Near me"
 *   toggle, FOMO-172 Phase 4A) pass `enabled: false` until that opt-in
 *   happens — this avoids requesting permission before the user has asked
 *   for location-based search, without duplicating a second, independent
 *   location hook/state.
 */
export function useDeviceLocation(enabled: boolean = true): UseDeviceLocationResult {
  const [status, setStatus] = useState<LocationStatus>('pending');
  const [location, setLocation] = useState<DeviceLocation>(DEFAULT_LOCATION);
  // Incrementing this re-runs the location effect (used by requestLocation).
  const [triggerCount, setTriggerCount] = useState(0);

  useEffect(() => {
    if (!enabled) {
      // Not opted in yet — do not request permission or resolve location.
      return;
    }
    if (!ExpoLocation) {
      // Native module not available (Expo Go); fall back immediately.
      setStatus('unavailable');
      return;
    }

    let cancelled = false;
    let settled = false;
    setStatus('pending');
    const mark = perfMark();

    function settle(status: LocationStatus, outcome: string): void {
      settled = true;
      setStatus(status);
      perfLog('location-resolve', { outcome, duration_ms: perfSince(mark) });
    }

    async function request(): Promise<void> {
      try {
        const { status: perm } =
          await ExpoLocation!.requestForegroundPermissionsAsync();

        if (cancelled) return;

        if (perm !== 'granted') {
          settle('denied', 'denied');
          return;
        }

        // getLastKnownPositionAsync is instant (OS cache from any app).
        // Falls back to a fresh reading only when the cache is empty.
        // This prevents the common failure where getCurrentPositionAsync
        // times out right after a fresh permission grant before GPS warms up.
        const lastPos = await ExpoLocation!.getLastKnownPositionAsync({});
        const pos =
          lastPos ??
          (await ExpoLocation!.getCurrentPositionAsync({
            accuracy: ExpoLocation!.Accuracy.Balanced,
          }));

        if (!cancelled) {
          setLocation({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
            isDefault: false,
          });
          settle('granted', 'granted');
        }
      } catch {
        if (!cancelled) settle('error', 'error');
        // location stays at DEFAULT_LOCATION
      }
    }

    request();

    // See LOCATION_TIMEOUT_MS above — bounds the pending phase so Discover's
    // deferred initial fetch (FOMO-176) never waits indefinitely.
    const timeoutId = setTimeout(() => {
      if (!settled) {
        cancelled = true;
        settle('unavailable', 'timeout');
      }
    }, LOCATION_TIMEOUT_MS);

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  // triggerCount drives both the initial run and any manual retriggers.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [triggerCount, enabled]);

  return {
    location,
    status,
    // useState setters are stable references — this inline fn is safe to use as a handler.
    requestLocation: () => setTriggerCount((n) => n + 1),
  };
}
