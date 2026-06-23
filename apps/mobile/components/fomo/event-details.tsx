import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import {
  Bookmark,
  Calendar,
  CheckCircle,
  Clock,
  Heart,
  MapPin,
  Navigation,
  Share2,
  Star,
  Ticket,
  X,
} from 'lucide-react-native';
import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
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
import { Colors, Gradients, Shadows } from '../../theme';
import { hasValidCoords } from '../../utils/geo';
import type { RelationshipType } from '../../utils/event-relationships-api';
import type { Event } from '../../types/ui';

// ─── Constants ────────────────────────────────────────────────────────────────

const { height: SCREEN_H } = Dimensions.get('window');
const SHEET_HEIGHT = SCREEN_H * 0.42;

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

interface RelActionConfig {
  type: RelationshipType;
  label: string;
  Icon: React.FC<{ size: number; color: string; fill?: string; strokeWidth?: number }>;
  activeColor: string;
}

const REL_ACTIONS: RelActionConfig[] = [
  { type: 'saved',      label: 'Save',       Icon: Bookmark,     activeColor: Colors.purple },
  { type: 'interested', label: 'Interested', Icon: Heart,        activeColor: Colors.magenta },
  { type: 'going',      label: 'Going',      Icon: CheckCircle,  activeColor: Colors.success },
];

interface EventDetailsProps {
  event: Event | null;
  onClose: () => void;
  /** Relationship types currently active for this event */
  relationships?: RelationshipType[];
  /** Called when user taps a relationship button */
  onToggleRelationship?: (type: RelationshipType) => void;
  /** Relationship types currently waiting for an API response */
  pendingRelationships?: RelationshipType[];
}

// ─── Component ────────────────────────────────────────────────────────────────

export function EventDetails({
  event,
  onClose,
  relationships = [],
  onToggleRelationship,
  pendingRelationships = [],
}: EventDetailsProps) {
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
    ? Colors.category[displayEvent.category]
    : Colors.category.Music;

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

                {/* Relationship actions: Saved / Interested / Going */}
                {onToggleRelationship && (
                  <View style={styles.relSection}>
                    {/* Intent hierarchy label */}
                    <View style={styles.relDivider}>
                      <View style={styles.relDividerLine} />
                      <Text style={styles.relDividerLabel}>YOUR INTENT</Text>
                      <View style={styles.relDividerLine} />
                    </View>

                    <View style={styles.relRow}>
                      {REL_ACTIONS.map(({ type, label, Icon, activeColor }) => {
                        const isActive  = relationships.includes(type);
                        const isPending = pendingRelationships.includes(type);
                        return (
                          <Pressable
                            key={type}
                            style={[
                              styles.relBtn,
                              isActive && {
                                borderColor: activeColor,
                                backgroundColor: `${activeColor}28`,
                                shadowColor: activeColor,
                                shadowOpacity: 0.35,
                                shadowRadius: 8,
                                shadowOffset: { width: 0, height: 0 },
                                elevation: 4,
                              },
                            ]}
                            onPress={() => onToggleRelationship(type)}
                            disabled={isPending}
                            accessibilityRole="button"
                            accessibilityLabel={isActive ? `Remove ${label}` : label}
                            accessibilityState={{ checked: isActive }}
                          >
                            {isPending ? (
                              <ActivityIndicator size={14} color={activeColor} />
                            ) : (
                              <Icon
                                size={15}
                                color={isActive ? activeColor : 'rgba(255,255,255,0.4)'}
                                fill={isActive ? activeColor : 'transparent'}
                                strokeWidth={1.5}
                              />
                            )}
                            <Text style={[styles.relLabel, isActive && { color: activeColor, fontFamily: 'Inter_600SemiBold' }]}>
                              {label}
                            </Text>
                          </Pressable>
                        );
                      })}
                    </View>
                  </View>
                )}

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
                    colors={Gradients.primaryCta}
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
  relSection: {
    marginBottom: 12,
    gap: 10,
  },
  relDivider: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  relDividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  relDividerLabel: {
    fontFamily: 'Inter_600SemiBold',
    fontSize: 9,
    letterSpacing: 1.4,
    color: 'rgba(255,255,255,0.30)',
  },
  relRow: {
    flexDirection: 'row',
    gap: 8,
  },
  relBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
    paddingVertical: 11,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: 'rgba(255,255,255,0.04)',
  },
  relLabel: {
    fontFamily: 'Inter_500Medium',
    fontSize: 11,
    color: 'rgba(255,255,255,0.40)',
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
    ...Shadows.ctaGlow,
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
