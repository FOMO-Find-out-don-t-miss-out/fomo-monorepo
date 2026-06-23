import {
  Bookmark,
  CalendarDays,
  CheckCircle,
  Heart,
} from 'lucide-react-native';
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
import type { UiEvent } from '../../types/ui';

// ─── Tab config ───────────────────────────────────────────────────────────────

const TABS = ['Saved', 'Interested', 'Going'] as const;
type TabLabel = (typeof TABS)[number];

const TAB_TYPE: Record<TabLabel, RelationshipType> = {
  Saved:      'saved',
  Interested: 'interested',
  Going:      'going',
};

const TAB_COLOR: Record<TabLabel, string> = {
  Saved:      Colors.purple,
  Interested: Colors.magenta,
  Going:      Colors.success,
};

const EMPTY_COPY: Record<TabLabel, { message: string; sub: string }> = {
  Saved: {
    message: 'Nothing saved yet',
    sub:     'Tap the bookmark on any event to save it here for later.',
  },
  Interested: {
    message: 'No interested events',
    sub:     'Open an event and tap Interested when something catches your eye.',
  },
  Going: {
    message: 'No plans yet',
    sub:     "Mark yourself as Going when you're committed — your plans live here.",
  },
};

const TAB_EMPTY_ICON: Record<TabLabel, React.ReactNode> = {
  Saved:      <Bookmark     size={44} color={Colors.purple}  strokeWidth={1.2} />,
  Interested: <Heart        size={44} color={Colors.magenta} strokeWidth={1.2} />,
  Going:      <CheckCircle  size={44} color={Colors.success} strokeWidth={1.2} />,
};

// ─── Date grouping ────────────────────────────────────────────────────────────

interface DateSection {
  key: string;       // YYYY-MM-DD for sort, "zzzz" for no-date
  label: string;     // "Today", "Tomorrow", "Fri, 27 Jun"
  dateRight: string; // e.g. "Jun 24"
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

  const dateRight = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  if (key === today)    return { label: 'Today',    dateRight };
  if (key === tomorrow) return { label: 'Tomorrow', dateRight };

  const label = d.toLocaleDateString('en-US', {
    weekday: 'short',
    day:     'numeric',
    month:   'short',
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

  // Sort events within each section by startTime
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
  const [activeTab, setActiveTab]               = useState<TabLabel>('Saved');
  const [selectedEvent, setSelectedEvent]       = useState<UiEvent | null>(null);

  const { events, relationships: batchRel, isLoading, error, refetch } = useMyEvents(
    TAB_TYPE[activeTab],
    accessToken,
  );

  const {
    state: relState,
    syncFromServer,
    toggle: toggleRel,
    isPending: isRelPending,
  } = useRelationshipState(accessToken);

  useEffect(() => {
    syncFromServer(batchRel);
  }, [batchRel, syncFromServer]);

  useFocusEffect(
    useCallback(() => {
      refetch();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTab]),
  );

  // Events still in the list: filter out any whose optimistic state no longer
  // includes the current tab's relationship type.
  const visibleEvents = useMemo(
    () =>
      events.filter((e) => {
        const rels = relState[e.id];
        if (rels === undefined) return true;
        return rels.includes(TAB_TYPE[activeTab]);
      }),
    [events, relState, activeTab],
  );

  const sections = useMemo(() => groupAndSort(visibleEvents), [visibleEvents]);

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
          sub="Your saved events, interest, and plans live here."
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
        <Text style={styles.screenSub}>Your upcoming plans and saved discoveries</Text>
      </View>

      {/* Segmented tab bar */}
      <View style={styles.tabBar}>
        {TABS.map((tab) => {
          const isActive = tab === activeTab;
          const color    = isActive ? TAB_COLOR[tab] : Colors.textMuted;
          const bgColor  = isActive ? `${TAB_COLOR[tab]}18` : 'transparent';

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
              {isActive && visibleEvents.length > 0 && (
                <View style={[styles.countBadge, { backgroundColor: color }]}>
                  <Text style={styles.countText}>{visibleEvents.length}</Text>
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
              {/* Date section header */}
              <View style={styles.sectionHeader}>
                <Text style={styles.sectionLabel}>{section.label.toUpperCase()}</Text>
                {section.dateRight ? (
                  <Text style={styles.sectionDate}>{section.dateRight}</Text>
                ) : null}
              </View>

              {/* Event rows */}
              <View style={styles.sectionItems}>
                {section.events.map((event) => (
                  <MyEventListItem
                    key={event.id}
                    event={event}
                    relationships={relState[event.id] ?? [TAB_TYPE[activeTab]]}
                    pendingTypes={
                      (['saved', 'interested', 'going'] as const).filter((t) =>
                        isRelPending(event.id, t),
                      )
                    }
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
        relationships={
          selectedEvent
            ? (relState[selectedEvent.id] ?? [TAB_TYPE[activeTab]])
            : []
        }
        onToggleRelationship={
          selectedEvent ? (type) => toggleRel(selectedEvent.id, type) : undefined
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
  // ── Header ──────────────────────────────────────────────────────────────────
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

  // ── Tab bar ─────────────────────────────────────────────────────────────────
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

  // ── List ────────────────────────────────────────────────────────────────────
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
