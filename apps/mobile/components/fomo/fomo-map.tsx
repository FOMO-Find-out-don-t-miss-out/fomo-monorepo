import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

// Runtime pk.* token. Mirrors `MAPBOX_ACCESS_TOKEN` from apps/api/.env and
// must be re-declared in apps/mobile with the `EXPO_PUBLIC_` prefix so Metro
// inlines it into the client bundle. The sk.* download token required for
// native builds belongs in EAS secrets, not here.
const ACCESS_TOKEN =
  (globalThis as { process?: { env?: Record<string, string | undefined> } })
    .process?.env?.EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN ?? '';

const DARK_STYLE_URL = 'mapbox://styles/mapbox/dark-v11';
// Placeholder centering — swap for device location once permissions flow lands.
const DEFAULT_CENTER: [number, number] = [-73.9857, 40.7484]; // NYC
const DEFAULT_ZOOM = 12;

// ─── Lazy native-module load ─────────────────────────────────────────────────
// `@rnmapbox/maps` ships native code; importing it in Expo Go throws at
// module eval. We swallow that here so the rest of the screen still boots,
// and render a dark placeholder until a dev client is built.

type MaybeComponent = React.ComponentType<Record<string, unknown>> | null;

let MapViewComp: MaybeComponent = null;
let CameraComp: MaybeComponent = null;
let nativeAvailable = false;

try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const mod = require('@rnmapbox/maps');
  const Mapbox = mod.default ?? mod;
  MapViewComp = (mod.MapView ?? Mapbox.MapView) as MaybeComponent;
  CameraComp = (mod.Camera ?? Mapbox.Camera) as MaybeComponent;
  nativeAvailable = typeof MapViewComp === 'function' || typeof MapViewComp === 'object';
  if (nativeAvailable && ACCESS_TOKEN) {
    Mapbox.setAccessToken(ACCESS_TOKEN);
  }
} catch {
  nativeAvailable = false;
}

// ─── Component ───────────────────────────────────────────────────────────────

export function FomoMap() {
  if (!nativeAvailable || !MapViewComp || !CameraComp) {
    return (
      <View style={[styles.container, styles.fallback]}>
        <Text style={styles.fallbackText}>Map preview requires a dev client build</Text>
      </View>
    );
  }

  const MapView = MapViewComp;
  const Camera = CameraComp;

  return (
    <View style={styles.container}>
      <MapView
        style={styles.map}
        styleURL={DARK_STYLE_URL}
        logoEnabled={false}
        attributionEnabled={false}
        compassEnabled={false}
        scaleBarEnabled={false}
        rotateEnabled={false}
        pitchEnabled={false}
      >
        <Camera
          zoomLevel={DEFAULT_ZOOM}
          centerCoordinate={DEFAULT_CENTER}
          animationMode="none"
        />
      </MapView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 0,
    backgroundColor: '#0B0B0F',
  },
  map: {
    flex: 1,
  },
  fallback: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  fallbackText: {
    color: 'rgba(255, 255, 255, 0.25)',
    fontSize: 11,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
});
