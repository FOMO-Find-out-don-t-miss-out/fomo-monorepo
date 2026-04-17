import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
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
import type { Event, EventCategory } from '../../types/ui';

// ─── Constants ────────────────────────────────────────────────────────────────

const { height: SCREEN_H } = Dimensions.get('window');

// v0 default sheet height: 40vh → we use 42% to include safe area buffer
const SHEET_HEIGHT = SCREEN_H * 0.42;

// ─── Design tokens ────────────────────────────────────────────────────────────

const CTA_GRADIENT: [string, string] = ['#BC13FE', '#9333EA'];

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
// Matches v0 event-bottom-sheet.tsx with Premium Glassmorphism:
//   • BlurView background (intensity: 20, tint: 'dark')
//   • LinearGradient CTA button (#BC13FE → #9333EA)
//   • Inter font family integration

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
        {/* Outer container handles rounded corners and clipping for BlurView */}
        <View style={styles.sheet}>
          <BlurView intensity={20} tint="dark" style={StyleSheet.absoluteFill} />

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
              <View style={styles.ctaWrapper}>
                <LinearGradient
                  colors={CTA_GRADIENT}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={styles.ctaBtn}
                >
                  <Pressable 
                    style={styles.ctaPressable}
                    onPress={onClose}
                  >
                    <Ticket size={16} color="#fff" strokeWidth={1.5} />
                    <Text style={styles.ctaText}>Get Tickets</Text>
                    {event.price != null && (
                      <View style={styles.pricePill}>
                        <Text style={styles.priceText}>{event.price}</Text>
                      </View>
                    )}
                  </Pressable>
                </LinearGradient>
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

  // ── Sheet — BlurView inside View with borderRadius + overflow:hidden
  sheet: {
    height: SHEET_HEIGHT,
    backgroundColor: 'rgba(12, 12, 18, 0.88)', // Fallback
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    borderTopWidth: 1,
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
    paddingTop: 12,
    overflow: 'hidden',
  },
  handleBar: {
    alignSelf: 'center',
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.20)',
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
    paddingHorizontal: 20,
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
    fontFamily: 'Inter_600SemiBold',
    fontSize: 10,
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
    fontFamily: 'Inter_600SemiBold',
    fontSize: 10,
    color: '#A855F7',
  },

  // ── Title ─────────────────────────────────────────────────────────────────
  title: {
    fontFamily: 'Inter_800ExtraBold',
    fontSize: 20,
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
    fontFamily: 'Inter_400Regular',
    fontSize: 13,
    color: 'rgba(255,255,255,0.6)',
  },
  distanceText: {
    fontFamily: 'Inter_400Regular',
    fontSize: 12,
    color: 'rgba(255,255,255,0.4)',
  },
  directionsChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 8,
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
  },
  directionsText: {
    fontFamily: 'Inter_600SemiBold',
    fontSize: 11,
    color: '#3B82F6',
  },

  // ── Info pills ────────────────────────────────────────────────────────────
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
    fontFamily: 'Inter_600SemiBold',
    fontSize: 11,
    color: '#22D3EE',
  },
  pillPurple: {
    fontFamily: 'Inter_600SemiBold',
    fontSize: 11,
    color: '#A855F7',
  },

  // ── Action row ────────────────────────────────────────────────────────────
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
    fontFamily: 'Inter_400Regular',
    fontSize: 11,
    color: 'rgba(255,255,255,0.4)',
  },

  // ── CTA ───────────────────────────────────────────────────────────────────
  ctaWrapper: {
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.06)',
  },
  ctaBtn: {
    borderRadius: 12,
    overflow: 'hidden',
    shadowColor: '#BC13FE',
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 15,
    shadowOpacity: 0.5,
    elevation: 8,
  },
  ctaPressable: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 13,
  },
  ctaText: {
    fontFamily: 'Inter_700Bold',
    fontSize: 15,
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
    fontFamily: 'Inter_700Bold',
    fontSize: 11,
    color: '#fff',
  },

});
