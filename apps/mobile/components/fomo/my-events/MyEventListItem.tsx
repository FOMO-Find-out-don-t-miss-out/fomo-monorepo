import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { MapPin } from 'lucide-react-native';
import React from 'react';

import { Colors, Radii, Spacing, Typography } from '../../../theme';
import { perfCountRender } from '../../../utils/performance-debug';
import type { EventIntent, UiEvent } from '../../../types/ui';

// ─── Intent dot config ───────────────────────────────────────────────────────

const INTENT_DOT: Record<'interested' | 'going', string> = {
  interested: Colors.intentInterested,
  going:      Colors.intentGoing,
};

// ─── Props ───────────────────────────────────────────────────────────────────

interface MyEventListItemProps {
  event: UiEvent;
  intent: EventIntent;
  isPending?: boolean;
  /**
   * Receives the event's id rather than being called with no args, so the
   * parent can pass one stable function to every row instead of a fresh
   * closure per row per render — required for React.memo below to actually
   * skip re-renders (FOMO-178, mirrors the FOMO-175 EventCard pattern).
   */
  onPress: (id: string) => void;
}

// ─── Component ───────────────────────────────────────────────────────────────
//
// Memoized (FOMO-178): with a stable `onPress` reference and a stable
// `event` object identity from the hook's data layer, this bails out of
// re-render for rows unaffected by an unrelated state change (e.g. the
// other tab's background refresh).

function MyEventListItemBase({
  event,
  intent,
  isPending = false,
  onPress,
}: MyEventListItemProps) {
  perfCountRender('MyEventListItem', 10);
  const catColors = Colors.category[event.category];
  const accentColor = catColors.text;
  const dotColor = intent ? INTENT_DOT[intent] : null;

  return (
    <Pressable
      style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
      onPress={() => onPress(event.id)}
      accessibilityRole="button"
      accessibilityLabel={`View details for ${event.title}`}
    >
      {/* Left category accent bar */}
      <View style={[styles.accent, { backgroundColor: accentColor }]} />

      {/* Main content */}
      <View style={styles.content}>
        {/* Row 1: title + category chip */}
        <View style={styles.titleRow}>
          <Text style={styles.title} numberOfLines={1}>
            {event.title}
          </Text>
          <View style={[styles.catChip, { borderColor: catColors.border }]}>
            <Text style={[styles.catLabel, { color: catColors.text }]} numberOfLines={1}>
              {event.category}
            </Text>
          </View>
        </View>

        {/* Row 2: time · venue + intent indicator */}
        <View style={styles.metaRow}>
          <View style={styles.metaLeft}>
            {event.time ? (
              <Text style={styles.time}>{event.time}</Text>
            ) : null}
            {event.time && event.venue ? (
              <Text style={styles.separator}>·</Text>
            ) : null}
            {event.venue ? (
              <>
                <MapPin size={10} color={Colors.textMuted} strokeWidth={1.5} />
                <Text style={styles.venue} numberOfLines={1}>
                  {event.venue}
                </Text>
              </>
            ) : null}
          </View>

          {/* Intent indicator */}
          <View style={styles.indicator}>
            {isPending ? (
              <ActivityIndicator size={12} color={dotColor ?? Colors.intentInterested} />
            ) : dotColor ? (
              <View style={[styles.dot, { backgroundColor: dotColor }]} />
            ) : null}
          </View>
        </View>
      </View>
    </Pressable>
  );
}

export const MyEventListItem = React.memo(MyEventListItemBase);

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'stretch',
    backgroundColor: Colors.surfaceCard,
    borderRadius: Radii.md,
    borderWidth: 1,
    borderColor: Colors.borderSubtle,
    overflow: 'hidden',
    minHeight: 60,
  },
  rowPressed: {
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  accent: {
    width: 3,
    borderTopLeftRadius: Radii.md,
    borderBottomLeftRadius: Radii.md,
  },
  content: {
    flex: 1,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm + 2,
    gap: 5,
    justifyContent: 'center',
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  title: {
    flex: 1,
    fontFamily: Typography.font.semiBold,
    fontSize: Typography.size.base,
    color: Colors.textPrimary,
  },
  catChip: {
    borderWidth: 1,
    borderRadius: Radii.full,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  catLabel: {
    fontFamily: Typography.font.semiBold,
    fontSize: 9,
    letterSpacing: 0.3,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  metaLeft: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  time: {
    fontFamily: Typography.font.semiBold,
    fontSize: Typography.size.sm,
    color: '#22D3EE',
  },
  separator: {
    fontFamily: Typography.font.regular,
    fontSize: Typography.size.sm,
    color: Colors.textDisabled,
  },
  venue: {
    flex: 1,
    fontFamily: Typography.font.regular,
    fontSize: Typography.size.sm,
    color: Colors.textMuted,
  },
  indicator: {
    flexShrink: 0,
    width: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: Radii.full,
  },
});
