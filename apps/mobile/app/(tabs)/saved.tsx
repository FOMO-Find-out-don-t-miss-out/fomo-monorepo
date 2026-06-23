import { Bookmark, CheckCircle, Heart, LayoutList } from 'lucide-react-native';
import { useFocusEffect } from 'expo-router';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { EventCard } from '../../components/fomo/event-card';
import { EventDetails } from '../../components/fomo/event-details';
import { FomoEmptyState, FomoErrorState, FomoLoadingState, FomoScreen } from '../../components/ui';
import { useAuth } from '../../hooks/use-auth';
import { useMyEvents } from '../../hooks/use-my-events';
import { useRelationshipState } from '../../hooks/use-relationship-state';
import { Colors, Radii, Spacing, Typography } from '../../theme';
import type { RelationshipType } from '../../utils/event-relationships-api';
import type { UiEvent } from '../../types/ui';

// ─── Tab config ───────────────────────────────────────────────────────────────

const TABS = ['Saved', 'Interested', 'Going'] as const;
type TabLabel = (typeof TABS)[number];

const TAB_TYPE: Record<TabLabel, RelationshipType> = {
  Saved: 'saved',
  Interested: 'interested',
  Going: 'going',
};

const TAB_COLOR: Record<TabLabel, string> = {
  Saved: Colors.purple,
  Interested: Colors.magenta,
  Going: Colors.success,
};

const EMPTY_MESSAGE: Record<TabLabel, string> = {
  Saved: 'No saved events yet',
  Interested: 'No interested events yet',
  Going: 'No going events yet',
};

const EMPTY_SUB: Record<TabLabel, string> = {
  Saved: 'Tap the bookmark on any event to save it here.',
  Interested: 'Mark events as interested from the event detail sheet.',
  Going: 'Mark events as going from the event detail sheet.',
};

// ─── Screen ───────────────────────────────────────────────────────────────────

