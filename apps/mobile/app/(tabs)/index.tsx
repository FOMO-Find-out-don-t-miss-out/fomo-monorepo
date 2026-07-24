import { useFocusEffect } from 'expo-router';
import { CalendarView } from '../../components/fomo/calendar-view';
import { EventCard } from '../../components/fomo/event-card';
import { EventDetails } from '../../components/fomo/event-details';
import { FomoMap } from '../../components/fomo/fomo-map';
import { SearchBar } from '../../components/fomo/search-bar';
import { FomoEmptyState, FomoErrorState, FomoLoadingState } from '../../components/ui';
import { useAuth } from '../../hooks/use-auth';
import { useDeviceLocation } from '../../hooks/use-device-location';
import { useDiscovery } from '../../hooks/use-discovery';
import { useEventRelationships } from '../../hooks/use-event-relationships';
import { getRelationshipRevision, setEventIntent } from '../../utils/event-relationships-api';
import { DEFAULT_DISCOVERY_RADIUS } from '../../utils/location-config';
import {
  perfCountRender,
  perfEnabled,
  perfLog,
  perfMark,
  perfSince,
  usePerfScreenFocus,
} from '../../utils/performance-debug';
import { haversineKm, formatDistanceKm, hasValidCoords } from '../../utils/geo';
import type { EventIntent, UiEvent } from '../../types/ui';
import { LocateFixed, MapPin } from 'lucide-react-native';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Dimensions,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import type { ListRenderItemInfo } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors } from '../../theme';

// ─── Constants ────────────────────────────────────────────────────────────────

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = 260;
const CARD_GAP   = 16;
const CARD_PITCH = CARD_WIDTH + CARD_GAP;

// FlatList windowing tuned relative to actual screen size rather than guessed
// constants (FOMO-175 — replaces the ScrollView that mounted all 70 cards):
//   - CARDS_PER_SCREEN: how many cards fit in one viewport width.
//   - initialNumToRender: first screen + ~2 cards buffer each side, so the
//     very first swipe never shows a blank/recycling cell.
//   - maxToRenderPerBatch: one screen's worth of new cards per incremental
//     render batch during scroll.
//   - windowSize (in "screens", RN default 21): keep ~2 screens mounted on
//     either side of the visible one — first/middle/last cards stay reachable
//     by scrolling without keeping all 70 mounted at once.
const CARDS_PER_SCREEN     = Math.max(1, Math.ceil(SCREEN_WIDTH / CARD_PITCH));
const INITIAL_NUM_TO_RENDER = CARDS_PER_SCREEN + 4;
const MAX_TO_RENDER_PER_BATCH = CARDS_PER_SCREEN + 2;
const WINDOW_SIZE = 5;

// ─── Screen ───────────────────────────────────────────────────────────────────

