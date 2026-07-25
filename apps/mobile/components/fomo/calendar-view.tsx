import { BlurView } from 'expo-blur';
import {
  Calendar as CalendarIcon,
  Clock,
  MapPin,
  Ticket,
} from 'lucide-react-native';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Animated,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors } from '../../theme';

import {
  DateStripPicker,
  formatEventDateKey,
} from './date-strip-picker';
import type { Event } from '../../types/ui';

// ─── Layout constants ─────────────────────────────────────────────────────────

// SearchBar ≈ insets.top + 58. Strip needs 12px gap below.
const HEADER_OFFSET = 70;
// Tab bar sits at bottom 116; leave a small buffer.
const BOTTOM_OFFSET = 124;

// ─── Props ────────────────────────────────────────────────────────────────────

interface CalendarViewProps {
  events: Event[];
  onEventPress: (event: Event) => void;
}

// ─── Sub: Compact event row ──────────────────────────────────────────────────

function CalendarEventCard({
  event,
  onPress,
}: {
  event: Event;
  onPress: () => void;
}) {
  const cat = Colors.category[event.category];
  return (
    <Pressable onPress={onPress} style={styles.card}>
      <View style={styles.timeCol}>
        <Clock size={12} color={Colors.textSecondary} />
        <Text style={styles.timeText}>{event.time}</Text>
      </View>

      <View style={styles.cardDivider} />

      <View style={styles.cardInfo}>
        <View style={styles.cardInfoRow}>
          <View
            style={[
              styles.categoryBadge,
              { borderColor: cat.border, backgroundColor: cat.bg },
            ]}
          >
            <Text style={[styles.categoryText, { color: cat.text }]}>
              {event.category}
            </Text>
          </View>
          {!!event.price && <Text style={styles.priceText}>{event.price}</Text>}
        </View>

        <Text numberOfLines={1} style={styles.cardTitle}>
          {event.title}
        </Text>

        <View style={styles.venueRow}>
          <MapPin size={10} color={Colors.textSecondary} />
          <Text numberOfLines={1} style={styles.venueText}>
            {event.venue}
          </Text>
          {!!event.distance && (
            <Text style={styles.distanceText}>{event.distance}</Text>
          )}
        </View>
      </View>

      <View style={styles.ticketBtn}>
        <Ticket size={14} color={Colors.purpleNeon} />
      </View>
    </Pressable>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function CalendarView({ events, onEventPress }: CalendarViewProps) {
  const insets = useSafeAreaInsets();
  const [selectedDate, setSelectedDate] = useState<string>(() =>
    formatEventDateKey(new Date()),
  );

  const eventCountByDate = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const e of events) counts[e.date] = (counts[e.date] ?? 0) + 1;
    return counts;
  }, [events]);

  const eventsForDate = useMemo(
    () => events.filter((e) => e.date === selectedDate),
    [events, selectedDate],
  );

  // Fade list when selectedDate changes + reset scroll.
  // Skip on the very first render so the list is immediately visible when
  // the calendar opens — the setValue(0) would otherwise leave it blank.
  const listRef = useRef<ScrollView>(null);
  const listOpacity = useRef(new Animated.Value(1)).current;
  const isFirstRender = useRef(true);
  useEffect(() => {
    listRef.current?.scrollTo({ y: 0, animated: false });
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    listOpacity.setValue(0);
    Animated.timing(listOpacity, {
      toValue: 1,
      duration: 220,
      useNativeDriver: true,
    }).start();
  }, [selectedDate, listOpacity]);

  return (
    <View
      pointerEvents="box-none"
      style={StyleSheet.absoluteFillObject}
    >
      {/* Backdrop — dims the map behind the glass surfaces.
          BlurView is GPU-intensive to mount/unmount on Android so use a plain
          dark overlay there; iOS keeps the frosted-glass effect. */}
      {Platform.OS === 'ios' ? (
        <BlurView
          pointerEvents="none"
          tint="dark"
          intensity={40}
          style={[StyleSheet.absoluteFillObject, styles.backdrop]}
        />
      ) : (
        <View
          pointerEvents="none"
          style={[StyleSheet.absoluteFillObject, styles.backdrop]}
        />
      )}

      {/* Content column — sits below the SearchBar, above the tab bar */}
      <View
        pointerEvents="box-none"
        style={[
          styles.content,
          {
            top: insets.top + HEADER_OFFSET,
            bottom: BOTTOM_OFFSET,
          },
        ]}
      >
        {/* Date strip (glassmorphic, neon active state) */}
        <View style={styles.strip}>
          <DateStripPicker
            selectedDate={selectedDate}
            onDateSelect={setSelectedDate}
            eventCountByDate={eventCountByDate}
          />
        </View>

        {/* Events for selected date */}
        <Animated.View style={[styles.listWrap, { opacity: listOpacity }]}>
          {eventsForDate.length === 0 ? (
            <View style={styles.empty}>
              <CalendarIcon size={36} color="rgba(255, 255, 255, 0.2)" />
              <Text style={styles.emptyText}>No events on this date</Text>
            </View>
          ) : (
            <ScrollView
              ref={listRef}
              showsVerticalScrollIndicator={false}
              contentContainerStyle={styles.listContent}
            >
              <View style={styles.headerRow}>
                <View style={styles.headerDot} />
                <Text style={styles.headerDate}>{selectedDate}</Text>
                <Text style={styles.headerCount}>
                  {eventsForDate.length} event
                  {eventsForDate.length !== 1 ? 's' : ''}
                </Text>
                <View style={styles.headerRule} />
              </View>

              {eventsForDate.map((event) => (
                <CalendarEventCard
                  key={event.id}
                  event={event}
                  onPress={() => onEventPress(event)}
                />
              ))}
            </ScrollView>
          )}
        </Animated.View>
      </View>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  backdrop: {
    backgroundColor: 'rgba(11, 11, 15, 0.78)',
  },
  content: {
    position: 'absolute',
    left: 0,
    right: 0,
    zIndex: 20,
  },
  strip: {
    paddingVertical: 4,
  },
  // ── List ─────────────────────────────────────────────────────────────────
  listWrap: {
    flex: 1,
  },
  listContent: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 16,
    gap: 10,
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingBottom: 48,
  },
  emptyText: {
    marginTop: 12,
    color: Colors.textMuted,
    fontSize: 13,
  },
  // ── Header ───────────────────────────────────────────────────────────────
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  headerDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.purpleNeon,
    shadowColor: Colors.purpleNeon,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.9,
    shadowRadius: 6,
    elevation: 4,
  },
  headerDate: {
    fontSize: 13,
    fontWeight: '700',
    color: Colors.textPrimary,
  },
  headerCount: {
    fontSize: 11,
    color: Colors.textMuted,
  },
  headerRule: {
    flex: 1,
    height: 1,
    backgroundColor: Colors.purpleDim,
  },
  // ── Event card ───────────────────────────────────────────────────────────
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    padding: 12,
    backgroundColor: Colors.surfaceGlass,
    borderWidth: 1,
    borderColor: Colors.borderGlass,
    borderRadius: 14,
  },
  timeCol: {
    minWidth: 48,
    alignItems: 'center',
    flexDirection: 'row',
    gap: 4,
  },
  timeText: {
    fontSize: 13,
    fontWeight: '700',
    color: Colors.textSecondary,
  },
  cardDivider: {
    width: 1,
    height: 40,
    backgroundColor: Colors.borderFocus,
  },
  cardInfo: {
    flex: 1,
    minWidth: 0,
  },
  cardInfoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 3,
  },
  categoryBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 999,
    borderWidth: 1,
  },
  categoryText: {
    fontSize: 9,
    fontWeight: '600',
  },
  priceText: {
    fontSize: 10,
    fontWeight: '700',
    color: Colors.textPrimary,
  },
  cardTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: Colors.textPrimary,
    marginBottom: 2,
  },
  venueRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  venueText: {
    fontSize: 10,
    color: Colors.textSecondary,
    flexShrink: 1,
  },
  distanceText: {
    fontSize: 10,
    color: Colors.textMuted,
    marginLeft: 4,
  },
  ticketBtn: {
    padding: 8,
    borderRadius: 10,
    backgroundColor: Colors.purpleDim,
    borderWidth: 1,
    borderColor: Colors.borderFocus,
  },
});
