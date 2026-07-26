import { Check, MapPin, X } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';
import React, { useEffect, useRef, useState } from 'react';
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { LocationStatus } from '../../hooks/use-device-location';
import { Colors, Gradients, Radii, Spacing, Typography } from '../../theme';
import {
  DATE_PRESET_OPTIONS,
  DEFAULT_EXPLORE_FILTERS,
  EXPLORE_CATEGORY_OPTIONS,
  RADIUS_OPTIONS_KM,
  computeDateBounds,
  type BackendEventCategory,
  type DatePreset,
  type ExploreActiveFilters,
} from '../../utils/explore-filters';

interface ExploreFilterModalProps {
  visible: boolean;
  initialFilters: ExploreActiveFilters;
  locationStatus: LocationStatus;
  currentLocation: { lat: number; lng: number } | null;
  onApply: (filters: ExploreActiveFilters) => void;
  onCancel: () => void;
  /** Fired once, the moment the user turns the Near me draft toggle on — lets
   * the screen start resolving device location without duplicating the
   * permission flow or waiting for Apply. */
  onNearMeEnabled: () => void;
}

/** Per-category colour tokens from the Explore 9-entry mapping. */
function catColors(cat: BackendEventCategory) {
  const map = Colors.exploreCategory as Record<string, { border: string; text: string; bg: string }>;
  return map[cat] ?? map.Other;
}

/** Human-readable status for the Near-me location card. */
function locationStatusLabel(status: LocationStatus): string {
  switch (status) {
    case 'pending':
      return 'Resolving your location\u2026';
    case 'denied':
      return 'Location access was denied. Turn off Near me or enable location in your device settings.';
    case 'unavailable':
      return 'Location services are unavailable. Turn off Near me to continue.';
    case 'error':
      return 'Location could not be determined. Turn off Near me or try again.';
    default:
      return '';
  }
}