export default function DiscoveryScreen() {
  perfCountRender('DiscoverScreen');
  usePerfScreenFocus('discover');

  const [selectedEvent, setSelectedEvent] = useState<UiEvent | null>(null);
  const [isCalendarView, setIsCalendarView] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [activeCategories, setActiveCategories] = useState<string[]>([]);

  const insets = useSafeAreaInsets();
  const { accessToken } = useAuth();

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

  // Defer the initial discovery fetch until location has resolved (granted,
  // denied, unavailable, or timed out — see useDeviceLocation) instead of
  // firing eagerly against default coordinates. Eliminates the FOMO-176
  // duplicate startup fetch: previously an immediate default-location request
  // was followed moments later by a second real-location request once
  // permission/GPS resolved, briefly rendering (and fetching intents for)
  // stale default-location events in between.
  const locationReady = locationStatus !== 'pending';

  const { events, loading, error, refetch } = useDiscovery({
    lat: location.lat,
    lng: location.lng,
    radiusKm: DEFAULT_DISCOVERY_RADIUS,
    enabled: locationReady,
  });

  const eventsWithDistance = useMemo(
    () =>
      events.map((e) => ({
        ...e,
        distance: hasValidCoords(e.lat, e.lng)
          ? formatDistanceKm(haversineKm(location.lat, location.lng, e.lat!, e.lng!))
          : undefined,
      })),
    [events, location.lat, location.lng],
  );

  // ── Intent state ─────────────────────────────────────────────────────────────
  //
  // serverIntents: authoritative batch fetch from backend (cancelled + replaced on
  // each refetch to prevent stale responses from overwriting newer state).
  // localIntents: applied immediately after a successful mutation, bridges the gap
  // before the next server refetch returns.

  const eventIds = useMemo(() => eventsWithDistance.map((e) => e.id), [eventsWithDistance]);
  const { intents: serverIntents, refetch: refetchIntents } = useEventRelationships(eventIds, accessToken);

  const [localIntents, setLocalIntents] = useState<Record<string, EventIntent>>({});
  const [pendingEventId, setPendingEventId] = useState<string | null>(null);

  // Merged view: local overrides take precedence until the next server response.
  const intents = useMemo(
    () => ({ ...serverIntents, ...localIntents }),
    [serverIntents, localIntents],
  );

  // Clear local overrides whenever a fresh server response arrives.
  useEffect(() => {
    setLocalIntents({});
  }, [serverIntents]);

  // Cross-screen relationship consistency (FOMO-177): rather than
  // unconditionally refetching all relationships on every focus, track the
  // shared mutation-revision counter (bumped by any successful setEventIntent
  // call, from Discover or My Events) and only refetch when it has moved past
  // what Discover last synchronized to — i.e. only when something changed
  // elsewhere while this screen wasn't looking. A Discover-originated mutation
  // advances this ref itself (see handleToggleIntent) so it never refetches
  // its own already-confirmed change.
  const lastSyncedRevisionRef = useRef(getRelationshipRevision());

  useFocusEffect(
    useCallback(() => {
      const currentRevision = getRelationshipRevision();
      if (currentRevision !== lastSyncedRevisionRef.current) {
        lastSyncedRevisionRef.current = currentRevision;
        refetchIntents('external-invalidation');
      }
    }, [refetchIntents]),
  );

  const handleToggleIntent = useCallback(async (type: 'interested' | 'going') => {
    if (!accessToken || !selectedEvent || pendingEventId) return;
    const eventId       = selectedEvent.id;
    const currentIntent = intents[eventId] ?? null;
    const tapMark       = perfMark();
    perfLog('intent-toggle', { screen: 'discover', phase: 'tap', type });
    setPendingEventId(eventId);
    try {
      const nextIntent = await setEventIntent(eventId, currentIntent, type, accessToken);
      perfLog('intent-toggle', {
        screen: 'discover',
        phase: 'mutation-done',
        duration_ms: perfSince(tapMark),
      });
      // setEventIntent only resolves on a server-confirmed success, so
      // nextIntent already IS canonical state — apply it locally and advance
      // our synced revision so this Discover-originated change doesn't
      // trigger a refetch of itself on the next focus (FOMO-177: no full
      // relationship refetch after a successful mutation).
      setLocalIntents((prev) => ({ ...prev, [eventId]: nextIntent }));
      lastSyncedRevisionRef.current = getRelationshipRevision();
      perfLog('intents-reconcile', { screen: 'discover', mode: 'local' });
    } catch {
      // silent — user can retry by tapping again
    } finally {
      setPendingEventId(null);
      perfLog('intent-toggle', {
        screen: 'discover',
        phase: 'settled',
        duration_ms: perfSince(tapMark),
      });
    }
  }, [accessToken, selectedEvent, pendingEventId, intents]);

  // ── Filtering ─────────────────────────────────────────────────────────────────

  const filteredEvents = useMemo(() => {
    let result = eventsWithDistance;
    const q = searchText.trim().toLowerCase();
    if (q) {
      result = result.filter(
        (e) => e.title.toLowerCase().includes(q) || e.venue.toLowerCase().includes(q),
      );
    }
    if (activeCategories.length > 0) {
      result = result.filter((e) => activeCategories.includes(e.category.toLowerCase()));
    }
    return result;
  }, [eventsWithDistance, searchText, activeCategories]);

  const handleFilterChange = useCallback((filters: string[]) => {
    setActiveCategories(filters);
  }, []);

  // Size of the filtered dataset handed to the carousel — NOT the number of
  // FlatList cells actually mounted (that's windowed/virtualized and varies
  // with scroll position, FOMO-175). For real mounted-card counts, run a
  // dedicated EXPO_PUBLIC_PERF_RENDER_DEBUG pass and read the EventCard
  // `render` counter instead.
  useEffect(() => {
    if (perfEnabled && !loading && !error) {
      perfLog('discover-render', {
        events_total: events.length,
        cards_in_dataset: filteredEvents.length,
      });
    }
  }, [loading, error, events.length, filteredEvents.length]);

  // Shared by the map (pin tap) and the carousel (card tap): looks up the
  // pressed event by id and selects it. One stable reference — identity only
  // changes when eventsWithDistance changes, not on every Discover render —
  // is what lets memoized EventCard bail out of unrelated re-renders (FOMO-175).
  const handleEventSelect = useCallback(
    (eventId: string) => {
      const found = eventsWithDistance.find((e) => e.id === eventId);
      if (found) setSelectedEvent(found);
    },
    [eventsWithDistance],
  );

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

  // Card pitch (width + gap) is fixed, so the offset of item `i` from the
  // start of content is always `carouselPadding + i * CARD_PITCH` and every
  // item is exactly CARD_WIDTH wide — genuinely fixed dimensions, safe for
  // getItemLayout (FOMO-175: avoids an async layout pass per card on mount).
  const getItemLayout = useCallback(
    (_data: ArrayLike<UiEvent> | null | undefined, index: number) => ({
      length: CARD_WIDTH,
      offset: carouselPadding + index * CARD_PITCH,
      index,
    }),
    [carouselPadding],
  );

  const keyExtractor = useCallback((event: UiEvent) => event.id, []);

  const renderEventCard = useCallback(
    ({ item }: ListRenderItemInfo<UiEvent>) => (
      <EventCard
        event={item}
        isActive={selectedEvent?.id === item.id}
        onPress={handleEventSelect}
      />
    ),
    [selectedEvent?.id, handleEventSelect],
  );

  const locateIconColor =
    locationStatus === 'granted'
      ? Colors.purple
      : locationStatus === 'pending'
        ? Colors.textSecondary
        : Colors.textMuted;

  const selectedIntent = selectedEvent ? (intents[selectedEvent.id] ?? null) : null;
  const selectedPending = selectedEvent ? pendingEventId === selectedEvent.id : false;

  return (
    <View style={styles.screen}>

      {/* Layer 0: Mapbox map */}
      <FomoMap
        centerLat={location.lat}
        centerLng={location.lng}
        events={eventsWithDistance}
        selectedEventId={selectedEvent?.id ?? null}
        showUserLocation={locationStatus === 'granted'}
        onPinPress={handleEventSelect}
        locateMe={locateMe}
      />

      {/* Layer 1: SearchBar */}
      <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
        <SearchBar
          isCalendarView={isCalendarView}
          onViewToggle={() => setIsCalendarView((v) => !v)}
          onSearchChange={setSearchText}
          onFilterChange={handleFilterChange}
        />
      </View>

      {/* Layer 2: Locate-me button */}
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

      {/* Location mode label */}
      {!isCalendarView && locationStatus !== 'pending' && !pendingLocate && (
        <View style={styles.locationLabel}>
          <View
            style={[
              styles.locationDot,
              {
                backgroundColor:
                  locationStatus === 'granted'
                    ? Colors.purple
                    : locationStatus === 'unavailable'
                      ? Colors.warning
                      : Colors.textDisabled,
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
      <View
        pointerEvents={isCalendarView ? 'none' : 'auto'}
        style={[styles.carouselAnchor, { opacity: isCalendarView ? 0 : 1 }]}
      >
        {loading ? (
          <FomoLoadingState style={styles.feedbackContainer} />
        ) : error ? (
          <FomoErrorState
            style={styles.feedbackContainer}
            message="Could not load events"
            onRetry={refetch}
          />
        ) : filteredEvents.length === 0 ? (
          <FomoEmptyState
            style={styles.feedbackContainer}
            icon={<MapPin size={28} color={Colors.textMuted} strokeWidth={1.5} />}
            message={events.length === 0 ? 'No events nearby' : 'No events match your search'}
          />
        ) : (
          <FlatList
            data={filteredEvents}
            renderItem={renderEventCard}
            keyExtractor={keyExtractor}
            getItemLayout={getItemLayout}
            horizontal
            showsHorizontalScrollIndicator={false}
            decelerationRate="fast"
            snapToInterval={CARD_PITCH}
            snapToAlignment="center"
            contentContainerStyle={[
              styles.carouselContent,
              { paddingHorizontal: carouselPadding },
            ]}
            initialNumToRender={INITIAL_NUM_TO_RENDER}
            maxToRenderPerBatch={MAX_TO_RENDER_PER_BATCH}
            windowSize={WINDOW_SIZE}
          />
        )}
      </View>

      {/* Layer 3b: Calendar view */}
      {isCalendarView && (
        <CalendarView
          events={filteredEvents}
          onEventPress={(e) => setSelectedEvent(e)}
        />
      )}

      {/* Layer 4: Detail sheet */}
      <EventDetails
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
        intent={accessToken ? selectedIntent : null}
        onToggleIntent={accessToken ? handleToggleIntent : undefined}
        isPendingIntent={selectedPending}
      />

    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: Colors.background,
  },
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
  },
});
