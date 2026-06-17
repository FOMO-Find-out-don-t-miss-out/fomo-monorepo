import { CalendarView } from '../../components/fomo/calendar-view';
import { EventCard } from '../../components/fomo/event-card';
import { EventDetails } from '../../components/fomo/event-details';
import { FomoMap } from '../../components/fomo/fomo-map';
import { NeonGrid } from '../../components/fomo/neon-grid';
import { SearchBar } from '../../components/fomo/search-bar';
import { useDiscovery } from '../../hooks/use-discovery';
import {
  DEFAULT_DISCOVERY_LAT,
  DEFAULT_DISCOVERY_LNG,
  DEFAULT_DISCOVERY_RADIUS,
} from '../../utils/location-config';
import type { UiEvent } from '../../types/ui';
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

// ─── Constants ────────────────────────────────────────────────────────────────

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = 260;
const CARD_GAP   = 16;

// Coordinates come from utils/location-config (reads EXPO_PUBLIC_DEFAULT_* env vars).
// Athens defaults are used for staging; swap via .env for other cities.
// TODO: replace with real device location once expo-location is wired up.

// ─── Screen ───────────────────────────────────────────────────────────────────

export default function DiscoveryScreen() {
  const [selectedEvent, setSelectedEvent] = useState<UiEvent | null>(null);
  const [isCalendarView, setIsCalendarView] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [activeCategories, setActiveCategories] = useState<string[]>([]);

  const { events, loading, error, refetch } = useDiscovery({
    lat: DEFAULT_DISCOVERY_LAT,
    lng: DEFAULT_DISCOVERY_LNG,
    radiusKm: DEFAULT_DISCOVERY_RADIUS,
  });

  // Client-side filter: text matches title or venue; categories match UiEventCategory (lowercase).
  const filteredEvents = useMemo(() => {
    let result = events;
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
  }, [events, searchText, activeCategories]);

  const handleFilterChange = useCallback((filters: string[]) => {
    setActiveCategories(filters);
  }, []);

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

  return (
    <View style={styles.screen}>

      {/* Layer 0: Mapbox — bottom-most; shares staging defaults as discovery */}
      <FomoMap centerLat={DEFAULT_DISCOVERY_LAT} centerLng={DEFAULT_DISCOVERY_LNG} />

      {/* Layer 1: neon grid overlay */}
      <NeonGrid />

      {/* Layer 2: SearchBar — text search + category chips + view toggle */}
      <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
        <SearchBar
          isCalendarView={isCalendarView}
          onViewToggle={() => setIsCalendarView((v) => !v)}
          onSearchChange={setSearchText}
          onFilterChange={handleFilterChange}
        />
      </View>

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