export function ExploreFilterModal({
  visible,
  initialFilters,
  locationStatus,
  currentLocation,
  onApply,
  onCancel,
  onNearMeEnabled,
}: ExploreFilterModalProps) {
  const insets = useSafeAreaInsets();

  const [draftCategories, setDraftCategories] = useState<BackendEventCategory[]>(
    initialFilters.categories,
  );
  const [draftDatePreset, setDraftDatePreset] = useState<DatePreset>(initialFilters.datePreset);
  const [draftNearMe, setDraftNearMe] = useState(initialFilters.nearMe);
  const [draftRadiusKm, setDraftRadiusKm] = useState(initialFilters.radiusKm);

  // Guards against a rapid double-tap on Apply running handleApply twice
  // before the modal has visually closed (state updates aren't synchronous
  // with the tap) — reset every time the modal (re-)opens.
  const hasAppliedRef = useRef(false);

  // Reset the draft from whatever is currently active every time the modal
  // (re-)opens — draft edits while closed/between sessions must never leak.
  // Intentionally keyed on `visible` only: `initialFilters` is read fresh
  // each time this runs, but must not itself retrigger the reset while the
  // modal is already open (that would clobber in-progress draft edits).
  useEffect(() => {
    if (visible) {
      hasAppliedRef.current = false;
      setDraftCategories(initialFilters.categories);
      setDraftDatePreset(initialFilters.datePreset);
      setDraftNearMe(initialFilters.nearMe);
      setDraftRadiusKm(initialFilters.radiusKm);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible]);

  const toggleCategory = (value: BackendEventCategory) => {
    setDraftCategories((prev) =>
      prev.includes(value) ? prev.filter((c) => c !== value) : [...prev, value],
    );
  };

  const handleNearMeToggle = () => {
    const next = !draftNearMe;
    setDraftNearMe(next);
    if (next) onNearMeEnabled();
  };

  const handleReset = () => {
    setDraftCategories(DEFAULT_EXPLORE_FILTERS.categories);
    setDraftDatePreset(DEFAULT_EXPLORE_FILTERS.datePreset);
    setDraftNearMe(DEFAULT_EXPLORE_FILTERS.nearMe);
    setDraftRadiusKm(DEFAULT_EXPLORE_FILTERS.radiusKm);
  };

  const nearMeBlocked = draftNearMe && locationStatus !== 'granted';

  const handleApply = () => {
    if (nearMeBlocked || hasAppliedRef.current) return;
    hasAppliedRef.current = true;
    // Canonical enum order regardless of selection order, so the request
    // identity (and any downstream JSON-based comparison) is deterministic.
    const orderedCategories = EXPLORE_CATEGORY_OPTIONS.map((o) => o.value).filter((v) =>
      draftCategories.includes(v),
    );
    onApply({
      categories: orderedCategories,
      datePreset: draftDatePreset,
      dateBounds: computeDateBounds(draftDatePreset, new Date()),
      nearMe: draftNearMe,
      radiusKm: draftRadiusKm,
      location: draftNearMe && currentLocation ? currentLocation : null,
    });
  };

  const footerBottom = Math.max(insets.bottom, Spacing.base);

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onCancel}>
      <View style={styles.overlay}>
        <Pressable
          style={StyleSheet.absoluteFill}
          onPress={onCancel}
          accessibilityLabel="Close filters"
        />

        <View style={[styles.sheet, { paddingBottom: 0 }]}>
          {/* ── Drag handle ────────────────────────────────────────── */}
          <View style={styles.dragHandle} />

          {/* ── Fixed header ───────────────────────────────────────── */}
          <View style={styles.header}>
            <Text style={styles.title}>Filters</Text>
            <Pressable
              onPress={onCancel}
              hitSlop={12}
              accessibilityRole="button"
              accessibilityLabel="Close filters"
            >
              <X size={20} color={Colors.textSecondary} strokeWidth={2} />
            </Pressable>
          </View>
          <View style={styles.headerDivider} />

          {/* ── Scrollable content ─────────────────────────────────── */}
          <ScrollView
            showsVerticalScrollIndicator={false}
            style={styles.scroll}
            contentContainerStyle={styles.scrollContent}
            keyboardShouldPersistTaps="handled"
          >
            {/* ── Category ─────────────────────────────────────────── */}
            <Text style={styles.sectionLabel}>Category</Text>
            <View style={styles.chipRow}>
              {EXPLORE_CATEGORY_OPTIONS.map(({ value, label }) => {
                const active = draftCategories.includes(value);
                const c = catColors(value);
                return (
                  <Pressable
                    key={value}
                    onPress={() => toggleCategory(value)}
                    style={[
                      styles.chip,
                      active && { backgroundColor: c.bg, borderColor: c.border },
                    ]}
                    accessibilityRole="button"
                    accessibilityState={{ selected: active }}
                    accessibilityLabel={`${label}, ${active ? 'selected' : 'not selected'}`}
                  >
                    {active && (
                      <Check size={12} color={c.text} strokeWidth={2.5} style={styles.chipCheck} />
                    )}
                    <Text
                      style={[
                        styles.chipLabel,
                        active && { color: c.text, fontFamily: Typography.font.semiBold },
                      ]}
                    >
                      {label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            {/* ── Date ────────────────────────────────────────────── */}
            <Text style={styles.sectionLabel}>Date</Text>
            <View style={styles.chipRow}>
              {DATE_PRESET_OPTIONS.map(({ value, label }) => {
                const active = draftDatePreset === value;
                return (
                  <Pressable
                    key={value}
                    onPress={() => setDraftDatePreset(value)}
                    style={[styles.chip, active && styles.chipActive]}
                    accessibilityRole="button"
                    accessibilityState={{ selected: active }}
                    accessibilityLabel={`${label}, ${active ? 'selected' : 'not selected'}`}
                  >
                    <Text style={[styles.chipLabel, active && styles.chipLabelActive]}>
                      {label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            {/* ── Location ────────────────────────────────────────── */}
            <Text style={styles.sectionLabel}>Location</Text>

            <Pressable
              onPress={handleNearMeToggle}
              style={[
                styles.nearMeCard,
                draftNearMe && styles.nearMeCardActive,
              ]}
              accessibilityRole="button"
              accessibilityState={{ selected: draftNearMe, disabled: nearMeBlocked }}
              accessibilityLabel={`Near me, ${draftNearMe ? 'enabled' : 'not enabled'}`}
            >
              <MapPin
                size={18}
                color={draftNearMe ? Colors.brandPrimary : Colors.textMuted}
                strokeWidth={2}
                style={styles.nearMeIcon}
              />
              <View style={styles.nearMeTextCol}>
                <Text
                  style={[
                    styles.nearMeLabel,
                    draftNearMe && styles.nearMeLabelActive,
                  ]}
                >
                  Near me
                </Text>
                <Text style={styles.nearMeSubtitle}>Use your current location</Text>
              </View>
              <View
                style={[
                  styles.toggleCircle,
                  draftNearMe && styles.toggleCircleActive,
                ]}
              >
                {draftNearMe && <Check size={12} color={Colors.background} strokeWidth={3} />}
              </View>
            </Pressable>

            {/* ── Location resolving / warning ───────────────────── */}
            {locationStatus === 'pending' && (
              <Text style={styles.locationStatus} accessibilityLiveRegion="polite">
                {locationStatusLabel(locationStatus)}
              </Text>
            )}
            {nearMeBlocked && (
              <Text style={styles.warning} accessibilityLiveRegion="polite">
                {locationStatusLabel(locationStatus)}
              </Text>
            )}

            {/* ── Radius ──────────────────────────────────────────── */}
            {draftNearMe && (
              <>
                <Text style={styles.distanceLabel}>Distance</Text>
                <View style={styles.radiusRow}>
                  {RADIUS_OPTIONS_KM.map((km) => {
                    const active = draftRadiusKm === km;
                    return (
                      <Pressable
                        key={km}
                        onPress={() => setDraftRadiusKm(km)}
                        style={[styles.radiusChip, active && styles.radiusChipActive]}
                        accessibilityRole="button"
                        accessibilityState={{ selected: active }}
                        accessibilityLabel={`${km} kilometers, ${active ? 'selected' : 'not selected'}`}
                      >
                        <Text
                          style={[
                            styles.radiusChipLabel,
                            active && styles.radiusChipLabelActive,
                          ]}
                          numberOfLines={1}
                          adjustsFontSizeToFit
                          minimumFontScale={0.8}
                        >
                          {km} km
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>
              </>
            )}

            {/* Bottom spacer so last controls don't touch the footer */}
            <View style={{ height: Spacing.base }} />
          </ScrollView>

          {/* ── Fixed action footer ───────────────────────────────── */}
          <View style={styles.footerDivider} />
          <View style={[styles.footer, { paddingBottom: footerBottom }]}>
            <TouchableOpacity
              onPress={handleReset}
              activeOpacity={0.7}
              style={styles.footerResetBtn}
              accessibilityRole="button"
              accessibilityLabel="Reset all filters to defaults"
            >
              <Text style={styles.footerResetLabel}>Reset filters</Text>
            </TouchableOpacity>

            <TouchableOpacity
              onPress={handleApply}
              activeOpacity={0.78}
              disabled={nearMeBlocked}
              style={[
                styles.footerPrimaryBtn,
                nearMeBlocked && styles.footerPrimaryDisabled,
              ]}
              accessibilityRole="button"
              accessibilityLabel={
                nearMeBlocked ? 'Show events, unavailable' : 'Show events'
              }
              accessibilityState={{ disabled: nearMeBlocked }}
            >
              <LinearGradient
                colors={Gradients.primaryCta}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.footerPrimaryGradient}
              >
                <Text style={styles.footerPrimaryLabel}>Show events</Text>
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  // ── Overlay & sheet ──────────────────────────────────────────────────────
  overlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
  },
  sheet: {
    maxHeight: '85%',
    backgroundColor: Colors.surface,
    borderTopLeftRadius: Radii['2xl'],
    borderTopRightRadius: Radii['2xl'],
    borderTopWidth: 1,
    borderColor: Colors.border,
    paddingTop: 0,
    paddingHorizontal: Spacing.base,
  },

  // ── Drag handle ──────────────────────────────────────────────────────────
  dragHandle: {
    width: 36,
    height: 4,
    borderRadius: 2,
    backgroundColor: Colors.border,
    alignSelf: 'center',
    marginTop: Spacing.sm,
    marginBottom: Spacing.sm,
  },

  // ── Header ───────────────────────────────────────────────────────────────
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingBottom: Spacing.md,
  },
  title: {
    fontFamily: Typography.font.extraBold,
    fontSize: Typography.size.xl,
    color: Colors.textPrimary,
  },
  headerDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: Colors.borderSubtle,
    marginHorizontal: -Spacing.base,
  },

  // ── Scrollable content ───────────────────────────────────────────────────
  scroll: {
    flexGrow: 0,
  },
  scrollContent: {
    paddingTop: Spacing.lg,
    paddingBottom: Spacing.sm,
  },

  // ── Section labels ───────────────────────────────────────────────────────
  sectionLabel: {
    fontFamily: Typography.font.bold,
    fontSize: Typography.size.sm,
    letterSpacing: 1,
    color: Colors.textMuted,
    textTransform: 'uppercase',
    marginBottom: Spacing.sm,
    marginTop: Spacing.xl,
  },

  // ── Chips (categories, dates, radii) ─────────────────────────────────────
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -Spacing.xs,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm + 2, // ~10px for 44px touch with border+lineHeight
    borderRadius: Radii.sm,
    borderWidth: 1,
    borderColor: Colors.borderGlass,
    backgroundColor: Colors.surfaceGlass,
    marginHorizontal: Spacing.xs,
    marginBottom: Spacing.sm,
  },
  chipActive: {
    borderColor: Colors.borderFocus,
    backgroundColor: Colors.purpleDim,
  },
  chipCheck: {
    marginRight: Spacing.xs,
  },
  chipLabel: {
    fontFamily: Typography.font.medium,
    fontSize: Typography.size.sm,
    color: Colors.textSecondary,
  },
  chipLabelActive: {
    color: Colors.textPrimary,
    fontFamily: Typography.font.semiBold,
  },

  // ── Near me card ─────────────────────────────────────────────────────────
  nearMeCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surfaceGlass,
    borderWidth: 1,
    borderColor: Colors.borderGlass,
    borderRadius: Radii.md,
    paddingHorizontal: Spacing.md + 2, // ~14px
    paddingVertical: Spacing.sm + 2, // ~10px → ~64px total
    minHeight: 64,
  },
  nearMeCardActive: {
    borderColor: Colors.borderFocus,
  },
  nearMeIcon: {
    flexShrink: 0,
  },
  nearMeTextCol: {
    flex: 1,
    minWidth: 0,
    marginLeft: Spacing.md,
  },
  nearMeLabel: {
    fontFamily: Typography.font.medium,
    fontSize: Typography.size.md,
    color: Colors.textPrimary,
  },
  nearMeLabelActive: {
    fontFamily: Typography.font.semiBold,
  },
  nearMeSubtitle: {
    fontFamily: Typography.font.regular,
    fontSize: Typography.size.sm,
    color: Colors.textMuted,
    marginTop: 2,
  },
  toggleCircle: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: Colors.border,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    marginLeft: Spacing.md,
  },
  toggleCircleActive: {
    backgroundColor: Colors.brandPrimary,
    borderColor: Colors.brandPrimary,
  },

  // ── Location resolving / warning ─────────────────────────────────────────
  locationStatus: {
    fontFamily: Typography.font.regular,
    fontSize: Typography.size.sm,
    color: Colors.textMuted,
    marginTop: Spacing.md,
  },

  // ── Distance section ─────────────────────────────────────────────────────
  distanceLabel: {
    fontFamily: Typography.font.bold,
    fontSize: Typography.size.sm,
    letterSpacing: 1,
    color: Colors.textMuted,
    textTransform: 'uppercase',
    marginTop: Spacing.md + 2, // ~14px
    marginBottom: Spacing.sm,
  },
  radiusRow: {
    flexDirection: 'row',
    marginHorizontal: -3, // offset 6px item margins
  },
  radiusChip: {
    flex: 1,
    minWidth: 0,
    height: 42,
    borderRadius: Radii.sm,
    borderWidth: 1,
    borderColor: Colors.borderGlass,
    backgroundColor: 'transparent',
    alignItems: 'center',
    justifyContent: 'center',
    marginHorizontal: 3,
  },
  radiusChipActive: {
    borderColor: Colors.borderFocus,
    backgroundColor: Colors.purpleDim,
  },
  radiusChipLabel: {
    fontFamily: Typography.font.medium,
    fontSize: Typography.size.sm + 1,
    color: Colors.textSecondary,
  },
  radiusChipLabelActive: {
    color: Colors.textPrimary,
    fontFamily: Typography.font.semiBold,
  },

  // ── Warning ──────────────────────────────────────────────────────────────
  warning: {
    fontFamily: Typography.font.regular,
    fontSize: Typography.size.sm,
    color: Colors.feedbackWarning,
    marginTop: Spacing.md,
  },

  // ── Footer ───────────────────────────────────────────────────────────────
  footerDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: Colors.borderSubtle,
    marginHorizontal: -Spacing.base,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: Spacing.md,
    paddingHorizontal: 0,
    backgroundColor: Colors.surface,
  },
  // ── Reset filters ──────────────────────────────────────────────────
  footerResetBtn: {
    width: 116,
    height: 48,
    borderRadius: Radii.md,
    backgroundColor: Colors.surfaceGlass,
    borderWidth: 1,
    borderColor: Colors.borderGlass,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  footerResetLabel: {
    fontFamily: Typography.font.semiBold,
    fontSize: 13,
    lineHeight: 16,
    includeFontPadding: false,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
  // ── Show events ────────────────────────────────────────────────────
  footerPrimaryBtn: {
    flex: 1,
    minWidth: 0,
    height: 48,
    marginLeft: Spacing.md,
    borderRadius: Radii.md,
    overflow: 'hidden',
  },
  footerPrimaryDisabled: {
    opacity: 0.45,
  },
  footerPrimaryGradient: {
    flex: 1,
    width: '100%',
    height: '100%',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: Radii.md,
  },
  footerPrimaryLabel: {
    fontFamily: Typography.font.bold,
    fontSize: 14,
    lineHeight: 18,
    includeFontPadding: false,
    color: Colors.textPrimary,
    textAlign: 'center',
  },
});
