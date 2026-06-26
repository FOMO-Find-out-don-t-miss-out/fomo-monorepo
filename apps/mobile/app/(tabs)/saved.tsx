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
import type { EventIntent, UiEvent } from '../../types/ui';

// ─── Tab config ───────────────────────────────────────────────────────────────

const TABS = ['Interested', 'Going'] as const;
type TabLabel = (typeof TABS)[number];

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
  const d       = new Date(isoDate);
  const today   = localDateKey(new Date());
  const tmrw    = localDateKey(new Date(Date.now() + 86_400_000));
  const key     = localDateKey(d);
  const dateRight = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  if (key === today) return { label: 'Today',    dateRight };
  if (key === tmrw)  return { label: 'Tomorrow', dateRight };

  return {
    label: d.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }),
    dateRight,
  };
}

function groupAndSort(events: UiEvent[]): DateSection[] {
  const sections = new Map<string, DateSection>();
  const noDate: UiEvent[] = [];

  for (const event of events) {
    if (!event.startTime) { noDate.push(event); continue; }
    const key = localDateKey(new Date(event.startTime));
    if (!sections.has(key)) {
      const { label, dateRight } = dateLabel(event.startTime);
      sections.set(key, { key, label, dateRight, events: [] });
    }
    sections.get(key)!.events.push(event);
  }

  for (const s of sections.values()) {
    s.events.sort((a, b) => (a.startTime ?? '').localeCompare(b.startTime ?? ''));
  }

  const sorted = [...sections.values()].sort((a, b) => a.key.localeCompare(b.key));
  if (noDate.length > 0) sorted.push({ key: 'zzzz', label: 'Date TBA', dateRight: '', events: noDate });
  return sorted;
}

// ─── Visible events helper ────────────────────────────────────────────────────
//
// Pure function — same logic for both tabs. Returns server events whose intent
// matches `tabIntent`, plus any registry events optimistically moved here that
// aren't in the server response yet.

function computeVisibleEvents(
  serverEvents: UiEvent[],
  intentState: Record<string, EventIntent>,
  registry:    Record<string, UiEvent>,
  tabIntent:   EventIntent,
): UiEvent[] {
  const currentIds = new Set(serverEvents.map((e) => e.id));

  // Pre-sync guard: keep events that haven't been synced into intentState yet
  // (one-render gap before the syncFromServer useEffect fires after a fresh fetch).
  const fromCurrentTab = serverEvents.filter((e) => {
    if (!(e.id in intentState)) return true;
    return intentState[e.id] === tabIntent;
  });

  // Registry events optimistically moved to this tab but not yet in server response.
  const fromOtherTabs = Object.values(registry).filter(
    (e) => !currentIds.has(e.id) && intentState[e.id] === tabIntent,
  );

  return [...fromCurrentTab, ...fromOtherTabs];
}

// ─── Screen ───────────────────────────────────────────────────────────────────

