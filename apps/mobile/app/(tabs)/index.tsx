import { CalendarView } from '../../components/fomo/calendar-view';
import { EventCard } from '../../components/fomo/event-card';
import { EventDetails } from '../../components/fomo/event-details';
import { FomoMap } from '../../components/fomo/fomo-map';
import { SearchBar } from '../../components/fomo/search-bar';
import { useDeviceLocation } from '../../hooks/use-device-location';
import { useDiscovery } from '../../hooks/use-discovery';
import { DEFAULT_DISCOVERY_RADIUS } from '../../utils/location-config';
import { haversineKm, formatDistanceKm, hasValidCoords } from '../../utils/geo';
import type { UiEvent } from '../../types/ui';
import { LocateFixed } from 'lucide-react-native';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  Dimensions,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

// ─── Constants ────────────────────────────────────────────────────────────────

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = 260;
const CARD_GAP   = 16;

// ─── Screen ───────────────────────────────────────────────────────────────────

export default function DiscoveryScreen() {
  const [selectedEvent, setSelectedEvent] = useState<UiEvent | null>(null);
  const [isCalendarView, setIsCalendarView] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [activeCategories, setActiveCategories] = useState<string[]>([]);

  const insets = useSafeAreaInsets();

  // Device location — falls back to env defaults when denied/unavailable.
  const { location, status: locationStatus, requestLocation } = useDeviceLocation();

  // locateMe triggers an animated fly-to in FomoMap; reset after animation starts.
  const [locateMe, setLocateMe] = useState(false);
  useEffect(() => {
    if (locateMe) {
      const t = setTimeout(() => setLocateMe(false), 600);
      return () => clearTimeout(t);
    }
  }, [locateMe]);

  // pendingLocate: the user tapped Locate Me while permission was not yet granted.
  // We defer the flyTo until the permission flow completes with 'granted'.
  // Clear on any terminal status so the spinner doesn't hang when denied again.
  const [pendingLocate, setPendingLocate] = useState(false);
  useEffect(() => {
    if (!pendingLocate) return;
    if (locationStatus === 'granted') {
      setPendingLocate(false);
      setLocateMe(true);
    } else if (locationStatus !== 'pending') {
      setPendingLocate(false);
    }
  }, [pendingLocate, locationStatus]);

  // Discovery fetches from the real API using device coords (or defaults).
  // Re-fetches automatically when location.lat/lng change (default → real).
  const { events, loading, error, refetch } = useDiscovery({
    lat: location.lat,
    lng: location.lng,
    radiusKm: DEFAULT_DISCOVERY_RADIUS,
  });

  // Attach computed distance to every event based on current origin.
  const eventsWithDistance = useMemo(
    () =>
      events.map((e) => ({
        ...e,
        distance: hasValidCoords(e.lat, e.lng)
          ? formatDistanceKm(
              haversineKm(location.lat, location.lng, e.lat!, e.lng!),
            )
          : undefined,
      })),
    [events, location.lat, location.lng],
  );

  // Client-side filter: text matches title or venue; categories match UiEventCategory (lowercase).
  const filteredEvents = useMemo(() => {
    let result = eventsWithDistance;
    const q = searchText.trim().toLowerCase();
    if (q) {
      result = result.filter(
        (e) =>
          e.title.toLowerCase().includes(q) ||
          e.venue.toLowerCase().includes(q),
      );
    }
    if (activeCategories.length > 0) {
      result = result.filter((e) =>
        activeCategories.includes(e.category.toLowerCase()),
      );
    }
    return result;
  }, [eventsWithDistance, searchText, activeCategories]);

  const handleFilterChange = useCallback((filters: string[]) => {
    setActiveCategories(filters);
  }, []);

  // Pin tap: find matching event and select it (syncs carousel + detail sheet).
  const handlePinPress = useCallback(
    (eventId: string) => {
      const found = eventsWithDistance.find((e) => e.id === eventId);
      if (found) setSelectedEvent(found);
    },
    [eventsWithDistance],
  );

  // Locate-me: fly to real device coords when already granted; otherwise request
  // permission and defer the flyTo until locationStatus transitions to 'granted'.
  function handleLocateMe() {
    setSelectedEvent(null);
    if (locationStatus === 'granted') {
      setLocateMe(true);
    } else {
      setPendingLocate(true);
      requestLocation();
    }
  }

  const carouselPadding = (SCREEN_WIDTH - CARD_WIDTH) / 2;

  // Fade in the carousel only when *returning* from Calendar view, not on initial mount.
  // On Android, useNativeDriver animations fail silently when the native view has not been
  // laid out yet. Setting opacity to 0 on mount leaves the carousel invisible until the
  // next effect cycle, which only triggers after a Calendar ↔ Map toggle.
  const carouselOpacity = useRef(new Animated.Value(1)).current;
  const prevCalendar = useRef(false);
  useEffect(() => {
    const wasCalendar = prevCalendar.current;
    prevCalendar.current = isCalendarView;

    if (!isCalendarView && wasCalendar) {
      carouselOpacity.setValue(0);
      Animated.timing(carouselOpacity, {
        toValue: 1,
        duration: 240,
        useNativeDriver: true,
      }).start();
    }
  }, [isCalendarView, carouselOpacity]);

  // ── Location status icon color for the locate button ─────────────────────
  const locateIconColor =
    locationStatus === 'granted'
      ? '#A855F7'
      : locationStatus === 'pending'
        ? 'rgba(255,255,255,0.5)'
        : 'rgba(255,255,255,0.3)';

  return (
    <View style={styles.screen}>

      {/* Layer 0: Mapbox map with real event pins */}
      <FomoMap
        centerLat={location.lat}
        centerLng={location.lng}
        events={eventsWithDistance}
        selectedEventId={selectedEvent?.id ?? null}
        showUserLocation={locationStatus === 'granted'}
        onPinPress={handlePinPress}
        locateMe={locateMe}
      />

      {/* Layer 1: SearchBar — text search + category chips + view toggle */}
      <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
        <SearchBar
          isCalendarView={isCalendarView}
          onViewToggle={() => setIsCalendarView((v) => !v)}
          onSearchChange={setSearchText}
          onFilterChange={handleFilterChange}
        />
      </View>

      {/* Layer 2: Locate-me button — top-right, below SearchBar (map view only) */}
      {!isCalendarView && (
        <Pressable
          style={[styles.locateBtn, { top: insets.top + 68 }]}
          onPress={handleLocateMe}
          hitSlop={8}
        >
          {locationStatus === 'pending' || pendingLocate ? (
            <ActivityIndicator size="small" color="rgba(255,255,255,0.5)" />
          ) : (
            <LocateFixed size={18} color={locateIconColor} strokeWidth={1.8} />
          )}
        </Pressable>
      )}

      {/* Location mode label — bottom-left above carousel; hidden while in-flight */}
      {!isCalendarView && locationStatus !== 'pending' && !pendingLocate && (
        <View style={styles.locationLabel}>
          <View
            style={[
              styles.locationDot,
              {
                backgroundColor:
                  locationStatus === 'granted'
                    ? '#A855F7'
                    : locationStatus === 'unavailable'
                      ? '#F97316'
                      : 'rgba(255,255,255,0.22)',
              },
            ]}
          />
          <Text style={styles.locationLabelText}>
            {locationStatus === 'granted'
              ? 'Your location'
              : locationStatus === 'denied'
                ? 'Location denied'
                : locationStatus === 'unavailable'
                  ? 'Location unavailable'
                  : 'Default location'}
          </Text>
        </View>
      )}

      {/* Layer 3a: Map-view carousel */}
      {!isCalendarView && (
        <Animated.View style={[styles.carouselAnchor, { opacity: carouselOpacity }]}>
          {loading ? (
            <View style={styles.feedbackContainer}>
              <ActivityIndicator color="#A855F7" size="small" />
            </View>
          ) : error ? (
            <View style={styles.feedbackContainer}>
              <Text style={styles.feedbackText}>Could not load events</Text>
              <Pressable onPress={refetch} style={styles.retryBtn}>
                <Text style={styles.retryText}>Retry</Text>
              </Pressable>
            </View>
          ) : filteredEvents.length === 0 ? (
            <View style={styles.feedbackContainer}>
              <Text style={styles.feedbackText}>
                {events.length === 0 ? 'No events nearby' : 'No events match your search'}
              </Text>
            </View>
          ) : (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              decelerationRate="fast"
              snapToInterval={CARD_WIDTH + CARD_GAP}
              snapToAlignment="center"
              contentContainerStyle={[
                styles.carouselContent,
                { paddingHorizontal: carouselPadding },
              ]}
            >
              {filteredEvents.map((event) => (
                <EventCard
                  key={event.id}
                  event={event}
                  isActive={selectedEvent?.id === event.id}
                  onPress={() => setSelectedEvent(event)}
                />
              ))}
            </ScrollView>
          )}
        </Animated.View>
      )}

      {/* Layer 3b: Calendar view */}
      {isCalendarView && (
        <CalendarView events={filteredEvents} onEventPress={setSelectedEvent} />
      )}

      {/* Layer 4: details modal */}
      <EventDetails
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
      />

    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#0B0B0F',
  },
  // Locate-me button — top-right map control; `top` is set inline via insets
  locateBtn: {
    position: 'absolute',
    right: 16,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(12, 12, 18, 0.85)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  },
  // Small pill showing whether real or default location is active
  locationLabel: {
    position: 'absolute',
    bottom: 116 + 200 + 8,
    left: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    backgroundColor: 'rgba(10, 10, 16, 0.70)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
  },
  locationDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  locationLabelText: {
    fontFamily: 'Inter_400Regular',
    fontSize: 10,
    color: 'rgba(255,255,255,0.45)',
    letterSpacing: 0.3,
  },
  carouselAnchor: {
    position: 'absolute',
    bottom: 116,
    left: 0,
    right: 0,
    height: 200,
  },
  carouselContent: {
    gap: CARD_GAP,
    alignItems: 'center',
  },
  feedbackContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  feedbackText: {
    color: 'rgba(255,255,255,0.35)',
    fontSize: 13,
    letterSpacing: 0.5,
    fontFamily: 'Inter_400Regular',
  },
  retryBtn: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(168, 85, 247, 0.4)',
  },
  retryText: {
    color: '#A855F7',
    fontSize: 12,
    fontFamily: 'Inter_600SemiBold',
  },
});
