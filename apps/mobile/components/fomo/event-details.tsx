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
import React, { useEffect, useRef } from 'react';
import {
  Animated,
  Dimensions,
  Linking,
  Modal,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  View,
} from 'react-native';
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

function ctaUrl(event: Event): string | null {
  return event.ticketUrl ?? event.sourceUrl ?? null;
}

function hasValidCoordinates(event: Event): boolean {
  const { lat, lng } = event;
  return (
    typeof lat === 'number' &&
    typeof lng === 'number' &&
    !Number.isNaN(lat) &&
    !Number.isNaN(lng) &&
    !(lat === 0 && lng === 0)
  );
}

async function openDirections(event: Event): Promise<void> {
  if (!hasValidCoordinates(event)) return;
  const url = `https://www.google.com/maps/search/?api=1&query=${event.lat},${event.lng}`;
  try {
    await Linking.openURL(url);
  } catch {
    // silently ignore — openURL failures are non-fatal
  }
}

async function openUrl(url: string): Promise<void> {
  try {
    const supported = await Linking.canOpenURL(url);
    if (supported) await Linking.openURL(url);
  } catch {
    // silently ignore — user will see nothing happen, not a crash
  }
}

async function shareEvent(event: Event): Promise<void> {
  const url = ctaUrl(event);
  try {
    await Share.share({
      title: event.title,
      message: url ? `${event.title} — ${url}` : event.title,
      url: url ?? undefined,
    });
  } catch {
    // dismissed or unsupported
  }
}


// ─── Props ────────────────────────────────────────────────────────────────────

interface EventDetailsProps {
  event: Event | null;
  onClose: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

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

  const url = event ? ctaUrl(event) : null;
  const canOpenDirections = event ? hasValidCoordinates(event) : false;

  return (
    <Modal
      visible={event !== null}
      transparent
      animationType="slide"
      statusBarTranslucent
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>

        {/* Backdrop */}
        <Animated.View style={[styles.backdrop, { opacity: backdropOpacity }]}>
          <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        </Animated.View>

        {/* Bottom sheet */}
        <View style={styles.sheet}>
          <BlurView intensity={20} tint="dark" style={StyleSheet.absoluteFill} />

          {event && (
            <>
              <View style={styles.handleBar} />

              <Pressable style={styles.closeBtn} onPress={onClose} hitSlop={8}>
                <X size={16} color="rgba(255,255,255,0.7)" strokeWidth={1.5} />
              </Pressable>

              <ScrollView
                style={styles.scroll}
                contentContainerStyle={styles.scrollContent}
                showsVerticalScrollIndicator={false}
                bounces={false}
              >
                {/* Header: category badge + hype badge (only when high) */}
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

                {/* Venue — Directions deferred to FOMO-168 (needs device location) */}
                <View style={styles.venueRow}>
                  <MapPin size={14} color="rgba(255,255,255,0.6)" strokeWidth={1.5} />
                  <Text style={styles.venueText} numberOfLines={1}>{event.venue}</Text>
                  {event.distance != null && (
                    <Text style={styles.distanceText}>({event.distance})</Text>
                  )}
                </View>

                {/* Date / Time pills */}
                <View style={styles.pillRow}>
                  <View style={styles.pill}>
                    <Calendar size={14} color="#22D3EE" strokeWidth={1.5} />
                    <Text style={styles.pillCyan}>{event.date}</Text>
                  </View>
                  <View style={styles.pill}>
                    <Clock size={14} color="#22D3EE" strokeWidth={1.5} />
                    <Text style={styles.pillCyan}>{event.time}</Text>
                  </View>
                </View>

                {/* Action row — Directions (when coords valid) + Share (Heart/Save deferred to post-auth) */}
                <View style={styles.actionRow}>
                  {canOpenDirections && (
                    <Pressable style={styles.actionBtn} onPress={() => openDirections(event)}>
                      <Navigation size={16} color="rgba(255,255,255,0.6)" strokeWidth={1.5} />
                    </Pressable>
                  )}
                  <Pressable style={styles.actionBtn} onPress={() => shareEvent(event)}>
                    <Share2 size={16} color="rgba(255,255,255,0.6)" strokeWidth={1.5} />
                  </Pressable>
                </View>

              </ScrollView>

              {/* Get Tickets CTA — only shown when a URL exists */}
              {url && (
                <View style={styles.ctaWrapper}>
                  <LinearGradient
                    colors={CTA_GRADIENT}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.ctaBtn}
                  >
                    <Pressable
                      style={styles.ctaPressable}
                      onPress={() => openUrl(url)}
                    >
                      <Ticket size={16} color="#fff" strokeWidth={1.5} />
                      <Text style={styles.ctaText}>
                        {event.ticketUrl ? 'Get Tickets' : 'View Source'}
                      </Text>
                    </Pressable>
                  </LinearGradient>
                </View>
              )}
            </>
          )}
        </View>

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
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
  },
  sheet: {
    height: SHEET_HEIGHT,
    backgroundColor: 'rgba(12, 12, 18, 0.88)',
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