export default function MyEventsScreen() {
  const insets                                  = useSafeAreaInsets();
  const { accessToken, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab]               = useState<TabLabel>('Interested');
  const [selectedEvent, setSelectedEvent]       = useState<UiEvent | null>(null);

  // ── Two parallel hooks — one per tab, both fetch on mount ────────────────────
  //
  // Each hook is fixed to its relationship type — tab switching never triggers
  // a new network request. Both hooks fetch in parallel so both badge counts
  // are available immediately without requiring the user to visit each tab.

  const interestedHook = useMyEvents('interested', accessToken);
  const goingHook      = useMyEvents('going',      accessToken);

  const {
    state: intentState,
    syncFromServer,
    toggle: toggleIntent,
    isPending,
    intentFor,
  } = useRelationshipState(accessToken);

  // Merge both hooks' relationship seeds into intentState.
  // Backend mutual exclusivity means the two hooks will never return conflicting
  // intents for the same event.
  useEffect(() => {
    syncFromServer(interestedHook.relationships);
  }, [interestedHook.relationships, syncFromServer]);

  useEffect(() => {
    syncFromServer(goingHook.relationships);
  }, [goingHook.relationships, syncFromServer]);

  // ── Event registry ───────────────────────────────────────────────────────────
  //
  // Accumulates UiEvent objects from both hooks so computeVisibleEvents can
  // surface events in the other tab after an optimistic intent change, before
  // the server response for that tab has been refetched.

  const [eventRegistry, setEventRegistry] = useState<Record<string, UiEvent>>({});

  useEffect(() => {
    if (!accessToken) { setEventRegistry({}); return; }
  }, [accessToken]);

  useEffect(() => {
    if (interestedHook.events.length === 0) return;
    setEventRegistry((prev) => {
      const next = { ...prev };
      for (const e of interestedHook.events) next[e.id] = e;
      return next;
    });
  }, [interestedHook.events]);

  useEffect(() => {
    if (goingHook.events.length === 0) return;
    setEventRegistry((prev) => {
      const next = { ...prev };
      for (const e of goingHook.events) next[e.id] = e;
      return next;
    });
  }, [goingHook.events]);

  // ── Refetch on screen focus ──────────────────────────────────────────────────

  const refetchBoth = useCallback(() => {
    interestedHook.refetch();
    goingHook.refetch();
  }, [interestedHook.refetch, goingHook.refetch]);

  useFocusEffect(
    useCallback(() => { refetchBoth(); }, [refetchBoth]),
  );

  // ── Visible events for each tab ──────────────────────────────────────────────
  //
  // Computed for BOTH tabs so badge counts reflect optimistic intent changes
  // immediately (e.g. Interested count drops the moment an event is marked Going).

  const interestedVisible = useMemo(
    () => computeVisibleEvents(interestedHook.events, intentState, eventRegistry, 'interested'),
    [interestedHook.events, intentState, eventRegistry],
  );

  const goingVisible = useMemo(
    () => computeVisibleEvents(goingHook.events, intentState, eventRegistry, 'going'),
    [goingHook.events, intentState, eventRegistry],
  );

  const visibleEvents = activeTab === 'Interested' ? interestedVisible : goingVisible;

  const sections = useMemo(() => groupAndSort(visibleEvents), [visibleEvents]);

  // ── Tab counts ───────────────────────────────────────────────────────────────
  //
  // Null while loading so the badge renders nothing (not "0") during initial
  // fetch. Once loaded, reflects the visible count — matching what each list shows.

  const tabCounts: Record<TabLabel, number | null> = {
    Interested: interestedHook.isLoading ? null : interestedVisible.length,
    Going:      goingHook.isLoading      ? null : goingVisible.length,
  };

  // Active tab's loading / error states for the content area.
  const isLoading = activeTab === 'Interested' ? interestedHook.isLoading : goingHook.isLoading;
  const error     = activeTab === 'Interested' ? interestedHook.error     : goingHook.error;

  const tabIntent = TAB_INTENT[activeTab];

  const handleTabPress = useCallback((tab: TabLabel) => {
    setActiveTab(tab);
    setSelectedEvent(null);
  }, []);

  // ── Auth guards ─────────────────────────────────────────────────────────────

  if (authLoading) {
    return <FomoScreen><FomoLoadingState /></FomoScreen>;
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
          const count     = tabCounts[tab];

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
                <Heart size={13} color={color} fill={isActive ? color : 'transparent'} strokeWidth={1.5} />
              )}
              {tab === 'Going' && (
                <CheckCircle size={13} color={color} strokeWidth={1.5} />
              )}
              <Text style={[styles.tabLabel, { color }]}>{tab}</Text>
              {/* Badge renders only when count is known (null = loading = no badge) */}
              {count !== null && (
                <View style={[
                  styles.countBadge,
                  isActive
                    ? { backgroundColor: tabColor }
                    : { backgroundColor: Colors.borderSubtle },
                ]}>
                  <Text style={[styles.countText, !isActive && { color: Colors.textMuted }]}>
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
        <FomoErrorState message={error} onRetry={refetchBoth} />
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
          selectedEvent
            ? (type) => { void toggleIntent(selectedEvent.id, type).finally(refetchBoth); }
            : undefined
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
    minWidth: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 5,
    marginLeft: 1,
  },
  countText: {
    fontFamily: Typography.font.bold,
    fontSize: 10,
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
