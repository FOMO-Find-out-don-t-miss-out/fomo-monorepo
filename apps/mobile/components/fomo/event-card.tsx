import { LinearGradient } from 'expo-linear-gradient';
import { Calendar, MapPin, Ticket } from 'lucide-react-native';
import React, { useRef } from 'react';
import {
  Animated,
  ImageBackground,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Colors, Gradients, Shadows } from '../../theme';
import {
  perfClaimImageSample,
  perfCountRender,
  perfLog,
  perfMark,
  perfSince,
} from '../../utils/performance-debug';

// ─── Types (canonical definitions live in types/ui) ──────────────────────────
import type { Event } from '../../types/ui';
export type { Event, EventCategory } from '../../types/ui';

interface EventCardProps {
  event: Event;
  isActive?: boolean;
  /**
   * Receives the event's id rather than being called with no args, so the
   * parent can pass one stable function (keyed off id lookup) to every card
   * instead of a fresh closure per card per render — required for
   * React.memo below to actually skip re-renders (FOMO-175).
   */
  onPress?: (id: string) => void;
  /**
   * Overrides the category badge TEXT only — the swatch colour still comes
   * from event.category (the existing 6-bucket UI taxonomy). Discover never
   * passes this and is unaffected. Explore (FOMO-172 Phase 4A) passes the
   * true backend EventCategory label here: apiEventToUiEvent's UI-bucket
   * mapping is lossy (e.g. backend "Tech"/"Food"/"Nightlife"/"Business"
   * collapse into the "Arts"/"Festival"/"Comedy"/"Theater" buckets), so a
   * user filtering by "Tech" would otherwise see a card badged "Arts" — a
   * real, visibly contradictory label this override corrects without
   * touching the shared UiEventCategory/Colors.category system.
   */
  categoryLabel?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────
//
// Two-layer architecture (required on Android):
//
//   Animated.View  ← owns dimensions (260×180), shadow/glow, scale transform
//     └── Pressable  ← owns touch, background colour, overflow:hidden, padding
//           └── content
//
// overflow:'hidden' clips elevation shadow on Android. Keeping shadow on the
// outer Animated.View (no overflow) and clipping on the inner Pressable gives
// correct behaviour on both platforms.
//
// Memoized (FOMO-175): with a stable `onPress` reference and a stable `event`
// object identity from the parent's data layer, this bails out of re-render
// for cards unaffected by a Discover state change (search text, pending
// intent, locate-me timer, etc.).

function EventCardBase({
  event,
  isActive = false,
  onPress,
  categoryLabel,
}: EventCardProps) {
  perfCountRender('EventCard', 25);

  const scale = useRef(new Animated.Value(1)).current;
  const catColors = Colors.category[event.category];

  // Image-load timing for a small capped sample of cards (see performance-debug).
  const imageSampleRef = useRef<number | null | undefined>(undefined);
  if (imageSampleRef.current === undefined) {
    imageSampleRef.current = event.imageUri ? perfClaimImageSample() : null;
  }
  const imageMarkRef = useRef(0);

  function pressIn() {
    Animated.spring(scale, {
      toValue: 0.97,
      speed: 50,
      bounciness: 4,
      useNativeDriver: true,
    }).start();
  }

  function pressOut() {
    Animated.spring(scale, {
      toValue: 1,
      speed: 50,
      bounciness: 4,
      useNativeDriver: true,
    }).start();
  }

  return (
    // Outer: scale + glow — NO overflow:hidden (would clip shadow on Android)
    <Animated.View
      style={[
        styles.shadow,
        isActive && Shadows.cardActive,
        { transform: [{ scale }] },
      ]}
    >
      {/* Inner: background, border, clipping, padding, content */}
      <Pressable
        onPress={() => onPress?.(event.id)}
        onPressIn={pressIn}
        onPressOut={pressOut}
        style={[styles.card, isActive && styles.cardBorderActive]}
      >
        {/* Cover image */}
        {event.imageUri ? (
          <ImageBackground
            source={{ uri: event.imageUri }}
            style={StyleSheet.absoluteFill}
            imageStyle={styles.coverImageStyle}
            {...(imageSampleRef.current != null
              ? {
                  onLoadStart: () => {
                    imageMarkRef.current = perfMark();
                  },
                  onLoadEnd: () => {
                    perfLog('image', {
                      sample: imageSampleRef.current,
                      duration_ms: perfSince(imageMarkRef.current),
                    });
                  },
                }
              : {})}
          />
        ) : null}

        {/* ── Header: category badge + price ── */}
        <View style={styles.headerRow}>
          <View style={[styles.categoryBadge, { borderColor: catColors.border }]}>
            <Text style={[styles.categoryText, { color: catColors.text }]}>
              {categoryLabel ?? event.category}
            </Text>
          </View>
          {event.price != null && (
            <Text style={styles.price}>From {event.price}</Text>
          )}
        </View>

        {/* ── Title ── */}
        <Text style={styles.title} numberOfLines={1}>
          {event.title}
        </Text>

        {/* ── Venue + distance ── */}
        <View style={styles.venueRow}>
          <MapPin size={14} color={Colors.textMuted} strokeWidth={1.5} />
          <Text style={styles.venueText} numberOfLines={1}>{event.venue}</Text>
          {event.distance != null && (
            <Text style={styles.distanceText}>{event.distance}</Text>
          )}
        </View>

        {/* ── Date + time ── */}
        <View style={styles.dateRow}>
          <Calendar size={14} color={Colors.textSecondary} strokeWidth={1.5} />
          <Text style={styles.dateText}>{event.date}</Text>
          <Text style={styles.atText}>at</Text>
          <Text style={styles.dateText}>{event.time}</Text>
        </View>

        {/* ── CTA — LinearGradient from #BC13FE → #9333EA (purple-600) ── */}
        <LinearGradient
          colors={Gradients.primaryCta}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={styles.ctaBtn}
        >
          <Ticket size={12} color={Colors.textPrimary} strokeWidth={1.5} />
          <Text style={styles.ctaText}>View Details</Text>
        </LinearGradient>

      </Pressable>
    </Animated.View>
  );
}

export const EventCard = React.memo(EventCardBase);

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  // Outer wrapper — exact dimensions, owns shadow + transform
  shadow: {
    width: 260,
    height: 180,
    borderRadius: 16,
  },

