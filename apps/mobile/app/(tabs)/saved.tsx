import { CalendarDays, CheckCircle, Heart } from 'lucide-react-native';
import { useFocusEffect } from 'expo-router';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { EventDetails } from '../../components/fomo/event-details';
import { MyEventListItem } from '../../components/fomo/my-events/MyEventListItem';
import {
  FomoEmptyState,
  FomoErrorState,
  FomoLoadingState,
  FomoScreen,
} from '../../components/ui';
import { useAuth } from '../../hooks/use-auth';
import { useMyEvents } from '../../hooks/use-my-events';
import { useRelationshipState } from '../../hooks/use-relationship-state';
import { Colors, Radii, Spacing, Typography } from '../../theme';
import type { RelationshipType } from '../../utils/event-relationships-api';
import type { EventIntent, UiEvent } from '../../types/ui';

// ─── Tab config ───────────────────────────────────────────────────────────────

const TABS = ['Interested', 'Going'] as const;
type TabLabel = (typeof TABS)[number];

const TAB_TYPE: Record<TabLabel, RelationshipType> = {
  Interested: 'interested',
  Going:      'going',
};

const TAB_INTENT: Record<TabLabel, EventIntent> = {
  Interested: 'interested',
  Going:      'going',
};

const TAB_COLOR: Record<TabLabel, string> = {
  Interested: Colors.magenta,
  Going:      Colors.success,
};

const EMPTY_COPY: Record<TabLabel, { message: string; sub: string }> = {
  Interested: {
    message: 'Nothing here yet',
    sub:     'Open an event and tap Interested when something catches your eye.',
  },
  Going: {
    message: 'No plans yet',
    sub:     "Mark yourself as Going when you're committed — your plans live here.",
  },
};

const TAB_EMPTY_ICON: Record<TabLabel, React.ReactNode> = {
  Interested: <Heart       size={44} color={Colors.magenta} strokeWidth={1.2} />,
  Going:      <CheckCircle size={44} color={Colors.success} strokeWidth={1.2} />,
};

// ─── Date grouping ────────────────────────────────────────────────────────────

interface DateSection {
  key: string;
  label: string;
  dateRight: string;
  events: UiEvent[];
}

function localDateKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function dateLabel(isoDate: string): { label: string; dateRight: string } {
  const d = new Date(isoDate);
  const today    = localDateKey(new Date());
  const tomorrow = localDateKey(new Date(Date.now() + 86_400_000));
  const key      = localDateKey(d);

  const dateRight = d.toLocaleDateString('en-US', {
    month: 'short',
    day:   'numeric',
    year:  'numeric',
  });

  if (key === today)    return { label: 'Today',    dateRight };
  if (key === tomorrow) return { label: 'Tomorrow', dateRight };

  const label = d.toLocaleDateString('en-US', {
    weekday: 'short',
    day:     'numeric',
    month:   'short',
    year:    'numeric',
  });
  return { label, dateRight };
}

function groupAndSort(events: UiEvent[]): DateSection[] {
  const sections = new Map<string, DateSection>();
  const noDate: UiEvent[] = [];

  for (const event of events) {
    if (!event.startTime) {
      noDate.push(event);
      continue;
    }
    const key = localDateKey(new Date(event.startTime));
    if (!sections.has(key)) {
      const { label, dateRight } = dateLabel(event.startTime);
      sections.set(key, { key, label, dateRight, events: [] });
    }
    sections.get(key)!.events.push(event);
  }

  for (const section of sections.values()) {
    section.events.sort((a, b) => (a.startTime ?? '').localeCompare(b.startTime ?? ''));
  }

  const sorted = [...sections.values()].sort((a, b) => a.key.localeCompare(b.key));
  if (noDate.length > 0) {
    sorted.push({ key: 'zzzz', label: 'Date TBA', dateRight: '', events: noDate });
  }
  return sorted;
}

// ─── Screen ───────────────────────────────────────────────────────────────────

