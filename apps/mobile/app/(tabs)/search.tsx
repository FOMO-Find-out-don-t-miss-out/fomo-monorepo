import { useLocalSearchParams } from 'expo-router';
import { MapPin, Search, SlidersHorizontal, User, Users, X } from 'lucide-react-native';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type ListRenderItemInfo,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ExploreEventListItem } from '../../components/fomo/explore-event-list-item';
import { EventDetails } from '../../components/fomo/event-details';
import { ExploreFilterModal } from '../../components/fomo/explore-filter-modal';
import { ExploreSearchInput } from '../../components/fomo/explore-search-input';
import { FomoErrorState, FomoLoadingState, FomoScreen } from '../../components/ui';
import { useAuth } from '../../hooks/use-auth';
import { useDeviceLocation } from '../../hooks/use-device-location';
import { useEventRelationships } from '../../hooks/use-event-relationships';
import { useExploreSearch, type ExploreEvent } from '../../hooks/use-explore-search';
import { setEventIntent } from '../../utils/event-relationships-api';
import {
  DEFAULT_EXPLORE_FILTERS,
  activeFilterGroupCount,
  backendCategoryLabel,
  datePresetLabel,
  hasActiveFilters,
  parseExploreHandoffLocation,
  type ExploreActiveFilters,
} from '../../utils/explore-filters';
import { usePerfScreenFocus } from '../../utils/performance-debug';
import { Colors, Spacing, Typography } from '../../theme';
import type { EventIntent } from '../../types/ui';

// ─── Entity scopes ────────────────────────────────────────────────────────────

type EntityScope = 'all' | 'events' | 'organizers' | 'people' | 'places';

const ENTITY_SCOPES: readonly { key: EntityScope; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'events', label: 'Events' },
  { key: 'organizers', label: 'Organizers' },
  { key: 'people', label: 'People' },
  { key: 'places', label: 'Places' },
];

function formatCount(count: number, hasMore: boolean): string {
  if (count === 0) return '0';
  return hasMore ? `${count}+` : `${count}`;
}

// ─── Bottom tab bar clearance ─────────────────────────────────────────────────
//
// The floating tab bar (apps/mobile/app/(tabs)/_layout.tsx) overlays the
// bottom of every tab screen. Its total height from the screen bottom edge is:
//
//   navWrapper.paddingTop (8)
//   + pill (borderWidth×2 + row paddingVertical×2 + tab content ≈ 74)
//   + navWrapper.paddingBottom (max(insets.bottom, 16) + 8)
//   = 90 + Math.max(insets.bottom, 16)
//
// We add 16 px breathing room so the last result card and loading-more footer
// are never hidden behind the floating pill.

const TAB_BAR_BASE_HEIGHT = 90;

function listBottomPadding(insetsBottom: number): number {
  return TAB_BAR_BASE_HEIGHT + Math.max(insetsBottom, 16) + Spacing.base;
}

// ─── Screen ───────────────────────────────────────────────────────────────────

