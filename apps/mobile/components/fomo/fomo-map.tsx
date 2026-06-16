import { DEFAULT_DISCOVERY_LAT, DEFAULT_DISCOVERY_LNG } from '../../utils/location-config';
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

const ACCESS_TOKEN =
  (globalThis as { process?: { env?: Record<string, string | undefined> } })
    .process?.env?.EXPO_PUBLIC_MAPBOX_TOKEN ?? '';

const DARK_STYLE_URL = 'mapbox://styles/mapbox/dark-v11';
const DEFAULT_ZOOM = 12;

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

interface FomoMapProps {
  centerLat?: number;
  centerLng?: number;
}

export function FomoMap({ centerLat, centerLng }: FomoMapProps = {}) {
  const center: [number, number] = [
    centerLng ?? DEFAULT_DISCOVERY_LNG,
    centerLat ?? DEFAULT_DISCOVERY_LAT,
  ];

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
          centerCoordinate={center}
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
