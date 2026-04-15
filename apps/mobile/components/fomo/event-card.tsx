import { Bookmark, Calendar, MapPin, Ticket } from 'lucide-react-native';
import React, { useRef } from 'react';
import {
  Animated,
  ImageBackground,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';


// ─── Types ────────────────────────────────────────────────────────────────────

export type EventCategory =
  | 'Music'
  | 'Arts'
  | 'Theater'
  | 'Sports'
  | 'Comedy'
  | 'Festival';

export interface Event {
  id: string;
  title: string;
  venue: string;
  date: string;
  time: string;
  category: EventCategory;
  hypeLevel: 'high' | 'medium' | 'low';
  price?: string;
  distance?: string;
  imageUri?: string;
  attendeesCount?: string;
  hypeScore?: number;
}

interface EventCardProps {
  event: Event;
  isActive?: boolean;
  onPress?: () => void;
}

// ─── Category colour map ──────────────────────────────────────────────────────

const CATEGORY_COLORS: Record<EventCategory, { border: string; text: string }> = {
  Music:    { border: 'rgba(168, 85,  247, 0.5)', text: '#A855F7' },
  Arts:     { border: 'rgba(236, 72,  153, 0.5)', text: '#EC4899' },
  Theater:  { border: 'rgba(245, 158, 11,  0.5)', text: '#F59E0B' },
  Sports:   { border: 'rgba(34,  197, 94,  0.5)', text: '#22C55E' },
  Comedy:   { border: 'rgba(249, 115, 22,  0.5)', text: '#F97316' },
  Festival: { border: 'rgba(34,  211, 238, 0.5)', text: '#22D3EE' },
};

// ─── Component ────────────────────────────────────────────────────────────────
//
// Two-layer architecture (required on Android):
//
//   Animated.View  ← owns dimensions (260×180), shadow/glow, scale transform
//     └── Pressable  ← owns touch, background colour, overflow:hidden, padding
//           └── content (bookmark, header, title, venue, date, cta)
//
// Reason: overflow:'hidden' clips elevation shadow on Android. Putting shadow
// on the outer Animated.View (which has NO overflow:hidden) and clipping on
// the inner Pressable gives correct behaviour on both platforms.

export function EventCard({ event, isActive = false, onPress }: EventCardProps) {
  const scale = useRef(new Animated.Value(1)).current;
  const catColors = CATEGORY_COLORS[event.category];

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
    // Outer: scale transform + glow shadow — NO overflow:hidden here
    <Animated.View
      style={[
        styles.shadow,
        isActive && styles.shadowActive,
        { transform: [{ scale }] },
      ]}
    >
      {/* Inner: background, border, clipping, padding, all content */}
      <Pressable
        onPress={onPress}
        onPressIn={pressIn}
        onPressOut={pressOut}
        style={[styles.card, isActive && styles.cardBorderActive]}
      >
        {/* Cover image — rendered behind content when provided */}
        {event.imageUri ? (
          <ImageBackground
            source={{ uri: event.imageUri }}
            style={StyleSheet.absoluteFill}
            imageStyle={styles.coverImageStyle}
          />
        ) : null}

        {/* Bookmark — absolute top-right (View, not Pressable, so it never
            intercepts touches meant for the card's main Pressable) */}
        <View style={styles.bookmark}>
          <Bookmark size={13} color="rgba(255,255,255,0.45)" strokeWidth={1.5} />
        </View>

        {/* ── Header: category badge (left) + price (right) ── */}
        <View style={styles.headerRow}>
          <View style={[styles.categoryBadge, { borderColor: catColors.border }]}>
            <Text style={[styles.categoryText, { color: catColors.text }]}>
              {event.category}
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
          <MapPin size={14} color="rgba(255,255,255,0.45)" strokeWidth={1.5} />
          <Text style={styles.venueText} numberOfLines={1}>{event.venue}</Text>
          {event.distance != null && (
            <Text style={styles.distanceText}>{event.distance}</Text>
          )}
        </View>

        {/* ── Date + time ── */}
        <View style={styles.dateRow}>
          <Calendar size={14} color="#22D3EE" strokeWidth={1.5} />
          <Text style={styles.dateText}>{event.date}</Text>
          <Text style={styles.atText}>at</Text>
          <Text style={styles.dateText}>{event.time}</Text>
        </View>

        {/* ── CTA button ── */}
        <View style={styles.ctaBtn}>
          <Ticket size={12} color="#BC13FE" strokeWidth={1.5} />
          <Text style={styles.ctaText}>View Tickets</Text>
        </View>

      </Pressable>
    </Animated.View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  // Outer wrapper — exact card dimensions, owns the shadow + transform.
  // Must NOT have overflow:'hidden' so the shadow/elevation aren't clipped.
  shadow: {
    width: 260,
    height: 180,
    borderRadius: 16,
  },
  shadowActive: {
    shadowColor: '#A855F7',
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 16,
    shadowOpacity: 0.45,
    elevation: 12,
  },

  // Inner Pressable — fills the shadow wrapper, owns background + clipping
  card: {
    flex: 1,
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(188, 19, 254, 0.3)',
    // Glass dark background (v0: glassmorphism ≈ dark semi-transparent)
    backgroundColor: 'rgba(18, 18, 24, 0.85)',
    padding: 14,
  },
  cardBorderActive: {
    borderColor: 'rgba(168, 85, 247, 0.6)',
  },
  coverImageStyle: {
    borderRadius: 16,
  },

  // ── Bookmark ────────────────────────────────────────────────────────────
  bookmark: {
    position: 'absolute',
    top: 10,
    right: 10,
    padding: 6,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.05)',
    zIndex: 2,
  },

  // ── Header row ──────────────────────────────────────────────────────────
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
    paddingRight: 28,   // clears bookmark button
  },
  categoryBadge: {
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  categoryText: {
    fontSize: 10,
    fontWeight: '600',
  },
  price: {
    fontSize: 11,
    fontWeight: '700',
    color: '#22D3EE',
  },

  // ── Title ────────────────────────────────────────────────────────────────
  title: {
    fontSize: 14,
    fontWeight: '700',
    color: '#fff',
    lineHeight: 18,
    marginBottom: 5,
  },

  // ── Venue row ────────────────────────────────────────────────────────────
  venueRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 5,
  },
  venueText: {
    flex: 1,
    fontSize: 11,
    color: 'rgba(255,255,255,0.5)',
  },
  distanceText: {
    fontSize: 10,
    color: 'rgba(255,255,255,0.35)',
    flexShrink: 0,
  },

  // ── Date row ─────────────────────────────────────────────────────────────
  dateRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 9,
  },
  dateText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#22D3EE',
  },
  atText: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.3)',
  },

  // ── CTA button ────────────────────────────────────────────────────────────
  ctaBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 7,
    borderRadius: 9,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderWidth: 1,
    borderColor: 'rgba(188, 19, 254, 0.30)',
  },
  ctaText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#BC13FE',
  },
});