export default function ExploreScreen() {
  usePerfScreenFocus('search');
  const insets = useSafeAreaInsets();
  const { accessToken } = useAuth();

  const {
    query,
    setQuery,
    activeFilters,
    applyFilters,
    status,
    events,
    error,
    loadingMore,
    hasMore,
    loadMore,
    retry,
  } = useExploreSearch();

  // Location is only requested once the user opts in via the filter modal's
  // Near me toggle, or once a valid Discover handoff arrives (below) —
  // `enabled` gates use-device-location's own permission flow so opening
  // Explore on its own never eagerly prompts for location.
  const [locationRequested, setLocationRequested] = useState(false);

  // Discover → Explore handoff (FOMO-172 Phase 4B). Consumed exactly once per
  // distinct `handoff` nonce: re-renders and tab refocuses that still carry
  // the same params (no new navigation occurred) must never reapply and
  // clobber filters the user has since changed themselves. Keyed only on the
  // primitive `params.handoff` string, never the whole `params` object (a
  // new reference every render).
  const params = useLocalSearchParams<{
    lat?: string;
    lng?: string;
    radiusKm?: string;
    handoff?: string;
  }>();
  const consumedHandoffRef = useRef<string | null>(null);

  useEffect(() => {
    const handoff = params.handoff;
    if (!handoff || handoff === consumedHandoffRef.current) return;
    consumedHandoffRef.current = handoff;

    const handoffLocation = parseExploreHandoffLocation({
      lat: params.lat,
      lng: params.lng,
      radiusKm: params.radiusKm,
    });
    if (!handoffLocation) return; // no valid location handed off — leave filters untouched

    // Start Explore's own location resolution too (resolves near-instantly,
    // since Discover only sends real coordinates when permission is already
    // granted) so the filter modal's Near me toggle/Apply reflect a settled
    // 'granted' status immediately rather than staying stuck on 'pending'.
    setLocationRequested(true);
    applyFilters({
      ...DEFAULT_EXPLORE_FILTERS,
      nearMe: true,
      location: { lat: handoffLocation.lat, lng: handoffLocation.lng },
      radiusKm: handoffLocation.radiusKm,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.handoff]);

  const { location: deviceLocation, status: locationStatus } = useDeviceLocation(
    locationRequested,
  );
  const currentLocation = locationStatus === 'granted' ? { lat: deviceLocation.lat, lng: deviceLocation.lng } : null;

  const [isFilterModalOpen, setIsFilterModalOpen] = useState(false);

  const [selectedEvent, setSelectedEvent] = useState<ExploreEvent | null>(null);
  const [pendingEventId, setPendingEventId] = useState<string | null>(null);

  // Relationship state is resolved only for the single currently-open event
  // (reusing the existing batch endpoint/hook with a one-element id list) —
  // never one request per visible result card (no N+1 on the list itself).
  const selectedEventIds = useMemo(
    () => (selectedEvent ? [selectedEvent.id] : []),
    [selectedEvent],
  );
  const { intents } = useEventRelationships(selectedEventIds, accessToken);

  // Applied immediately after a successful mutation, mirroring Discover's/My
  // Events' localIntents pattern — bridges the gap until the next server
  // refetch (which for a single already-open event may never come, since
  // selectedEvent.id doesn't change on toggle). Scoped to one event because
  // Explore only ever has one event selected at a time.
  const [localIntentOverride, setLocalIntentOverride] = useState<{
    eventId: string;
    intent: EventIntent;
  } | null>(null);

  const selectedIntent = selectedEvent
    ? localIntentOverride && localIntentOverride.eventId === selectedEvent.id
      ? localIntentOverride.intent
      : (intents[selectedEvent.id] ?? null)
    : null;

  const handleEventSelect = useCallback(
    (eventId: string) => {
      const found = events.find((e) => e.id === eventId);
      if (found) {
        setSelectedEvent(found);
        // A previous event's override must never leak into a new selection.
        setLocalIntentOverride(null);
      }
    },
    [events],
  );

  const handleToggleIntent = useCallback(
    async (type: 'interested' | 'going') => {
      if (!accessToken || !selectedEvent || pendingEventId) return;
      const eventId = selectedEvent.id;
      const currentIntent = intents[eventId] ?? null;
      setPendingEventId(eventId);
      try {
        const nextIntent = await setEventIntent(eventId, currentIntent, type, accessToken);
        setLocalIntentOverride({ eventId, intent: nextIntent });
      } catch {
        // silent — user can retry by tapping again (matches Discover/My Events)
      } finally {
        setPendingEventId(null);
      }
    },
    [accessToken, selectedEvent, pendingEventId, intents],
  );

  const keyExtractor = useCallback((event: ExploreEvent) => event.id, []);

  const renderItem = useCallback(
    ({ item }: ListRenderItemInfo<ExploreEvent>) => (
      <ExploreEventListItem event={item} onPress={handleEventSelect} />
    ),
    [handleEventSelect],
  );

  const listFooter = loadingMore ? (
    <View style={styles.footer}>
      <ActivityIndicator color={Colors.brandPrimary} />
    </View>
  ) : null;

  const trimmedQuery = query.trim();
  const isTextSearch = trimmedQuery.length >= 2;
  const filtersActive = hasActiveFilters(activeFilters);
  const filterBadgeCount = activeFilterGroupCount(activeFilters);

  // ── Entity scope ──────────────────────────────────────────────────────────

  const [entityScope, setEntityScope] = useState<EntityScope>('all');
  const tabScrollRef = useRef<ScrollView>(null);
  const tabPositionsRef = useRef<Record<string, number>>({});

  const eventCountLabel = formatCount(events.length, hasMore);

  const scopeCount = useCallback(
    (scope: EntityScope): string => {
      switch (scope) {
        case 'all':
        case 'events':
          return eventCountLabel;
        case 'organizers':
        case 'people':
        case 'places':
          return '0';
      }
    },
    [eventCountLabel],
  );

  // Auto-scroll the selected tab into view when the user taps a scope.
  const handleScopeChange = useCallback(
    (scope: EntityScope, _index: number) => {
      setEntityScope(scope);
      // Small delay so layout settles before we measure scroll position.
      setTimeout(() => {
        const x = tabPositionsRef.current[scope];
        if (x !== undefined && tabScrollRef.current) {
          tabScrollRef.current.scrollTo({ x: Math.max(0, x - 16), animated: true });
        }
      }, 0);
    },
    [],
  );

  // ── Active filter removal ─────────────────────────────────────────────────

  const removeCategory = useCallback(
    (category: string) => {
      applyFilters({
        ...activeFilters,
        categories: activeFilters.categories.filter((c) => c !== category),
      });
    },
    [activeFilters, applyFilters],
  );

  const removeDatePreset = useCallback(() => {
    applyFilters({
      ...activeFilters,
      datePreset: 'any',
      dateBounds: { dateFrom: null, dateTo: null },
    });
  }, [activeFilters, applyFilters]);

  const removeNearMe = useCallback(() => {
    applyFilters({ ...activeFilters, nearMe: false, location: null });
  }, [activeFilters, applyFilters]);

  const clearAll = useCallback(() => {
    applyFilters(DEFAULT_EXPLORE_FILTERS);
  }, [applyFilters]);

  const handleApplyFilters = useCallback(
    (next: ExploreActiveFilters) => {
      applyFilters(next);
      setIsFilterModalOpen(false);
    },
    [applyFilters],
  );

  // ── Derived UI state ──────────────────────────────────────────────────────

  const showResults = status === 'results' && (entityScope === 'all' || entityScope === 'events');
  const showFutureEmpty = status !== 'loading' && status !== 'error' &&
    (entityScope === 'organizers' || entityScope === 'people' || entityScope === 'places');
  // Idle/too-short/loading when the eligible scope produces no results yet
  const showNonResultState = !showResults && !showFutureEmpty;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <FomoScreen>
      {/* ── Fixed shell ──────────────────────────────────────────────────── */}
      <View style={[styles.shell, { paddingTop: insets.top + Spacing.base }]}>
        {/* Title */}
        <Text style={styles.title}>Explore</Text>

        {/* Search + filter row */}
        <View style={styles.searchRow}>
          <View style={styles.searchInputWrap}>
            <ExploreSearchInput value={query} onChangeText={setQuery} onClear={() => setQuery('')} />
          </View>
          <Pressable
            onPress={() => setIsFilterModalOpen(true)}
            style={({ pressed }) => [
              styles.filterBtn,
              pressed && styles.filterBtnPressed,
            ]}
            accessibilityRole="button"
            accessibilityLabel={`Filters${filterBadgeCount > 0 ? `, ${filterBadgeCount} active` : ''}`}
          >
            <SlidersHorizontal size={20} color={Colors.textSecondary} strokeWidth={2} />
            {filterBadgeCount > 0 && (
              <View style={styles.filterBadge}>
                <Text style={styles.filterBadgeText}>{filterBadgeCount}</Text>
              </View>
            )}
          </Pressable>
        </View>

        {/* Entity scope tabs */}
        <View style={styles.tabsContainer}>
          <ScrollView
            ref={tabScrollRef}
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.tabsContent}
          >
            {ENTITY_SCOPES.map((scope, index) => {
              const active = entityScope === scope.key;
              return (
                <Pressable
                  key={scope.key}
                  onPress={() => handleScopeChange(scope.key, index)}
                  style={styles.tab}
                  accessibilityRole="tab"
                  accessibilityState={{ selected: active }}
                  onLayout={(e) => {
                    tabPositionsRef.current[scope.key] = e.nativeEvent.layout.x;
                  }}
                >
                  <Text
                    style={[
                      styles.tabLabel,
                      active && styles.tabLabelActive,
                    ]}
                    numberOfLines={1}
                  >
                    {scope.label}
                  </Text>
                  <Text
                    style={[
                      styles.tabCount,
                      active && styles.tabCountActive,
                    ]}
                  >
                    {scopeCount(scope.key)}
                  </Text>
                  {active && <View style={styles.tabIndicator} />}
                </Pressable>
              );
            })}
          </ScrollView>
        </View>

        {/* Active filter chips */}
        {filtersActive && (
          <View style={styles.chipsRow}>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              style={styles.chipsScroll}
              contentContainerStyle={styles.chipsScrollContent}
            >
              {activeFilters.categories.map((category) => (
                <FilterChip
                  key={category}
                  label={backendCategoryLabel(category)}
                  onRemove={() => removeCategory(category)}
                />
              ))}
              {activeFilters.datePreset !== 'any' && (
                <FilterChip
                  label={datePresetLabel(activeFilters.datePreset)}
                  onRemove={removeDatePreset}
                />
              )}
              {activeFilters.nearMe && (
                <FilterChip
                  label={`Near me · ${activeFilters.radiusKm} km`}
                  onRemove={removeNearMe}
                />
              )}
            </ScrollView>
            <Pressable onPress={clearAll} style={styles.clearAllBtn}>
              <Text style={styles.clearAll}>Clear all</Text>
            </Pressable>
          </View>
        )}
      </View>

      {/* ── Result / state area ───────────────────────────────────────────── */}
      {showResults && (
        <>
          <View style={styles.sectionRow}>
            <Text style={styles.sectionHeading}>Events</Text>
          </View>
          <FlatList
            data={events}
            keyExtractor={keyExtractor}
            renderItem={renderItem}
            contentContainerStyle={[
              styles.listContent,
              { paddingBottom: listBottomPadding(insets.bottom) },
            ]}
            onEndReached={loadMore}
            onEndReachedThreshold={0.5}
            ListFooterComponent={listFooter}
            keyboardDismissMode="on-drag"
            keyboardShouldPersistTaps="handled"
          />
        </>
      )}

      {showFutureEmpty && (
        <View style={[styles.stateArea, { paddingBottom: listBottomPadding(insets.bottom) }]}>
          <FutureEntityState scope={entityScope} />
        </View>
      )}

      {showNonResultState && (
        <View style={[styles.stateArea, { paddingBottom: listBottomPadding(insets.bottom) }]}>
          {status === 'idle' && (
            <StateContent
              icon={<Search size={40} color={Colors.textMuted} strokeWidth={1.5} />}
              heading="Search events or browse with filters"
              body="Search by event name, venue, or organizer. Use filters to browse by category, date, or distance."
            />
          )}

          {status === 'too-short' && (
            <StateContent
              icon={<Search size={40} color={Colors.textMuted} strokeWidth={1.5} />}
              heading="Type at least 2 characters to search"
            />
          )}

          {status === 'loading' && <FomoLoadingState />}

          {status === 'error' && (
            <FomoErrorState message={error ?? 'Could not load results'} onRetry={retry} />
          )}

          {status === 'empty' && (
            <StateContent
              icon={<Search size={40} color={Colors.textMuted} strokeWidth={1.5} />}
              heading="No events match your search and filters"
              body={isTextSearch ? `Nothing found for "${trimmedQuery}".` : 'Try different filters.'}
            />
          )}
        </View>
      )}

      <ExploreFilterModal
        visible={isFilterModalOpen}
        initialFilters={activeFilters}
        locationStatus={locationStatus}
        currentLocation={currentLocation}
        onApply={handleApplyFilters}
        onCancel={() => setIsFilterModalOpen(false)}
        onNearMeEnabled={() => setLocationRequested(true)}
      />

      <EventDetails
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
        intent={accessToken ? selectedIntent : null}
        onToggleIntent={accessToken ? handleToggleIntent : undefined}
        isPendingIntent={selectedEvent ? pendingEventId === selectedEvent.id : false}
      />
    </FomoScreen>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function FilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <View style={styles.chip}>
      <Text style={styles.chipLabel}>{label}</Text>
      <Pressable onPress={onRemove} hitSlop={8} accessibilityRole="button" accessibilityLabel={`Remove ${label}`}>
        <X size={12} color={Colors.textSecondary} strokeWidth={2.5} />
      </Pressable>
    </View>
  );
}