export default function MyEventsScreen() {
  const insets          = useSafeAreaInsets();
  const { accessToken, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab]               = useState<TabLabel>('Interested');
  const [selectedEvent, setSelectedEvent]       = useState<UiEvent | null>(null);

  const { events, relationships: rawRels, isLoading, error, refetch } = useMyEvents(
    TAB_TYPE[activeTab],
    accessToken,
  );

  const {
    state: intentState,
    syncFromServer,
    toggle: toggleIntent,
    isPending,
    intentFor,
  } = useRelationshipState(accessToken);

  // ── Event registry ───────────────────────────────────────────────────────────
  //
  // Accumulates event objects across ALL tab fetches so that an event moved via
  // optimistic update (e.g. Interested → Going) appears in the destination tab
  // immediately, without waiting for the server to respond to that tab's fetch.
  //
  // intentState is the single source of truth for which tab an event belongs to.
  // The registry is only the pool of known UiEvent objects.

  const [eventRegistry, setEventRegistry] = useState<Record<string, UiEvent>>({});

  useEffect(() => {
    if (!accessToken) setEventRegistry({});
  }, [accessToken]);

  useEffect(() => {
    if (events.length === 0) return;
    setEventRegistry((prev) => {
      const next = { ...prev };
      for (const e of events) next[e.id] = e;
      return next;
    });
  }, [events]);

  // ── Server sync ──────────────────────────────────────────────────────────────

  useEffect(() => {
    syncFromServer(rawRels);
  }, [rawRels, syncFromServer]);

  // ── Screen focus refetch ─────────────────────────────────────────────────────
  //
  // Fires only when the screen gains focus (e.g. user navigates here from another
  // app tab). Internal tab switches are already handled by useMyEvents responding
  // to the `relationshipType` argument changing — no second fetch needed.
  //
  // Previously `[activeTab]` was in deps which caused useFocusEffect to re-fire
  // on every internal tab switch while focused, duplicating every fetch.

  useFocusEffect(
    useCallback(() => {
      refetch();
    }, [refetch]),
  );

  // ── Visible events ───────────────────────────────────────────────────────────
  //
  // Two sources combined:
  //
  // 1. `events` (current tab server response): filtered with a pre-sync guard
  //    (!(id in intentState) → keep) to avoid a blank flash during the one-render
  //    gap between `events` arriving and syncFromServer running.
  //
  // 2. `eventRegistry` entries NOT in the current server response: events known
  //    from OTHER tab fetches that have been moved here via optimistic update.
  //    Strictly filtered (intentState[id] === tabIntent) since they were hydrated
  //    when originally loaded on the other tab.

  const tabIntent = TAB_INTENT[activeTab];
  const visibleEvents = useMemo(() => {
    const currentIds = new Set(events.map((e) => e.id));

    const fromCurrentTab = events.filter((e) => {
      if (!(e.id in intentState)) return true;
      return intentState[e.id] === tabIntent;
    });

    const fromOtherTabs = Object.values(eventRegistry).filter(
      (e) => !currentIds.has(e.id) && intentState[e.id] === tabIntent,
    );

    return [...fromCurrentTab, ...fromOtherTabs];
  }, [events, eventRegistry, intentState, tabIntent]);

  const sections = useMemo(() => groupAndSort(visibleEvents), [visibleEvents]);

  // Per-tab event count — persists across tab switches so the inactive tab always
  // shows its last known count. null = tab not yet loaded (no badge shown).
  const [tabCounts, setTabCounts] = useState<Record<TabLabel, number | null>>({
    Interested: null,
    Going:      null,
  });

  useEffect(() => {
    if (!isLoading) {
      setTabCounts((prev) => ({ ...prev, [activeTab]: visibleEvents.length }));
    }
  }, [activeTab, visibleEvents.length, isLoading]);

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
          icon={<CalendarDays size={44} color={Colors.textMuted} strokeWidth={1.2} />}
          message="Log in to see your events"
          sub="Your plans and interests live here."
        />
      </FomoScreen>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <FomoScreen>
      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + Spacing.base }]}>
        <Text style={styles.screenTitle}>My Events</Text>
        <Text style={styles.screenSub}>Your upcoming plans and interests</Text>
      </View>

      {/* Segmented tab bar */}
      <View style={styles.tabBar}>
        {TABS.map((tab) => {
          const isActive  = tab === activeTab;
          const tabColor  = TAB_COLOR[tab];
          const color     = isActive ? tabColor : Colors.textMuted;
          const bgColor   = isActive ? `${tabColor}18` : 'transparent';
          // Active tab: live count. Inactive tab: last-known cached count.
          const count     = isActive ? visibleEvents.length : tabCounts[tab];

          return (
            <Pressable
              key={tab}
              style={[
                styles.tabBtn,
                isActive && { borderColor: color, backgroundColor: bgColor },
              ]}
              onPress={() => handleTabPress(tab)}
              accessibilityRole="tab"
              accessibilityState={{ selected: isActive }}
            >
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
              {/* Always show badge when count is known (including 0) */}
              {count !== null && (
                <View style={[
                  styles.countBadge,
                  isActive
                    ? { backgroundColor: tabColor }
                    : { backgroundColor: Colors.borderSubtle },
                ]}>
                  <Text style={[
                    styles.countText,
                    !isActive && { color: Colors.textMuted },
                  ]}>
                    {count}
                  </Text>
                </View>
              )}
            </Pressable>
          );
        })}
      </View>

      {/* Content */}
      {isLoading ? (
        <FomoLoadingState />
      ) : error ? (
        <FomoErrorState message={error} onRetry={refetch} />
      ) : visibleEvents.length === 0 ? (
        <FomoEmptyState
          icon={TAB_EMPTY_ICON[activeTab]}
          message={EMPTY_COPY[activeTab].message}
          sub={EMPTY_COPY[activeTab].sub}
        />
      ) : (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={[
            styles.scrollContent,
            { paddingBottom: insets.bottom + Spacing['2xl'] },
          ]}
          showsVerticalScrollIndicator={false}
        >
          {sections.map((section) => (
            <View key={section.key} style={styles.section}>
              <View style={styles.sectionHeader}>
                <Text style={styles.sectionLabel}>{section.label.toUpperCase()}</Text>
                {section.dateRight ? (
                  <Text style={styles.sectionDate}>{section.dateRight}</Text>
                ) : null}
              </View>

              <View style={styles.sectionItems}>
                {section.events.map((event) => (
                  <MyEventListItem
                    key={event.id}
                    event={event}
                    intent={intentFor(event.id) ?? tabIntent}
                    isPending={isPending(event.id)}
                    onPress={() => setSelectedEvent(event)}
                  />
                ))}
              </View>
            </View>
          ))}
        </ScrollView>
      )}

      {/* Detail sheet */}
      <EventDetails
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
        intent={selectedEvent ? intentFor(selectedEvent.id) : null}
        onToggleIntent={
          selectedEvent ? (type) => toggleIntent(selectedEvent.id, type) : undefined
        }
        isPendingIntent={selectedEvent ? isPending(selectedEvent.id) : false}
      />
    </FomoScreen>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  header: {
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing.md,
    gap: 3,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderSubtle,
  },
  screenTitle: {
    fontFamily: Typography.font.extraBold,
    fontSize: Typography.size['2xl'],
    color: Colors.textPrimary,
  },
  screenSub: {
    fontFamily: Typography.font.regular,
    fontSize: Typography.size.sm,
    color: Colors.textMuted,
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
  },
  tabLabel: {
    fontFamily: Typography.font.semiBold,
    fontSize: Typography.size.sm,
  },
  countBadge: {
    borderRadius: Radii.full,
    minWidth: 16,
    height: 16,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
    marginLeft: 1,
  },
  countText: {
    fontFamily: Typography.font.bold,
    fontSize: 9,
    color: '#fff',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingTop: Spacing.base,
    paddingHorizontal: Spacing.base,
    gap: Spacing.lg,
  },
  section: {
    gap: Spacing.sm,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 2,
    paddingBottom: 2,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderSubtle,
  },
  sectionLabel: {
    fontFamily: Typography.font.bold,
    fontSize: 9,
    letterSpacing: 1.2,
    color: Colors.purple,
  },
  sectionDate: {
    fontFamily: Typography.font.regular,
    fontSize: 9,
    color: Colors.textMuted,
  },
  sectionItems: {
    gap: Spacing.sm,
  },
});
