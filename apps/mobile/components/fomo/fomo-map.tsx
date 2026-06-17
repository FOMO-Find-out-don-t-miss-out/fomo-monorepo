import { DEFAULT_DISCOVERY_LAT, DEFAULT_DISCOVERY_LNG } from '../../utils/location-config';
import { hasValidCoords } from '../../utils/geo';
import type { UiEvent } from '../../types/ui';
import React, { useMemo } from 'react';
import { StyleSheet, Text, View } from 'react-native';

const ACCESS_TOKEN =
  (globalThis as { process?: { env?: Record<string, string | undefined> } })
    .process?.env?.EXPO_PUBLIC_MAPBOX_TOKEN ?? '';

const DARK_STYLE_URL = 'mapbox://styles/mapbox/dark-v11';
const DEFAULT_ZOOM = 12;
const SELECTED_ZOOM = 14;

type MaybeComponent = React.ComponentType<Record<string, unknown>> | null;

let MapViewComp: MaybeComponent = null;
let CameraComp: MaybeComponent = null;
let ShapeSourceComp: MaybeComponent = null;
let CircleLayerComp: MaybeComponent = null;
let UserLocationComp: MaybeComponent = null;
let nativeAvailable = false;

try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const mod = require('@rnmapbox/maps');
  const Mapbox = mod.default ?? mod;
  MapViewComp       = (mod.MapView       ?? Mapbox.MapView)       as MaybeComponent;
  CameraComp        = (mod.Camera        ?? Mapbox.Camera)        as MaybeComponent;
  ShapeSourceComp   = (mod.ShapeSource   ?? Mapbox.ShapeSource)   as MaybeComponent;
  CircleLayerComp   = (mod.CircleLayer   ?? Mapbox.CircleLayer)   as MaybeComponent;
  UserLocationComp  = (mod.UserLocation  ?? Mapbox.UserLocation)  as MaybeComponent;
  nativeAvailable   = typeof MapViewComp === 'function' || typeof MapViewComp === 'object';
  if (nativeAvailable && ACCESS_TOKEN) {
    Mapbox.setAccessToken(ACCESS_TOKEN);
  }
} catch {
  nativeAvailable = false;
}

// ─── Minimal GeoJSON types (avoids @types/geojson dependency) ─────────────────

type PointFeature = {
  type: 'Feature';
  id: string;
  geometry: { type: 'Point'; coordinates: [number, number] };
  properties: Record<string, unknown>;
};

type FeatureCollection = {
  type: 'FeatureCollection';
  features: PointFeature[];
};

function buildGeoJSON(events: UiEvent[]): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: events
      .filter((e) => hasValidCoords(e.lat, e.lng))
      .map((e) => ({
        type: 'Feature',
        id: e.id,
        geometry: { type: 'Point', coordinates: [e.lng!, e.lat!] },
        properties: { id: e.id },
      })),
  };
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface FomoMapProps {
  centerLat?: number;
  centerLng?: number;
  /** Events to render as map pins. Only those with valid coords get a pin. */
  events?: UiEvent[];
  /** ID of the currently selected event; that pin is highlighted and camera follows it. */
  selectedEventId?: string | null;
  /** Show the native user-location dot (only when location permission is granted). */
  showUserLocation?: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function FomoMap({
  centerLat,
  centerLng,
  events = [],
  selectedEventId,
  showUserLocation = false,
}: FomoMapProps = {}) {
  const defaultCenter: [number, number] = [
    centerLng ?? DEFAULT_DISCOVERY_LNG,
    centerLat ?? DEFAULT_DISCOVERY_LAT,
  ];

  // When a card is selected, pan to that event; otherwise stay at discovery origin.
  const selectedEvent = selectedEventId
    ? events.find((e) => e.id === selectedEventId) ?? null
    : null;

  const cameraCenter: [number, number] =
    selectedEvent && hasValidCoords(selectedEvent.lat, selectedEvent.lng)
      ? [selectedEvent.lng!, selectedEvent.lat!]
      : defaultCenter;

  const cameraZoom = selectedEvent ? SELECTED_ZOOM : DEFAULT_ZOOM;

  // GeoJSON for all event pins (excluding invalid coords).
  const allGeojson = useMemo(() => buildGeoJSON(events), [events]);

  // GeoJSON for the highlighted selected-event pin (rendered on top layer).
  const selectedGeojson = useMemo((): FeatureCollection => {
    if (!selectedEvent || !hasValidCoords(selectedEvent.lat, selectedEvent.lng)) {
      return { type: 'FeatureCollection', features: [] };
    }
    return {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          id: selectedEvent.id,
          geometry: {
            type: 'Point',
            coordinates: [selectedEvent.lng!, selectedEvent.lat!],
          },
          properties: { id: selectedEvent.id },
        },
      ],
    };
  }, [selectedEvent]);

  // ── Expo Go / no native module fallback ──────────────────────────────────

  if (!nativeAvailable || !MapViewComp || !CameraComp) {
    return (
      <View style={[styles.container, styles.fallback]}>
        <Text style={styles.fallbackText}>Map preview requires a dev client build</Text>
      </View>
    );
  }

  const MapView      = MapViewComp;
  const Camera       = CameraComp;
  const ShapeSource  = ShapeSourceComp;
  const CircleLayer  = CircleLayerComp;
  const UserLocation = UserLocationComp;

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
        {/* Camera — snaps on initial/origin changes, animates on event selection */}
        <Camera
          zoomLevel={cameraZoom}
          centerCoordinate={cameraCenter}
          animationMode={selectedEvent ? 'easeTo' : 'none'}
          animationDuration={selectedEvent ? 400 : 0}
        />

        {/* User location blue dot — only shown when permission granted */}
        {UserLocation && showUserLocation && (
          <UserLocation visible={true} />
        )}

        {/* All event pins: small purple circles */}
        {ShapeSource && CircleLayer && (
          <ShapeSource
            id="fomo-events-source"
            shape={allGeojson as unknown as Record<string, unknown>}
          >
            <CircleLayer
              id="fomo-events-circles"
              style={{
                circleRadius: 6,
                circleColor: '#A855F7',
                circleStrokeWidth: 1.5,
                circleStrokeColor: '#ffffff',
                circleOpacity: 0.85,
              }}
            />
          </ShapeSource>
        )}

        {/* Selected-event pin: larger magenta circle on top */}
        {ShapeSource && CircleLayer && (
          <ShapeSource
            id="fomo-selected-source"
            shape={selectedGeojson as unknown as Record<string, unknown>}
          >
            <CircleLayer
              id="fomo-selected-circle"
              style={{
                circleRadius: 10,
                circleColor: '#BC13FE',
                circleStrokeWidth: 2,
                circleStrokeColor: '#ffffff',
                circleOpacity: 1,
              }}
            />
          </ShapeSource>
        )}
      </MapView>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

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
