import { CalendarDays, CheckCircle, Heart } from 'lucide-react-native';
import { useFocusEffect } from 'expo-router';
import React, { useCallback, useMemo, useRef, useState } from 'react';
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
import { getRelationshipRevision, setEventIntent } from '../../utils/event-relationships-api';
import {
  perfCountRender,
  perfEnabled,
  perfLog,
  perfMark,
  perfSince,
  usePerfScreenFocus,
} from '../../utils/performance-debug';
import { Colors, Radii, Spacing, Typography } from '../../theme';
import type { EventIntent, UiEvent } from '../../types/ui';

// ─── Tab config ───────────────────────────────────────────────────────────────

const TABS = ['Interested', 'Going'] as const;
type TabLabel = (typeof TABS)[number];

const TAB_INTENT: Record<TabLabel, 'interested' | 'going'> = {
  Interested: 'interested',
  Going:      'going',
};

const TAB_COLOR: Record<TabLabel, string> = {
  Interested: Colors.intentInterested,
  Going:      Colors.intentGoing,
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
  Interested: <Heart       size={44} color={Colors.intentInterested} strokeWidth={1.2} />,
  Going:      <CheckCircle size={44} color={Colors.intentGoing} strokeWidth={1.2} />,
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

// ─── Screen ───────────────────────────────────────────────────────────────────

export default function MyEventsScreen() {
  perfCountRender('MyEventsScreen');
  usePerfScreenFocus('my-events');

  const insets                                  = useSafeAreaInsets();
  const { accessToken, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab]               = useState<TabLabel>('Interested');
  const [selectedEvent, setSelectedEvent]       = useState<UiEvent | null>(null);
  const [pendingEventId, setPendingEventId]     = useState<string | null>(null);

  // Two independent hooks — one per relationship type.
  // Both fetch in parallel so badge counts are available without tab switching.
  const interestedHook = useMyEvents('interested', accessToken);
  const goingHook      = useMyEvents('going',      accessToken);

  const refetchInterested = interestedHook.refetch;
  const refetchGoing      = goingHook.refetch;
  const refetchBoth = useCallback((reason?: string) => {
    refetchInterested(reason);
    refetchGoing(reason);
  }, [refetchInterested, refetchGoing]);

  // Cross-screen relationship consistency (FOMO-178, mirrors the FOMO-177
  // Discover mechanism): rather than unconditionally refetching both lists on
  // every focus, track the shared mutation-revision counter (bumped by any
  // successful setEventIntent call, from Discover or My Events) and only
  // refetch when it has moved past what My Events last synchronized to — a
  // My-Events-originated mutation advances this ref itself (see
  // handleToggleIntent) so it never refetches its own already-applied change.
  const lastSyncedRevisionRef = useRef(getRelationshipRevision());

  useFocusEffect(
    useCallback(() => {
      const currentRevision = getRelationshipRevision();
      if (currentRevision !== lastSyncedRevisionRef.current) {
        lastSyncedRevisionRef.current = currentRevision;
        refetchBoth('external-invalidation');
      }
    }, [refetchBoth]),
  );

  // ── Intent for the selected event ────────────────────────────────────────────
  //
  // Derived from list membership, not a separate state. An event is either
  // in the interested list, the going list, or neither.

  const selectedEventIntent = useMemo((): EventIntent => {
    if (!selectedEvent) return null;
    // going wins (matches dedup rule above)
    if (goingHook.events.some((e) => e.id === selectedEvent.id))       return 'going';
    if (interestedHook.events.some((e) => e.id === selectedEvent.id))  return 'interested';
    return null;
  }, [selectedEvent, interestedHook.events, goingHook.events]);

  // ── Toggle ───────────────────────────────────────────────────────────────────
  //
  // Server-authoritative: setEventIntent only resolves on a server-confirmed
  // success, so its result is already canonical. The mutated event is always
  // already fully known here (it's already rendered in one of the two lists),
  // so the result is applied by moving that exact event object between the
  // two hooks' local state — no refetch needed (FOMO-178).

  const handleToggleIntent = useCallback(async (type: 'interested' | 'going') => {
    if (!accessToken || !selectedEvent || pendingEventId) return;
    const eventId       = selectedEvent.id;
    const currentIntent = selectedEventIntent;
    const tapMark       = perfMark();
    perfLog('intent-toggle', { screen: 'my-events', phase: 'tap', type });
    setPendingEventId(eventId);
    try {
      const nextIntent = await setEventIntent(eventId, currentIntent, type, accessToken);
      perfLog('intent-toggle', {
        screen: 'my-events',
        phase: 'mutation-done',
        duration_ms: perfSince(tapMark),
      });

      if (currentIntent === 'interested' && nextIntent !== 'interested') {
        interestedHook.setEvents((prev) => prev.filter((e) => e.id !== eventId));
      }
      if (currentIntent === 'going' && nextIntent !== 'going') {
        goingHook.setEvents((prev) => prev.filter((e) => e.id !== eventId));
      }
      if (nextIntent === 'interested' && currentIntent !== 'interested') {
        interestedHook.setEvents((prev) =>
          prev.some((e) => e.id === eventId) ? prev : [...prev, selectedEvent],
        );
      }
      if (nextIntent === 'going' && currentIntent !== 'going') {
        goingHook.setEvents((prev) =>
          prev.some((e) => e.id === eventId) ? prev : [...prev, selectedEvent],
        );
      }
      // Advance our synced revision past the bump setEventIntent just made,
      // so the next focus doesn't treat this self-originated change as an
      // external invalidation requiring a refetch.
      lastSyncedRevisionRef.current = getRelationshipRevision();
      perfLog('intents-reconcile', { screen: 'my-events', mode: 'local' });

      setSelectedEvent(null);
    } catch {
      // silent — user can retry by tapping again
    } finally {
      setPendingEventId(null);
      perfLog('intent-toggle', {
        screen: 'my-events',
        phase: 'settled',
        duration_ms: perfSince(tapMark),
      });
    }
  // interestedHook.setEvents / goingHook.setEvents are useState setters —
  // referentially stable across renders — so depending on the whole hook
  // objects (which are new literals every render) would defeat memoization.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    accessToken,
    selectedEvent,
    pendingEventId,
    selectedEventIntent,
    interestedHook.setEvents,
    goingHook.setEvents,
  ]);

  // ── Derived state ─────────────────────────────────────────────────────────────
  //
  // Defensive dedup: if backend returns an event in both lists (only possible
  // with stale legacy DB rows — the service enforces mutual exclusivity on every
  // write), going wins (mirrors the backend's own normalization rule) and the
  // event is removed from the interested list.

  const goingIds = useMemo(
    () => new Set(goingHook.events.map((e) => e.id)),
    [goingHook.events],
  );

  const deduplicatedInterested = useMemo(
    () => interestedHook.events.filter((e) => !goingIds.has(e.id)),
    [interestedHook.events, goingIds],
  );

  const interestedEvents = deduplicatedInterested;
  const goingEvents      = goingHook.events;

  const visibleEvents = activeTab === 'Interested' ? interestedEvents : goingEvents;
  // isInitialLoading is only true before this tab's data has EVER loaded —
  // a background refresh (e.g. external-invalidation refetch) never flips it
  // back true, so previously loaded rows stay visible during refetch
  // (FOMO-178, requirement: don't replace a populated list with a spinner).
  const isInitialLoading =
    activeTab === 'Interested' ? interestedHook.isInitialLoading : goingHook.isInitialLoading;
  const error = activeTab === 'Interested' ? interestedHook.error : goingHook.error;
  // Only treat an error as screen-replacing when there's no cached data to
  // fall back to — a background refresh failure with existing rows keeps
  // showing those rows instead of a false empty/error state.
  const showError = error != null && visibleEvents.length === 0;

  // Counts derived from authoritative list lengths; null while never-loaded.
  const tabCounts: Record<TabLabel, number | null> = {
    Interested: interestedHook.isInitialLoading ? null : interestedEvents.length,
    Going:      goingHook.isInitialLoading      ? null : goingEvents.length,
  };

  const sections = useMemo(() => groupAndSort(visibleEvents), [visibleEvents]);

  // Rows actually stable/rendered for the active tab — distinct from initial
  // loading and from a background refresh in flight (FOMO-178).
  React.useEffect(() => {
    if (perfEnabled && !isInitialLoading && !showError) {
      perfLog('my-events-render', { tab: activeTab, rows: visibleEvents.length });
    }
  }, [isInitialLoading, showError, activeTab, visibleEvents.length]);

  const handleTabPress = useCallback((tab: TabLabel) => {
    setActiveTab(tab);
    setSelectedEvent(null);
  }, []);

  // Stable across renders unless the active tab's own event list changes —
  // lets memoized MyEventListItem rows bail out of re-render when an
  // unrelated background refresh (e.g. the other tab's data) updates
  // (FOMO-178, mirrors the FOMO-175 Discover card-press pattern).
  const handleRowSelect = useCallback(
    (eventId: string) => {
      const found = visibleEvents.find((e) => e.id === eventId);
      if (found) setSelectedEvent(found);
    },
    [visibleEvents],
  );

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
      {isInitialLoading ? (
        <FomoLoadingState />
      ) : showError ? (
        <FomoErrorState message={error ?? 'Failed to load events'} onRetry={() => refetchBoth('manual-refresh')} />
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
                    intent={TAB_INTENT[activeTab]}
                    isPending={pendingEventId === event.id}
                    onPress={handleRowSelect}
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
        intent={selectedEventIntent}
        onToggleIntent={handleToggleIntent}
        isPendingIntent={selectedEvent ? pendingEventId === selectedEvent.id : false}
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
    color: Colors.textPrimary,
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
    color: Colors.brandPrimary,
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
