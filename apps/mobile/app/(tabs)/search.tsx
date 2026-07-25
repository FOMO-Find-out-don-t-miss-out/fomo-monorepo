import { Search } from 'lucide-react-native';
import React, { useCallback, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  View,
  type ListRenderItemInfo,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { EventCard } from '../../components/fomo/event-card';
import { EventDetails } from '../../components/fomo/event-details';
import { ExploreSearchInput } from '../../components/fomo/explore-search-input';
import { FomoEmptyState, FomoErrorState, FomoLoadingState, FomoScreen } from '../../components/ui';
import { useAuth } from '../../hooks/use-auth';
import { useEventRelationships } from '../../hooks/use-event-relationships';
import { useExploreSearch } from '../../hooks/use-explore-search';
import { setEventIntent } from '../../utils/event-relationships-api';
import { usePerfScreenFocus } from '../../utils/performance-debug';
import { Colors, Spacing, Typography } from '../../theme';
import type { EventIntent, UiEvent } from '../../types/ui';

export default function ExploreScreen() {
  usePerfScreenFocus('search');
  const insets = useSafeAreaInsets();
  const { accessToken } = useAuth();

  const { query, setQuery, status, events, error, loadingMore, loadMore, retry } =
    useExploreSearch();

  const [selectedEvent, setSelectedEvent] = useState<UiEvent | null>(null);
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

  const keyExtractor = useCallback((event: UiEvent) => event.id, []);

  const renderItem = useCallback(
    ({ item }: ListRenderItemInfo<UiEvent>) => (
      <EventCard event={item} onPress={handleEventSelect} />
    ),
    [handleEventSelect],
  );

  const listFooter = loadingMore ? (
    <View style={styles.footer}>
      <ActivityIndicator color={Colors.brandPrimary} />
    </View>
  ) : null;

  const trimmedQuery = query.trim();

  return (
    <FomoScreen>
      <View style={[styles.header, { paddingTop: insets.top + Spacing.base }]}>
        <Text style={styles.title}>Explore</Text>
        <ExploreSearchInput value={query} onChangeText={setQuery} onClear={() => setQuery('')} />
      </View>

      {status === 'idle' && (
        <FomoEmptyState
          icon={<Search size={40} color={Colors.textMuted} strokeWidth={1.5} />}
          message="Search for events"
          sub="Find events by title, venue, or organizer."
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
          message="No events match your search"
          sub={`Nothing found for "${trimmedQuery}".`}
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
