import { Search, SlidersHorizontal, X } from 'lucide-react-native';
import React, { useCallback, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
  type ListRenderItemInfo,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { EventCard } from '../../components/fomo/event-card';
import { EventDetails } from '../../components/fomo/event-details';
import { ExploreFilterModal } from '../../components/fomo/explore-filter-modal';
import { ExploreSearchInput } from '../../components/fomo/explore-search-input';
import { FomoEmptyState, FomoErrorState, FomoLoadingState, FomoScreen } from '../../components/ui';
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
  type ExploreActiveFilters,
} from '../../utils/explore-filters';
import { usePerfScreenFocus } from '../../utils/performance-debug';
import { Colors, Spacing, Typography } from '../../theme';
import type { EventIntent } from '../../types/ui';

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
    loadMore,
    retry,
  } = useExploreSearch();

  // Location is only requested once the user opts in via the filter modal's
  // Near me toggle — `enabled` gates use-device-location's own permission
  // flow so opening Explore never eagerly prompts for location.
  const [locationRequested, setLocationRequested] = useState(false);
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
      <EventCard
        event={item}
        onPress={handleEventSelect}
        categoryLabel={backendCategoryLabel(item.rawCategory)}
      />
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

  return (
    <FomoScreen>
      <View style={[styles.header, { paddingTop: insets.top + Spacing.base }]}>
        <Text style={styles.title}>Explore</Text>
        <View style={styles.searchRow}>
          <View style={styles.searchInputWrap}>
            <ExploreSearchInput value={query} onChangeText={setQuery} onClear={() => setQuery('')} />
          </View>
          <Pressable
            onPress={() => setIsFilterModalOpen(true)}
            style={styles.filterBtn}
            accessibilityRole="button"
            accessibilityLabel="Filters"
          >
            <SlidersHorizontal size={18} color={Colors.textSecondary} strokeWidth={2} />
            {filterBadgeCount > 0 && (
              <View style={styles.filterBadge}>
                <Text style={styles.filterBadgeText}>{filterBadgeCount}</Text>
              </View>
            )}
          </Pressable>
        </View>

        {filtersActive && (
          <View style={styles.chipsRow}>
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
            <Pressable onPress={clearAll} hitSlop={6}>
              <Text style={styles.clearAll}>Clear all</Text>
            </Pressable>
          </View>
        )}
      </View>

      {status === 'idle' && (
        <FomoEmptyState
          icon={<Search size={40} color={Colors.textMuted} strokeWidth={1.5} />}
          message="Search for events or apply filters"
          sub="Type at least 2 characters, or tap the filter icon to browse by category, date, or location."
        />
      )}

      {status === 'too-short' && (
        <FomoEmptyState
          icon={<Search size={40} color={Colors.textMuted} strokeWidth={1.5} />}
          message="Keep typing"
          sub="Enter at least 2 characters to search."
        />
      )}

      {status === 'loading' && <FomoLoadingState />}

      {status === 'error' && (
        <FomoErrorState message={error ?? 'Could not load results'} onRetry={retry} />
      )}

      {status === 'empty' && (
        <FomoEmptyState
          icon={<Search size={40} color={Colors.textMuted} strokeWidth={1.5} />}
          message="No events match your search and filters"
          sub={isTextSearch ? `Nothing found for "${trimmedQuery}".` : 'Try different filters.'}
        />
      )}

      {status === 'results' && (
        <FlatList
          data={events}
          keyExtractor={keyExtractor}
          renderItem={renderItem}
          contentContainerStyle={[
            styles.listContent,
            { paddingBottom: insets.bottom + Spacing['2xl'] },
          ]}
          onEndReached={loadMore}
          onEndReachedThreshold={0.5}
          ListFooterComponent={listFooter}
          keyboardDismissMode="on-drag"
          keyboardShouldPersistTaps="handled"
        />
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

const styles = StyleSheet.create({
  header: {
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing.md,
    gap: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderSubtle,
  },
  title: {
    fontFamily: Typography.font.extraBold,
    fontSize: Typography.size['2xl'],
    color: Colors.textPrimary,
  },
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  searchInputWrap: {
    flex: 1,
  },
  filterBtn: {
    padding: Spacing.md,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.borderGlass,
    backgroundColor: Colors.surfaceGlass,
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
  chipsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
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
  clearAll: {
    fontFamily: Typography.font.semiBold,
    fontSize: Typography.size.sm,
    color: Colors.textSecondary,
    textDecorationLine: 'underline',
  },
  listContent: {
    alignItems: 'center',
    paddingTop: Spacing.base,
    gap: Spacing.md,
  },
  footer: {
    paddingVertical: Spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
