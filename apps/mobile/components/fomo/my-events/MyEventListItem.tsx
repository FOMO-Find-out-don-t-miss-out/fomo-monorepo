import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { MapPin } from 'lucide-react-native';
import React from 'react';

import { Colors, Radii, Spacing, Typography } from '../../../theme';
import type { RelationshipType } from '../../../utils/event-relationships-api';
import type { UiEvent } from '../../../types/ui';

// ─── Relationship dot config ─────────────────────────────────────────────────

const REL_DOTS: { type: RelationshipType; color: string }[] = [
  { type: 'saved',      color: Colors.purple  },
  { type: 'interested', color: Colors.magenta },
  { type: 'going',      color: Colors.success  },
];

// ─── Props ───────────────────────────────────────────────────────────────────

interface MyEventListItemProps {
  event: UiEvent;
  relationships: RelationshipType[];
  pendingTypes?: RelationshipType[];
  onPress: () => void;
}

// ─── Component ───────────────────────────────────────────────────────────────

export function MyEventListItem({
  event,
  relationships,
  pendingTypes = [],
  onPress,
}: MyEventListItemProps) {
  const catColors = Colors.category[event.category];
  const accentColor = catColors.text;

  const activeDots = REL_DOTS.filter(({ type }) => relationships.includes(type));
  const hasPending = pendingTypes.length > 0;

  return (
    <Pressable
      style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
      onPress={onPress}
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

        {/* Row 2: time · venue + relationship indicators */}
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

          {/* Relationship indicators */}
          <View style={styles.indicators}>
            {hasPending ? (
              <ActivityIndicator size={12} color={Colors.purple} />
            ) : (
              activeDots.map(({ type, color }) => (
                <View key={type} style={[styles.dot, { backgroundColor: color }]} />
              ))
            )}
          </View>
        </View>
      </View>
    </Pressable>
  );
}

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
  indicators: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    flexShrink: 0,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: Radii.full,
  },
});
