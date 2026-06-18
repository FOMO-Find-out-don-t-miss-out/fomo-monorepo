import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import {
  Calendar,
  Clock,
  MapPin,
  Navigation,
  Share2,
  Star,
  Ticket,
  X,
} from 'lucide-react-native';
import React, { useEffect, useRef, useState } from 'react';
import {
  Animated,
  Dimensions,
  Easing,
  Linking,
  Modal,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { hasValidCoords } from '../../utils/geo';
import type { Event, EventCategory } from '../../types/ui';

// ─── Constants ────────────────────────────────────────────────────────────────

const { height: SCREEN_H } = Dimensions.get('window');
const SHEET_HEIGHT = SCREEN_H * 0.42;
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

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function openDirections(event: Event): Promise<void> {
  if (!hasValidCoords(event.lat, event.lng)) return;
  const url = `https://www.google.com/maps/dir/?api=1&destination=${event.lat},${event.lng}`;
  try { await Linking.openURL(url); } catch {}
}

async function openUrl(url: string): Promise<void> {
  try {
    const supported = await Linking.canOpenURL(url);
    if (supported) await Linking.openURL(url);
  } catch {}
}

async function shareEvent(event: Event): Promise<void> {
  const url = event.ticketUrl ?? event.sourceUrl ?? null;
  try {
    await Share.share({
      title: event.title,
      message: url ? `${event.title} — ${url}` : event.title,
      url: url ?? undefined,
    });
  } catch {}
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface EventDetailsProps {
  event: Event | null;
  onClose: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function EventDetails({ event, onClose }: EventDetailsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const isClosingRef = useRef(false);

  const backdropOpacity = useRef(new Animated.Value(0)).current;
  const sheetTranslateY = useRef(new Animated.Value(SHEET_HEIGHT)).current;

  // Keep content visible during the exit animation even when event becomes null.
  const prevEventRef = useRef<Event | null>(null);
  if (event) prevEventRef.current = event;
  const displayEvent = event ?? prevEventRef.current;

  function animateOut(callback?: () => void) {
    if (isClosingRef.current) return;
    isClosingRef.current = true;
    Animated.parallel([
      Animated.timing(backdropOpacity, { toValue: 0, duration: 180, useNativeDriver: true }),
      Animated.timing(sheetTranslateY, {
        toValue: SHEET_HEIGHT,
        duration: 220,
        easing: Easing.in(Easing.poly(3)),
        useNativeDriver: true,
      }),
    ]).start(() => {
      isClosingRef.current = false;
      setIsOpen(false);
      callback?.();
    });
  }

  function handleClose() {
    animateOut(onClose);
  }

  useEffect(() => {
    if (event && !isOpen && !isClosingRef.current) {
      setIsOpen(true);
      sheetTranslateY.setValue(SHEET_HEIGHT);
      backdropOpacity.setValue(0);
      Animated.parallel([
        Animated.timing(backdropOpacity, { toValue: 1, duration: 200, useNativeDriver: true }),
        Animated.timing(sheetTranslateY, {
          toValue: 0,
          duration: 300,
          easing: Easing.out(Easing.poly(4)),
          useNativeDriver: true,
        }),
      ]).start();
    } else if (!event && isOpen && !isClosingRef.current) {
      animateOut();
    }
  }, [event, isOpen]);

  const catColors = displayEvent
    ? CATEGORY_COLORS[displayEvent.category]
    : CATEGORY_COLORS.Music;

  const canOpenDirections = displayEvent ? hasValidCoords(displayEvent.lat, displayEvent.lng) : false;

  return (
    <Modal
      visible={isOpen}
      transparent
      animationType="none"
      statusBarTranslucent
      onRequestClose={handleClose}
    >
      <View style={styles.overlay}>

        {/* Backdrop — covers entire screen, fades in/out independently of sheet */}
        <Animated.View style={[styles.backdrop, { opacity: backdropOpacity }]}>
          <Pressable style={StyleSheet.absoluteFill} onPress={handleClose} />
        </Animated.View>

        {/* Bottom sheet — slides up from below the visible area */}
        <Animated.View style={[styles.sheet, { transform: [{ translateY: sheetTranslateY }] }]}>
          <BlurView intensity={20} tint="dark" style={StyleSheet.absoluteFill} />

          {displayEvent && (
            <>
              <View style={styles.handleBar} />

              <Pressable style={styles.closeBtn} onPress={handleClose} hitSlop={8}>
                <X size={16} color="rgba(255,255,255,0.7)" strokeWidth={1.5} />
              </Pressable>

              <ScrollView
                style={styles.scroll}
                contentContainerStyle={styles.scrollContent}
                showsVerticalScrollIndicator={false}
                bounces={false}
              >
                {/* Header: category badge + hype badge */}
                <View style={styles.badgeRow}>
                  <View style={[styles.categoryBadge, { borderColor: catColors.border }]}>
                    <Text style={[styles.categoryText, { color: catColors.text }]}>
                      {displayEvent.category}
                    </Text>
                  </View>
                  {displayEvent.hypeLevel === 'high' && (
                    <View style={styles.hypeBadge}>
                      <Star size={10} color="#A855F7" fill="#A855F7" strokeWidth={1.5} />
                      <Text style={styles.hypeText}>High Hype</Text>
                    </View>
                  )}
                </View>

                {/* Title */}
                <Text style={styles.title}>{displayEvent.title}</Text>

                {/* Venue + distance */}
                <View style={styles.venueRow}>
                  <MapPin size={14} color="rgba(255,255,255,0.6)" strokeWidth={1.5} />
                  <Text style={styles.venueText} numberOfLines={1}>{displayEvent.venue}</Text>
                  {displayEvent.distance != null && (
                    <Text style={styles.distanceText}>({displayEvent.distance})</Text>
                  )}
                </View>

                {/* Date / Time pills */}
                <View style={styles.pillRow}>
                  <View style={styles.pill}>
                    <Calendar size={14} color="#22D3EE" strokeWidth={1.5} />
                    <Text style={styles.pillCyan}>{displayEvent.date}</Text>
                  </View>
                  <View style={styles.pill}>
                    <Clock size={14} color="#22D3EE" strokeWidth={1.5} />
                    <Text style={styles.pillCyan}>{displayEvent.time}</Text>
                  </View>
                </View>

                {/* Action row — Directions (when valid coords) + Share */}
                <View style={styles.actionRow}>
                  {canOpenDirections && (
                    <Pressable style={styles.actionBtn} onPress={() => openDirections(displayEvent)}>
                      <Navigation size={16} color="rgba(255,255,255,0.6)" strokeWidth={1.5} />
                    </Pressable>
                  )}
                  <Pressable style={styles.actionBtn} onPress={() => shareEvent(displayEvent)}>
                    <Share2 size={16} color="rgba(255,255,255,0.6)" strokeWidth={1.5} />
                  </Pressable>
                </View>

              </ScrollView>

              {/* Get Tickets CTA — only when ticketUrl is available */}
              {displayEvent.ticketUrl && (
                <View style={styles.ctaWrapper}>
                  <LinearGradient
                    colors={CTA_GRADIENT}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.ctaBtn}
                  >
                    <Pressable
                      style={styles.ctaPressable}
                      onPress={() => openUrl(displayEvent.ticketUrl!)}
                    >
                      <Ticket size={16} color="#fff" strokeWidth={1.5} />
                      <Text style={styles.ctaText}>Get Tickets</Text>
                    </Pressable>
                  </LinearGradient>
                </View>
              )}
            </>
          )}
        </Animated.View>

      </View>
    </Modal>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
  },
  sheet: {
    height: SHEET_HEIGHT,
    backgroundColor: 'rgba(12, 12, 18, 0.95)',
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
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingBottom: 12,
  },
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
  title: {
    fontFamily: 'Inter_800ExtraBold',
    fontSize: 20,
    color: '#fff',
    lineHeight: 26,
    marginBottom: 10,
  },
  venueRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
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
});
