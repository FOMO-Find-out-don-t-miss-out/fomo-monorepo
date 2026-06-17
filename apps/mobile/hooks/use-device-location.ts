import { useEffect, useState } from 'react';
import {
  DEFAULT_DISCOVERY_LAT,
  DEFAULT_DISCOVERY_LNG,
} from '../utils/location-config';

export type LocationStatus =
  | 'pending'    // permission not yet requested
  | 'granted'    // real device location available
  | 'denied'     // user refused; using defaults
  | 'unavailable'// location services off; using defaults
  | 'error';     // unexpected error; using defaults

export interface DeviceLocation {
  lat: number;
  lng: number;
  /** True when real location is unavailable and defaults are being used. */
  isDefault: boolean;
}

export interface UseDeviceLocationResult {
  location: DeviceLocation;
  status: LocationStatus;
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

  useEffect(() => {
    if (!ExpoLocation) {
      // Native module not available (Expo Go); fall back immediately.
      setStatus('unavailable');
      return;
    }

    let cancelled = false;

    async function request(): Promise<void> {
      try {
        const { status: perm } =
          await ExpoLocation!.requestForegroundPermissionsAsync();

        if (cancelled) return;

        if (perm !== 'granted') {
          setStatus('denied');
          return;
        }

        const pos = await ExpoLocation!.getCurrentPositionAsync({
          accuracy: ExpoLocation!.Accuracy.Balanced,
        });

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
  }, []);

  return { location, status };
}
