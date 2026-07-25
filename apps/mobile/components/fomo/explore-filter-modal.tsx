import { Check, MapPin, X } from 'lucide-react-native';
import React, { useEffect, useRef, useState } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { LocationStatus } from '../../hooks/use-device-location';
import { Colors, Radii, Spacing, Typography } from '../../theme';
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
import { FomoButton } from '../ui';

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

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onCancel}>
      <View style={styles.overlay}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onCancel} accessibilityLabel="Close filters" />

        <View style={[styles.sheet, { paddingBottom: insets.bottom + Spacing.base }]}>
          <View style={styles.header}>
            <Text style={styles.title}>Filters</Text>
            <Pressable onPress={onCancel} hitSlop={8} accessibilityRole="button" accessibilityLabel="Close">
              <X size={20} color={Colors.textSecondary} strokeWidth={2} />
            </Pressable>
          </View>

          <ScrollView showsVerticalScrollIndicator={false} style={styles.scroll}>
            <Text style={styles.sectionLabel}>Category</Text>
            <View style={styles.chipRow}>
              {EXPLORE_CATEGORY_OPTIONS.map(({ value, label }) => {
                const active = draftCategories.includes(value);
                return (
                  <Pressable
                    key={value}
                    onPress={() => toggleCategory(value)}
                    style={[styles.chip, active && styles.chipActive]}
                    accessibilityRole="button"
                    accessibilityState={{ selected: active }}
                  >
                    {active && <Check size={12} color={Colors.textPrimary} strokeWidth={2.5} />}
                    <Text style={[styles.chipLabel, active && styles.chipLabelActive]}>{label}</Text>
                  </Pressable>
                );
              })}
            </View>

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
                  >
                    <Text style={[styles.chipLabel, active && styles.chipLabelActive]}>{label}</Text>
                  </Pressable>
                );
              })}
            </View>

            <Text style={styles.sectionLabel}>Location</Text>
            <Pressable
              onPress={handleNearMeToggle}
              style={[styles.chip, styles.nearMeRow, draftNearMe && styles.chipActive]}
              accessibilityRole="button"
              accessibilityState={{ selected: draftNearMe }}
            >
              <MapPin
                size={14}
                color={draftNearMe ? Colors.textPrimary : Colors.textSecondary}
                strokeWidth={2}
              />
              <Text style={[styles.chipLabel, draftNearMe && styles.chipLabelActive]}>Near me</Text>
            </Pressable>

            {draftNearMe && (
              <View style={styles.chipRow}>
                {RADIUS_OPTIONS_KM.map((km) => {
                  const active = draftRadiusKm === km;
                  return (
                    <Pressable
                      key={km}
                      onPress={() => setDraftRadiusKm(km)}
                      style={[styles.chip, active && styles.chipActive]}
                      accessibilityRole="button"
                      accessibilityState={{ selected: active }}
                    >
                      <Text style={[styles.chipLabel, active && styles.chipLabelActive]}>{km} km</Text>
                    </Pressable>
                  );
                })}
              </View>
            )}

            {nearMeBlocked && (
              <Text style={styles.warning}>
                Turn on location access to use Near me, or turn Near me off to continue.
              </Text>
            )}
          </ScrollView>

          <View style={styles.footer}>
            <FomoButton label="Reset" variant="ghost" onPress={handleReset} style={styles.footerBtn} />
            <FomoButton
              label="Apply"
              variant="primary"
              onPress={handleApply}
              disabled={nearMeBlocked}
              style={styles.footerBtn}
            />
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
  },
  sheet: {
    maxHeight: '80%',
    backgroundColor: Colors.surface,
    borderTopLeftRadius: Radii['2xl'],
    borderTopRightRadius: Radii['2xl'],
    borderTopWidth: 1,
    borderColor: Colors.border,
    paddingTop: Spacing.base,
    paddingHorizontal: Spacing.base,
  },
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
  scroll: {
    flexGrow: 0,
  },
  sectionLabel: {
    fontFamily: Typography.font.bold,
    fontSize: Typography.size.xs,
    letterSpacing: 1,
    color: Colors.textMuted,
    marginTop: Spacing.base,
    marginBottom: Spacing.sm,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: Radii.full,
    borderWidth: 1,
    borderColor: Colors.borderGlass,
    backgroundColor: Colors.surfaceGlass,
  },
  chipActive: {
    borderColor: Colors.borderFocus,
    backgroundColor: Colors.purpleDim,
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
  nearMeRow: {
    alignSelf: 'flex-start',
  },
  warning: {
    fontFamily: Typography.font.regular,
    fontSize: Typography.size.sm,
    color: Colors.feedbackWarning,
    marginTop: Spacing.md,
  },
  footer: {
    flexDirection: 'row',
    gap: Spacing.md,
    paddingTop: Spacing.base,
  },
  footerBtn: {
    flex: 1,
  },
});
