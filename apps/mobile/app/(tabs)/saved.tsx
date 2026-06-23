import { Bookmark, Heart } from 'lucide-react-native';
import React, { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { FomoEmptyState, FomoErrorState, FomoLoadingState, FomoScreen } from '../../components/ui';
import { useAuth } from '../../hooks/use-auth';
import { useSavedEvents } from '../../hooks/use-saved-events';
import { Colors, Spacing, Typography } from '../../theme';
import { EventCard } from '../../components/fomo/event-card';
import { EventDetails } from '../../components/fomo/event-details';
import type { UiEvent } from '../../types/ui';

export default function SavedScreen() {
  const insets = useSafeAreaInsets();
  const { accessToken, isLoading: authLoading } = useAuth();
  const { events, isLoading, error, refetch, unsave } = useSavedEvents(accessToken);
  const [selectedEvent, setSelectedEvent] = useState<UiEvent | null>(null);

  // While auth is still restoring from SecureStore, show loading.
  if (authLoading) {
    return (
      <FomoScreen>
        <FomoLoadingState />
      </FomoScreen>
    );
  }

  // App has registered-only gate — unauthenticated state is transitional only.
  if (!accessToken) {
    return (
      <FomoScreen>
        <FomoEmptyState
          icon={<Heart size={48} color={Colors.textMuted} strokeWidth={1.2} />}
          message="Log in to see saved events"
        />
      </FomoScreen>
    );
  }

  return (
    <FomoScreen>
      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + Spacing.md }]}>
        <Bookmark size={18} color={Colors.purple} strokeWidth={1.5} />
        <Text style={styles.headerTitle}>Saved</Text>
      </View>

      {/* Body */}
      {isLoading ? (
        <FomoLoadingState />
      ) : error ? (
        <FomoErrorState message={error} onRetry={refetch} />
      ) : events.length === 0 ? (
        <FomoEmptyState
          icon={<Heart size={48} color={Colors.purple} strokeWidth={1.2} />}
          message="No saved events yet"
          sub="Tap the bookmark on any event to save it here."
        />
      ) : (
        <ScrollView
          contentContainerStyle={[styles.list, { paddingBottom: insets.bottom + Spacing.xl }]}
          showsVerticalScrollIndicator={false}
        >
          {events.map((event) => (
            <View key={event.id} style={styles.cardRow}>
              <EventCard
                event={event}
                isSaved
                isSaveLoading={false}
                onToggleSave={() => unsave(event.id)}
                onPress={() => setSelectedEvent(event)}
              />
            </View>
          ))}
        </ScrollView>
      )}

      {/* Detail sheet */}
      <EventDetails
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
        relationships={selectedEvent ? ['saved'] : []}
        onToggleRelationship={selectedEvent
          ? (type) => {
              if (type === 'saved') {
                unsave(selectedEvent.id);
                setSelectedEvent(null);
              }
            }
          : undefined}
      />
    </FomoScreen>
  );
}

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
