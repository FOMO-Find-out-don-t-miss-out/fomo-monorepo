import { Bookmark, CheckCircle, Heart, LayoutList } from 'lucide-react-native';
import { useFocusEffect } from 'expo-router';
import React, { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { EventCard } from '../../components/fomo/event-card';
import { EventDetails } from '../../components/fomo/event-details';
import { FomoEmptyState, FomoErrorState, FomoLoadingState, FomoScreen } from '../../components/ui';
import { useAuth } from '../../hooks/use-auth';
import { useMyEvents } from '../../hooks/use-my-events';
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

// ─── Inner list (one per tab) ─────────────────────────────────────────────────

interface TabListProps {
  tab: TabLabel;
  accessToken: string;
  onEventPress: (event: UiEvent) => void;
  triggerRefetch: number;
}

function TabList({ tab, accessToken, onEventPress, triggerRefetch }: TabListProps) {
  const { events, isLoading, error, refetch, remove } = useMyEvents(
    TAB_TYPE[tab],
    accessToken,
  );
  const insets = useSafeAreaInsets();

  useFocusEffect(
    useCallback(() => {
      refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [triggerRefetch]),
  );

  if (isLoading) return <FomoLoadingState />;
  if (error) return <FomoErrorState message={error} onRetry={refetch} />;
  if (events.length === 0) {
    return (
      <FomoEmptyState
        icon={<Heart size={48} color={TAB_COLOR[tab]} strokeWidth={1.2} />}
        message={EMPTY_MESSAGE[tab]}
        sub={EMPTY_SUB[tab]}
      />
    );
  }

  return (
    <ScrollView
      contentContainerStyle={[
        styles.list,
        { paddingBottom: insets.bottom + Spacing.xl },
      ]}
      showsVerticalScrollIndicator={false}
    >
      {events.map((event) => (
        <View key={event.id} style={styles.cardRow}>
          <EventCard
            event={event}
            isSaved={tab === 'Saved'}
            isSaveLoading={false}
            onToggleSave={tab === 'Saved' ? () => remove(event.id) : undefined}
            onPress={() => onEventPress(event)}
          />
        </View>
      ))}
    </ScrollView>
  );
}

// ─── Screen ───────────────────────────────────────────────────────────────────

export default function MyEventsScreen() {
  const insets = useSafeAreaInsets();
  const { accessToken, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<TabLabel>('Saved');
  const [selectedEvent, setSelectedEvent] = useState<UiEvent | null>(null);
  // Incrementing this causes TabList to re-run useFocusEffect on tab switch
  const [refetchKey, setRefetchKey] = useState(0);

  // Trigger a refetch whenever the active tab changes so we get fresh data
  const handleTabPress = useCallback((tab: TabLabel) => {
    setActiveTab(tab);
    setRefetchKey((k) => k + 1);
  }, []);

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
                <Bookmark size={13} color={color} fill={isActive ? color : 'transparent'} strokeWidth={1.5} />
              )}
              {tab === 'Interested' && (
                <Heart size={13} color={color} fill={isActive ? color : 'transparent'} strokeWidth={1.5} />
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
      <TabList
        tab={activeTab}
        accessToken={accessToken}
        onEventPress={setSelectedEvent}
        triggerRefetch={refetchKey}
      />

      {/* Detail sheet — remove from this collection when toggled off */}
      <EventDetails
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
        relationships={selectedEvent ? [TAB_TYPE[activeTab]] : []}
        onToggleRelationship={
          selectedEvent
            ? (type) => {
                if (type === TAB_TYPE[activeTab]) {
                  setSelectedEvent(null);
                  setRefetchKey((k) => k + 1);
                }
              }
            : undefined
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
