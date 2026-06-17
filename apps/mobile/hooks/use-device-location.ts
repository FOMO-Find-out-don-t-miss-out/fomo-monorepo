import { useEffect, useState } from 'react';
import {
  DEFAULT_DISCOVERY_LAT,
  DEFAULT_DISCOVERY_LNG,
} from '../utils/location-config';

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

export function useDeviceLocation(): UseDeviceLocationResult {
  const [status, setStatus] = useState<LocationStatus>('pending');
  const [location, setLocation] = useState<DeviceLocation>(DEFAULT_LOCATION);
  // Incrementing this re-runs the location effect (used by requestLocation).
  const [triggerCount, setTriggerCount] = useState(0);

  useEffect(() => {
    if (!ExpoLocation) {
      // Native module not available (Expo Go); fall back immediately.
      setStatus('unavailable');
      return;
    }

    let cancelled = false;
    setStatus('pending');

    async function request(): Promise<void> {
      try {
        const { status: perm } =
          await ExpoLocation!.requestForegroundPermissionsAsync();

        if (cancelled) return;

        if (perm !== 'granted') {
          setStatus('denied');
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
          setStatus('granted');
        }
      } catch {
        if (!cancelled) setStatus('error');
        // location stays at DEFAULT_LOCATION
      }
    }

    request();
    return () => {
      cancelled = true;
    };
  // triggerCount drives both the initial run and any manual retriggers.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [triggerCount]);

  return {
    location,
    status,
    // useState setters are stable references — this inline fn is safe to use as a handler.
    requestLocation: () => setTriggerCount((n) => n + 1),
  };
}