function StateContent({
  icon,
  heading,
  body,
}: {
  icon: React.ReactNode;
  heading: string;
  body?: string;
}) {
  return (
    <View style={styles.stateContent}>
      {icon}
      <Text style={styles.stateHeading}>{heading}</Text>
      {body ? <Text style={styles.stateBody}>{body}</Text> : null}
    </View>
  );
}

function FutureEntityState({ scope }: { scope: EntityScope }) {
  const { icon: Icon, heading, body } = useMemo(() => {
    switch (scope) {
      case 'organizers':
        return {
          icon: User,
          heading: 'No organizers found',
          body: 'Organizer discovery is being prepared.',
        };
      case 'people':
        return {
          icon: Users,
          heading: 'No people found',
          body: 'People discovery will appear here.',
        };
      case 'places':
        return {
          icon: MapPin,
          heading: 'No places found',
          body: 'Place search is being connected.',
        };
      default:
        return { icon: Search, heading: '', body: '' };
    }
  }, [scope]);

  return (
    <View style={styles.stateContent}>
      <Icon size={40} color={Colors.textMuted} strokeWidth={1.5} />
      <Text style={styles.stateHeading}>{heading}</Text>
      <Text style={styles.stateBody}>{body}</Text>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  // ── Shell ──────────────────────────────────────────────────────────────────
  shell: {
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing.sm,
  },
  title: {
    fontFamily: Typography.font.extraBold,
    fontSize: Typography.size['2xl'],
    color: Colors.textPrimary,
    marginBottom: Spacing.md,
  },

  // ── Search + filter row ────────────────────────────────────────────────────
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  searchInputWrap: {
    flex: 1,
    minWidth: 0,
  },
  filterBtn: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.borderGlass,
    backgroundColor: Colors.surfaceGlass,
  },
  filterBtnPressed: {
    borderColor: Colors.borderFocus,
    backgroundColor: Colors.purpleDim,
  },
  filterBadge: {
    position: 'absolute',
    top: -4,
    right: -4,
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    paddingHorizontal: 3,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.brandPrimary,
  },
  filterBadgeText: {
    fontFamily: Typography.font.bold,
    fontSize: 9,
    color: Colors.textPrimary,
  },

  // ── Entity tabs ────────────────────────────────────────────────────────────
  tabsContainer: {
    marginTop: Spacing.lg,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.borderSubtle,
  },
  tabsContent: {
    paddingHorizontal: 0,
    gap: 0,
  },
  tab: {
    position: 'relative',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    minHeight: 44,
  },
  tabLabel: {
    fontFamily: Typography.font.medium,
    fontSize: Typography.size.md,
    color: Colors.textMuted,
  },
  tabLabelActive: {
    fontFamily: Typography.font.semiBold,
    color: Colors.textPrimary,
  },
  tabCount: {
    fontFamily: Typography.font.medium,
    fontSize: Typography.size.xs,
    color: Colors.textMuted,
  },
  tabCountActive: {
    color: Colors.brandPrimary,
  },
  tabIndicator: {
    position: 'absolute',
    bottom: 0,
    left: Spacing.md,
    right: Spacing.md,
    height: 2,
    backgroundColor: Colors.brandPrimary,
    borderTopLeftRadius: 1,
    borderTopRightRadius: 1,
  },

  // ── Active filter chips ────────────────────────────────────────────────────
  chipsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 40,
    marginTop: Spacing.sm,
  },
  chipsScroll: {
    flex: 1,
  },
  chipsScrollContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    paddingHorizontal: Spacing.md,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: Colors.borderFocus,
    backgroundColor: Colors.purpleDim,
  },
  chipLabel: {
    fontFamily: Typography.font.medium,
    fontSize: Typography.size.sm,
    color: Colors.textPrimary,
  },
  clearAllBtn: {
    paddingLeft: Spacing.sm,
  },
  clearAll: {
    fontFamily: Typography.font.semiBold,
    fontSize: Typography.size.sm,
    color: Colors.textSecondary,
    textDecorationLine: 'underline',
  },

  // ── Section heading ────────────────────────────────────────────────────────
  sectionRow: {
    paddingHorizontal: Spacing.base,
    paddingTop: Spacing.sm,
    paddingBottom: Spacing.xs,
  },
  sectionHeading: {
    fontFamily: Typography.font.bold,
    fontSize: Typography.size.sm,
    color: Colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },

  // ── Result list ────────────────────────────────────────────────────────────
  listContent: {
    paddingTop: Spacing.sm,
  },
  footer: {
    paddingVertical: Spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },

  // ── State area ─────────────────────────────────────────────────────────────
  stateArea: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: Spacing.base,
  },
  stateContent: {
    alignItems: 'center',
    gap: Spacing.md,
    paddingHorizontal: Spacing.xl,
  },
  stateHeading: {
    fontFamily: Typography.font.semiBold,
    fontSize: Typography.size.lg,
    color: Colors.textPrimary,
    textAlign: 'center',
  },
  stateBody: {
    fontFamily: Typography.font.regular,
    fontSize: Typography.size.base,
    color: Colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
  },
});
