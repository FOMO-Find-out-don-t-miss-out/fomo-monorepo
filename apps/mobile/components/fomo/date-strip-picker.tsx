import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

// ─── Design tokens ────────────────────────────────────────────────────────────

const NEON_PURPLE = '#BC13FE';

const ITEM_WIDTH = 64;
const ITEM_GAP = 8;
const STRIP_PADDING_X = 16;

// ─── Date helpers ─────────────────────────────────────────────────────────────

const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTH_LABELS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

// Matches the "Apr 15, 2026" keys used in the EVENTS mock data.
export function formatEventDateKey(date: Date): string {
  return `${MONTH_LABELS[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
}

interface DateEntry {
  key: string;
  day: string;
  date: number;
  month: string;
}

export function buildNext14Days(): DateEntry[] {
  const entries: DateEntry[] = [];
  const base = new Date();
  base.setHours(0, 0, 0, 0);
  for (let i = 0; i < 14; i++) {
    const d = new Date(base);
    d.setDate(base.getDate() + i);
    entries.push({
      key: formatEventDateKey(d),
      day: DAY_LABELS[d.getDay()],
      date: d.getDate(),
      month: MONTH_LABELS[d.getMonth()],
    });
  }
  return entries;
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface DateStripPickerProps {
  selectedDate?: string | null;
  onDateSelect?: (date: string) => void;
  eventCountByDate?: Record<string, number>;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function DateStripPicker({
  selectedDate: controlledSelected,
  onDateSelect,
  eventCountByDate = {},
}: DateStripPickerProps) {
  const scrollRef = useRef<ScrollView>(null);

  const dates = useMemo(buildNext14Days, []);
  const [internalSelected, setInternalSelected] = useState<string>(dates[0].key);
  const selectedDate = controlledSelected ?? internalSelected;

  const handleSelect = useCallback(
    (key: string) => {
      setInternalSelected(key);
      onDateSelect?.(key);
    },
    [onDateSelect],
  );

  // Center the selected item in the viewport on change.
  useEffect(() => {
    const index = dates.findIndex((d) => d.key === selectedDate);
    if (index < 0 || !scrollRef.current) return;
    const itemFullWidth = ITEM_WIDTH + ITEM_GAP;
    scrollRef.current.scrollTo({
      x: Math.max(0, index * itemFullWidth - itemFullWidth),
      animated: true,
    });
  }, [selectedDate, dates]);

  return (
    <View style={styles.container}>
      <ScrollView
        ref={scrollRef}
        horizontal
        showsHorizontalScrollIndicator={false}
        decelerationRate="fast"
        contentContainerStyle={styles.scrollContent}
      >
        {dates.map(({ key, day, date, month }) => {
          const isSelected = key === selectedDate;
          const eventCount = eventCountByDate[key] ?? 0;

          return (
            <Pressable
              key={key}
              onPress={() => handleSelect(key)}
              style={[
                styles.item,
                isSelected ? styles.itemActive : styles.itemInactive,
              ]}
            >
              <Text
                style={[
                  styles.dayText,
                  isSelected ? styles.dayTextActive : styles.dayTextInactive,
                ]}
              >
                {day}
              </Text>
              <Text
                style={[
                  styles.dateText,
                  isSelected ? styles.dateTextActive : styles.dateTextInactive,
                ]}
              >
                {date}
              </Text>
              <Text
                style={[
                  styles.monthText,
                  isSelected ? styles.monthTextActive : styles.monthTextInactive,
                ]}
              >
                {month}
              </Text>

              {eventCount > 0 && (
                <View
                  style={[
                    styles.badge,
                    isSelected ? styles.badgeActive : styles.badgeInactive,
                  ]}
                >
                  <Text style={styles.badgeText}>{eventCount}</Text>
                </View>
              )}
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    // Layout-agnostic: caller decides where the strip lives.
  },
  scrollContent: {
    paddingHorizontal: STRIP_PADDING_X,
    paddingVertical: 6,
    gap: ITEM_GAP,
  },
  // ── Item base ────────────────────────────────────────────────────────────
  item: {
    minWidth: ITEM_WIDTH,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 14,
    borderWidth: 1,
  },
  itemInactive: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  // Glowing neon glass — border only, no solid fill.
  // iOS gets the soft glow via shadow*; Android elevation is intentionally
  // omitted because it draws a rectangular material drop-shadow that reads
  // as an opaque box behind the near-transparent pill.
  itemActive: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderColor: NEON_PURPLE,
    shadowColor: NEON_PURPLE,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.45,
    shadowRadius: 8,
  },
  // ── Typography ───────────────────────────────────────────────────────────
  dayText: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  dayTextInactive: {
    color: 'rgba(255, 255, 255, 0.4)',
  },
  dayTextActive: {
    color: '#E9D5FF',
  },
  dateText: {
    fontSize: 22,
    fontWeight: '800',
    marginTop: 2,
    lineHeight: 26,
  },
  dateTextInactive: {
    color: 'rgba(255, 255, 255, 0.8)',
  },
  dateTextActive: {
    color: '#fff',
    textShadowColor: 'rgba(188, 19, 254, 0.6)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 4,
  },
  monthText: {
    fontSize: 9,
    fontWeight: '600',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    marginTop: 2,
  },
  monthTextInactive: {
    color: 'rgba(255, 255, 255, 0.35)',
  },
  monthTextActive: {
    color: '#67E8F9',
  },
  // ── Event count badge ────────────────────────────────────────────────────
  badge: {
    position: 'absolute',
    top: -6,
    right: -6,
    minWidth: 16,
    height: 16,
    paddingHorizontal: 4,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeInactive: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
  },
  badgeActive: {
    backgroundColor: NEON_PURPLE,
    shadowColor: NEON_PURPLE,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.7,
    shadowRadius: 5,
  },
  badgeText: {
    fontSize: 9,
    fontWeight: '700',
    color: '#fff',
  },
});