  // Inner Pressable — fills outer, owns bg + clipping
  card: {
    flex: 1,
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: Colors.borderFocus,
    backgroundColor: Colors.surfaceCard,
    padding: 14,
  },
  cardBorderActive: {
    borderColor: Colors.eventSelected,
  },
  coverImageStyle: {
    borderRadius: 16,
  },

  // ── Header row ────────────────────────────────────────────────────────────
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  categoryBadge: {
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  categoryText: {
    fontFamily: 'Inter_600SemiBold',
    fontSize: 10,
  },
  price: {
    fontFamily: 'Inter_700Bold',
    fontSize: 11,
    color: Colors.textPrimary,
  },

  // ── Title ─────────────────────────────────────────────────────────────────
  title: {
    fontFamily: 'Inter_700Bold',
    fontSize: 14,
    color: Colors.textPrimary,
    lineHeight: 18,
    marginBottom: 5,
  },

  // ── Venue row ─────────────────────────────────────────────────────────────
  venueRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 5,
  },
  venueText: {
    flex: 1,
    fontFamily: 'Inter_400Regular',
    fontSize: 11,
    color: Colors.textSecondary,
  },
  distanceText: {
    fontFamily: 'Inter_400Regular',
    fontSize: 10,
    color: Colors.textMuted,
    flexShrink: 0,
  },

  // ── Date row ──────────────────────────────────────────────────────────────
  dateRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 9,
  },
  dateText: {
    fontFamily: 'Inter_600SemiBold',
    fontSize: 11,
    color: Colors.textSecondary,
  },
  atText: {
    fontFamily: 'Inter_400Regular',
    fontSize: 11,
    color: Colors.textMuted,
  },

  // ── CTA — LinearGradient fills this style ────────────────────────────────
  ctaBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 7,
    borderRadius: 9,
  },
  ctaText: {
    fontFamily: 'Inter_600SemiBold',
    fontSize: 11,
    color: Colors.textPrimary,
  },
});
