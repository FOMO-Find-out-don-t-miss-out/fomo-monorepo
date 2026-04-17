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
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

const AnimatedBlurView = Animated.createAnimatedComponent(BlurView);

import {
  DateStripPicker,
  formatEventDateKey,
} from './date-strip-picker';
import type { Event, EventCategory } from '../../types/ui';

// ─── Design tokens ────────────────────────────────────────────────────────────

const NEON_PURPLE = '#BC13FE';
const NEON_CYAN = '#22D3EE';
const GLASS_BG = 'rgba(18, 18, 24, 0.75)';
const GLASS_BORDER = 'rgba(255, 255, 255, 0.1)';

// SearchBar ≈ insets.top + 58. Strip needs 12px gap below.
const HEADER_OFFSET = 70;
// Tab bar sits at bottom 116; leave a small buffer.
const BOTTOM_OFFSET = 124;

type CatSwatch = { border: string; text: string; bg: string };
const CATEGORY_COLORS: Record<EventCategory, CatSwatch> = {
  Music:    { border: 'rgba(168, 85, 247, 0.5)', text: '#C084FC', bg: 'rgba(168, 85, 247, 0.1)' },
  Arts:     { border: 'rgba(236, 72, 153, 0.5)', text: '#F472B6', bg: 'rgba(236, 72, 153, 0.1)' },
  Theater:  { border: 'rgba(245, 158, 11, 0.5)', text: '#FBBF24', bg: 'rgba(245, 158, 11, 0.1)' },
  Sports:   { border: 'rgba(34, 197, 94, 0.5)',  text: '#4ADE80', bg: 'rgba(34, 197, 94, 0.1)' },
  Comedy:   { border: 'rgba(249, 115, 22, 0.5)', text: '#FB923C', bg: 'rgba(249, 115, 22, 0.1)' },
  Festival: { border: 'rgba(6, 182, 212, 0.5)',  text: '#22D3EE', bg: 'rgba(6, 182, 212, 0.1)' },
};

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
  const cat = CATEGORY_COLORS[event.category];
  return (
    <Pressable onPress={onPress} style={styles.card}>
      <View style={styles.timeCol}>
        <Clock size={12} color="rgba(34, 211, 238, 0.7)" />
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
          <MapPin size={10} color="rgba(255, 255, 255, 0.5)" />
          <Text numberOfLines={1} style={styles.venueText}>
            {event.venue}
          </Text>
          {!!event.distance && (
            <Text style={styles.distanceText}>{event.distance}</Text>
          )}
        </View>
      </View>

      <View style={styles.ticketBtn}>
        <Ticket size={14} color={NEON_PURPLE} />
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

  // Fade in when the calendar view mounts.
  const viewOpacity = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(viewOpacity, {
      toValue: 1,
      duration: 260,
      useNativeDriver: true,
    }).start();
  }, [viewOpacity]);

  // Fade list when selectedDate changes + reset scroll.
  const listRef = useRef<ScrollView>(null);
  const listOpacity = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    listRef.current?.scrollTo({ y: 0, animated: false });
    listOpacity.setValue(0);
    Animated.timing(listOpacity, {
      toValue: 1,
      duration: 220,
      useNativeDriver: true,
    }).start();
  }, [selectedDate, listOpacity]);

  return (
    <Animated.View
      pointerEvents="box-none"
      style={[StyleSheet.absoluteFillObject, { opacity: viewOpacity }]}
    >
      {/* Backdrop — dims the map/grid behind so the glass surfaces read clearly */}
      <AnimatedBlurView
        pointerEvents="none"
        tint="dark"
        intensity={40}
        style={[StyleSheet.absoluteFillObject, styles.backdrop]}
      />

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
    </Animated.View>
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
    color: 'rgba(255, 255, 255, 0.4)',
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
    backgroundColor: NEON_PURPLE,
    shadowColor: NEON_PURPLE,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.9,
    shadowRadius: 6,
    elevation: 4,
  },
  headerDate: {
    fontSize: 13,
    fontWeight: '700',
    color: '#fff',
  },
  headerCount: {
    fontSize: 11,
    color: 'rgba(255, 255, 255, 0.4)',
  },
  headerRule: {
    flex: 1,
    height: 1,
    backgroundColor: 'rgba(188, 19, 254, 0.25)',
  },
  // ── Event card ───────────────────────────────────────────────────────────
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    padding: 12,
    backgroundColor: GLASS_BG,
    borderWidth: 1,
    borderColor: GLASS_BORDER,
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
    color: NEON_CYAN,
  },
  cardDivider: {
    width: 1,
    height: 40,
    backgroundColor: 'rgba(168, 85, 247, 0.35)',
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
    color: NEON_CYAN,
  },
  cardTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 2,
  },
  venueRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  venueText: {
    fontSize: 10,
    color: 'rgba(255, 255, 255, 0.5)',
    flexShrink: 1,
  },
  distanceText: {
    fontSize: 10,
    color: 'rgba(255, 255, 255, 0.3)',
    marginLeft: 4,
  },
  ticketBtn: {
    padding: 8,
    borderRadius: 10,
    backgroundColor: 'rgba(188, 19, 254, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(188, 19, 254, 0.3)',
  },
});
