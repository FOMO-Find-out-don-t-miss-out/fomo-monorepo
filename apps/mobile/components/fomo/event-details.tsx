import {
  Calendar,
  Clock,
  Heart,
  MapPin,
  Navigation,
  Share2,
  Star,
  Ticket,
  Users,
  X,
} from 'lucide-react-native';
import React, { useEffect, useRef } from 'react';
import {
  Animated,
  Dimensions,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import type { Event, EventCategory } from './event-card';

// ─── Constants ────────────────────────────────────────────────────────────────

const { height: SCREEN_H } = Dimensions.get('window');

// v0 default sheet height: 40vh → we use 42% to include safe area buffer
const SHEET_HEIGHT = SCREEN_H * 0.42;

// ─── Category colour map ──────────────────────────────────────────────────────

const CATEGORY_COLORS: Record<EventCategory, { border: string; text: string }> = {
  Music:    { border: 'rgba(168, 85,  247, 0.5)', text: '#A855F7' },
  Arts:     { border: 'rgba(236, 72,  153, 0.5)', text: '#EC4899' },
  Theater:  { border: 'rgba(245, 158, 11,  0.5)', text: '#F59E0B' },
  Sports:   { border: 'rgba(34,  197, 94,  0.5)', text: '#22C55E' },
  Comedy:   { border: 'rgba(249, 115, 22,  0.5)', text: '#F97316' },
  Festival: { border: 'rgba(34,  211, 238, 0.5)', text: '#22D3EE' },
};

// ─── Props ────────────────────────────────────────────────────────────────────

interface EventDetailsProps {
  event: Event | null;
  onClose: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────
//
// Matches v0 event-bottom-sheet.tsx:
//   • Backdrop fades in, sheet slides up from bottom
//   • Fixed 40vh height (42% in RN to account for safe area)
//   • Header: category badge + High Hype badge
//   • Venue row with Directions chip
//   • 3-column pill row: date / time / attendees
//   • Action row: heart + share + "Swipe up" label
//   • CTA: solid purple button with gradient approximation

export function EventDetails({ event, onClose }: EventDetailsProps) {
  const backdropOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (event) {
      Animated.timing(backdropOpacity, {
        toValue: 1,
        duration: 220,
        useNativeDriver: true,
      }).start();
    } else {
      backdropOpacity.setValue(0);
    }
  }, [event, backdropOpacity]);

  const catColors = event
    ? CATEGORY_COLORS[event.category]
    : CATEGORY_COLORS.Music;

  return (
    <Modal
      visible={event !== null}
      transparent
      animationType="slide"
      statusBarTranslucent
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>

        {/* ── Backdrop ───────────────────────────────────────────────── */}
        <Animated.View style={[styles.backdrop, { opacity: backdropOpacity }]}>
          <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        </Animated.View>

        {/* ── Bottom sheet ───────────────────────────────────────────── */}
        <View style={styles.sheet}>
          {event && (
            <>
              {/* Handle bar */}
              <View style={styles.handleBar} />

              {/* Close button */}
              <Pressable style={styles.closeBtn} onPress={onClose} hitSlop={8}>
                <X size={16} color="rgba(255,255,255,0.7)" strokeWidth={1.5} />
              </Pressable>

              {/* ── Scrollable body ─────────────────────────────────── */}
              <ScrollView
                style={styles.scroll}
                contentContainerStyle={styles.scrollContent}
                showsVerticalScrollIndicator={false}
                bounces={false}
              >

                {/* Header row — category badge + High Hype */}
                <View style={styles.badgeRow}>
                  <View style={[styles.categoryBadge, { borderColor: catColors.border }]}>
                    <Text style={[styles.categoryText, { color: catColors.text }]}>
                      {event.category}
                    </Text>
                  </View>
                  {event.hypeLevel === 'high' && (
                    <View style={styles.hypeBadge}>
                      <Star size={10} color="#A855F7" fill="#A855F7" strokeWidth={1.5} />
                      <Text style={styles.hypeText}>High Hype</Text>
                    </View>
                  )}
                </View>

                {/* Title */}
                <Text style={styles.title}>{event.title}</Text>

                {/* Venue + Directions */}
                <View style={styles.venueRow}>
                  <View style={styles.venueLeft}>
                    <MapPin size={14} color="rgba(255,255,255,0.6)" strokeWidth={1.5} />
                    <Text style={styles.venueText} numberOfLines={1}>{event.venue}</Text>
                    {event.distance != null && (
                      <Text style={styles.distanceText}>({event.distance})</Text>
                    )}
                  </View>
                  <View style={styles.directionsChip}>
                    <Navigation size={12} color="#3B82F6" strokeWidth={1.5} />
                    <Text style={styles.directionsText}>Directions</Text>
                  </View>
                </View>

                {/* Date / Time / Attendees pills */}
                <View style={styles.pillRow}>
                  <View style={styles.pill}>
                    <Calendar size={14} color="#22D3EE" strokeWidth={1.5} />
                    <Text style={styles.pillCyan}>{event.date}</Text>
                  </View>
                  <View style={styles.pill}>
                    <Clock size={14} color="#22D3EE" strokeWidth={1.5} />
                    <Text style={styles.pillCyan}>{event.time}</Text>
                  </View>
                  <View style={styles.pill}>
                    <Users size={14} color="#A855F7" strokeWidth={1.5} />
                    <Text style={styles.pillPurple}>
                      {event.attendeesCount ? `${event.attendeesCount} going` : '2.4K going'}
                    </Text>
                  </View>
                </View>

                {/* Action row */}
                <View style={styles.actionRow}>
                  <Pressable style={styles.actionBtn}>
                    <Heart size={16} color="#EC4899" strokeWidth={1.5} />
                  </Pressable>
                  <Pressable style={styles.actionBtn}>
                    <Share2 size={16} color="rgba(255,255,255,0.6)" strokeWidth={1.5} />
                  </Pressable>
                  <Text style={styles.swipeHint}>Swipe up for details</Text>
                </View>

              </ScrollView>

              {/* ── Get Tickets CTA ─────────────────────────────────── */}
              {/* v0: bg-gradient-to-r from-purple-600 to-purple-500   */}
              <View style={styles.ctaWrapper}>
                <Pressable style={styles.ctaBtn} onPress={onClose}>
                  <Ticket size={16} color="#fff" strokeWidth={1.5} />
                  <Text style={styles.ctaText}>Get Tickets</Text>
                  {event.price != null && (
                    <View style={styles.pricePill}>
                      <Text style={styles.priceText}>{event.price}</Text>
                    </View>
                  )}
                </Pressable>
              </View>
            </>
          )}
        </View>

      </View>
    </Modal>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({

  // ── Modal overlay ─────────────────────────────────────────────────────────
  overlay: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
  },

  // ── Sheet — matches v0 "glassmorphism rounded-t-3xl h-full flex flex-col"
  // Fixed height = 40vh (v0 default non-expanded state)
  sheet: {
    height: SHEET_HEIGHT,
    backgroundColor: 'rgba(18, 18, 24, 0.98)',
    borderTopLeftRadius: 24,     // rounded-t-3xl
    borderTopRightRadius: 24,
    borderTopWidth: 1,
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    paddingTop: 12,
    overflow: 'hidden',
  },
  handleBar: {
    alignSelf: 'center',
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.20)',  // v0: bg-white/20
    marginBottom: 12,
  },
  closeBtn: {
    position: 'absolute',
    top: 10,
    right: 14,
    padding: 6,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.10)',
    zIndex: 1,
  },

  // ── Scrollable body ───────────────────────────────────────────────────────
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 20,   // px-5
    paddingBottom: 12,
  },

  // ── Badges ────────────────────────────────────────────────────────────────
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
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
  hypeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 20,
    backgroundColor: 'rgba(168, 85, 247, 0.15)',
  },
  hypeText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#A855F7',
  },

  // ── Title ─────────────────────────────────────────────────────────────────
  // v0: text-xl font-bold (20px, 800)
  title: {
    fontSize: 20,
    fontWeight: '800',
    color: '#fff',
    lineHeight: 26,
    marginBottom: 10,
  },

  // ── Venue ─────────────────────────────────────────────────────────────────
  venueRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
    gap: 8,
  },
  venueLeft: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  venueText: {
    flex: 1,
    fontSize: 13,
    color: 'rgba(255,255,255,0.6)',   // v0: text-white/60
  },
  distanceText: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.4)',   // v0: text-white/40
  },
  directionsChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 8,
    backgroundColor: 'rgba(59, 130, 246, 0.15)',   // v0: bg-blue-500/15
  },
  directionsText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#3B82F6',
  },

  // ── Info pills ────────────────────────────────────────────────────────────
  // v0: flex items-center gap-3 mb-4, each pill: px-2.5 py-1.5 rounded-lg bg-white/5
  pillRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 14,
  },
  pill: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
    paddingHorizontal: 8,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
  },
  pillCyan: {
    fontSize: 11,
    fontWeight: '600',
    color: '#22D3EE',
  },
  pillPurple: {
    fontSize: 11,
    fontWeight: '600',
    color: '#A855F7',
  },

  // ── Action row ────────────────────────────────────────────────────────────
  // v0: flex items-center gap-2 mb-4
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  actionBtn: {
    padding: 10,
    borderRadius: 12,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
  },
  swipeHint: {
    marginLeft: 'auto',
    fontSize: 11,
    color: 'rgba(255,255,255,0.4)',
  },

  // ── CTA ───────────────────────────────────────────────────────────────────
  // v0: bg-gradient-to-r from-purple-600 to-purple-500
  //     shadow-[0_0_25px_rgba(168,85,247,0.4)]
  ctaWrapper: {
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.06)',
  },
  ctaBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 13,
    borderRadius: 12,
    // Approximate gradient from-purple-600 to-purple-500 with a single solid color
    backgroundColor: '#9333EA',   // purple-600
    shadowColor: '#A855F7',
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 20,
    shadowOpacity: 0.5,
    elevation: 12,
  },
  ctaText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#fff',
    letterSpacing: 0.2,
  },
  pricePill: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.18)',
  },
  priceText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#fff',
  },

});