export default function MyEventsScreen() {
  const insets = useSafeAreaInsets();
  const { accessToken, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<TabLabel>('Saved');
  const [selectedEvent, setSelectedEvent] = useState<UiEvent | null>(null);

  // Fetch events + full relationship state for the active tab.
  const { events, relationships: batchRel, isLoading, error, refetch } = useMyEvents(
    TAB_TYPE[activeTab],
    accessToken,
  );

  // Optimistic relationship layer — single source of truth for the detail sheet
  // and card bookmark state across all three relationship types.
  const {
    state: relState,
    syncFromServer,
    toggle: toggleRel,
    isPending: isRelPending,
    hasRelationship,
  } = useRelationshipState(accessToken);

  // Sync batch-fetched relationship state into the optimistic layer whenever
  // new events are loaded (tab switch, focus refetch, or initial mount).
  useEffect(() => {
    syncFromServer(batchRel);
  }, [batchRel, syncFromServer]);

  // Refetch the active tab's events when the screen gains focus so that
  // changes made in Discover (save/unsave) are reflected here.
  useFocusEffect(
    useCallback(() => {
      refetch();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTab]),
  );

  // Derive visible events: filter out any event where the optimistic state shows
  // the current tab's relationship type has been toggled off.  This lets the
  // card disappear instantly when the user unsaves/un-interests/un-goes in the
  // detail sheet without needing a separate list-remove API call.
  const visibleEvents = useMemo(
    () =>
      events.filter((e) => {
        const rels = relState[e.id];
        // If the optimistic layer hasn't received state for this event yet
        // (batch fetch still in flight), trust the list membership.
        if (rels === undefined) return true;
        return rels.includes(TAB_TYPE[activeTab]);
      }),
    [events, relState, activeTab],
  );

  const handleTabPress = useCallback((tab: TabLabel) => {
    setActiveTab(tab);
    setSelectedEvent(null);
  }, []);

  // ── Auth guards ─────────────────────────────────────────────────────────────

  if (authLoading) {
    return (
      <FomoScreen>
        <FomoLoadingState />
      </FomoScreen>
    );
  }

  if (!accessToken) {
    return (
      <FomoScreen>
        <FomoEmptyState
          icon={<LayoutList size={48} color={Colors.textMuted} strokeWidth={1.2} />}
          message="Log in to see your events"
        />
      </FomoScreen>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <FomoScreen>
      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + Spacing.md }]}>
        <LayoutList size={18} color={Colors.purple} strokeWidth={1.5} />
        <Text style={styles.headerTitle}>My Events</Text>
      </View>

      {/* Segmented tab bar */}
      <View style={styles.tabBar}>
        {TABS.map((tab) => {
          const isActive = tab === activeTab;
          const color = isActive ? TAB_COLOR[tab] : Colors.textMuted;
          return (
            <Pressable
              key={tab}
              style={[
                styles.tabBtn,
                isActive && { borderColor: color, backgroundColor: `${color}18` },
              ]}
              onPress={() => handleTabPress(tab)}
              accessibilityRole="tab"
              accessibilityState={{ selected: isActive }}
            >
              {tab === 'Saved' && (
                <Bookmark
                  size={13}
                  color={color}
                  fill={isActive ? color : 'transparent'}
                  strokeWidth={1.5}
                />
              )}
              {tab === 'Interested' && (
                <Heart
                  size={13}
                  color={color}
                  fill={isActive ? color : 'transparent'}
                  strokeWidth={1.5}
                />
              )}
              {tab === 'Going' && (
                <CheckCircle size={13} color={color} strokeWidth={1.5} />
              )}
              <Text style={[styles.tabLabel, { color }]}>{tab}</Text>
            </Pressable>
          );
        })}
      </View>

      {/* Event list for active tab */}
      {isLoading ? (
        <FomoLoadingState />
      ) : error ? (
        <FomoErrorState message={error} onRetry={refetch} />
      ) : visibleEvents.length === 0 ? (
        <FomoEmptyState
          icon={<Heart size={48} color={TAB_COLOR[activeTab]} strokeWidth={1.2} />}
          message={EMPTY_MESSAGE[activeTab]}
          sub={EMPTY_SUB[activeTab]}
        />
      ) : (
        <ScrollView
          contentContainerStyle={[
            styles.list,
            { paddingBottom: insets.bottom + Spacing.xl },
          ]}
          showsVerticalScrollIndicator={false}
        >
          {visibleEvents.map((event) => (
            <View key={event.id} style={styles.cardRow}>
              <EventCard
                event={event}
                isSaved={hasRelationship(event.id, 'saved')}
                isSaveLoading={isRelPending(event.id, 'saved')}
                onToggleSave={() => toggleRel(event.id, 'saved')}
                onPress={() => setSelectedEvent(event)}
              />
            </View>
          ))}
        </ScrollView>
      )}

      {/* Detail sheet — shows full relationship state, all three buttons active */}
      <EventDetails
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
        relationships={
          selectedEvent
            ? (relState[selectedEvent.id] ?? [TAB_TYPE[activeTab]])
            : []
        }
        onToggleRelationship={
          selectedEvent
            ? (type) => toggleRel(selectedEvent.id, type)
            : undefined
        }
        pendingRelationships={
          selectedEvent
            ? (['saved', 'interested', 'going'] as const).filter((t) =>
                isRelPending(selectedEvent.id, t),
              )
            : []
        }
      />
    </FomoScreen>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderSubtle,
  },
  headerTitle: {
    fontFamily: Typography.font.bold,
    fontSize: Typography.size['2xl'],
    color: Colors.textPrimary,
  },
  tabBar: {
    flexDirection: 'row',
    gap: Spacing.sm,
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderSubtle,
  },
  tabBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
    paddingVertical: Spacing.sm,
    borderRadius: Radii.md,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  tabLabel: {
    fontFamily: Typography.font.semiBold,
    fontSize: Typography.size.sm,
  },
  list: {
    paddingTop: Spacing.base,
    paddingHorizontal: Spacing.base,
    gap: Spacing.md,
    alignItems: 'center',
  },
  cardRow: {
    width: 260,
  },
});
