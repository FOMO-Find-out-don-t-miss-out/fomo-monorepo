import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { CheckCircle, Heart } from 'lucide-react-native';
import React from 'react';

import { Colors, Radii, Spacing, Typography } from '../../theme';
import type { EventIntent } from '../../types/ui';

// ── Config ────────────────────────────────────────────────────────────────────

interface ButtonConfig {
  type: 'interested' | 'going';
  label: string;
  Icon: React.FC<{ size: number; color: string; fill?: string; strokeWidth?: number }>;
  activeColor: string;
  fillOnActive: boolean;
}

const BUTTONS: ButtonConfig[] = [
  {
    type:         'interested',
    label:        'Interested',
    Icon:         Heart,
    activeColor:  Colors.magenta,
    fillOnActive: true,
  },
  {
    type:         'going',
    label:        'Going',
    Icon:         CheckCircle,
    activeColor:  Colors.success,
    fillOnActive: false,
  },
];

// ── Props ─────────────────────────────────────────────────────────────────────

export interface IntentSelectorProps {
  intent: EventIntent;
  pending?: boolean;
  onSelect: (intent: 'interested' | 'going') => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function IntentSelector({ intent, pending = false, onSelect }: IntentSelectorProps) {
  return (
    <View style={styles.section}>
      {/* Section label */}
      <View style={styles.divider}>
        <View style={styles.dividerLine} />
        <Text style={styles.dividerLabel}>YOUR INTENT</Text>
        <View style={styles.dividerLine} />
      </View>

      {/* Two equal-width buttons */}
      <View style={styles.row}>
        {BUTTONS.map(({ type, label, Icon, activeColor, fillOnActive }) => {
          const isActive    = intent === type;
          const showSpinner = pending && isActive;

          return (
            <Pressable
              key={type}
              // android_ripple disabled — we use opacity on press instead, which
              // is consistent across platforms and avoids ripple overflowing
              // the border radius on older Android versions.
              android_ripple={null}
              style={({ pressed }) => [
                styles.btn,
                isActive
                  ? {
                      borderColor: activeColor,
                      backgroundColor: `${activeColor}28`,
                    }
                  : styles.btnInactive,
                pressed && !pending && styles.btnPressed,
              ]}
              onPress={() => { if (!pending) onSelect(type); }}
              accessibilityRole="button"
              accessibilityLabel={isActive ? `Remove ${label}` : label}
              accessibilityState={{ checked: isActive, busy: pending }}
            >
              {showSpinner ? (
                <ActivityIndicator size={16} color={activeColor} />
              ) : (
                <Icon
                  size={18}
                  color={isActive ? activeColor : Colors.textSecondary}
                  fill={fillOnActive && isActive ? activeColor : 'transparent'}
                  strokeWidth={1.5}
                />
              )}
              <Text
                style={[
                  styles.btnLabel,
                  isActive && { color: activeColor },
                ]}
              >
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  section: {
    marginBottom: Spacing.md,
    gap: 10,
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: 'rgba(255,255,255,0.12)',
  },
  dividerLabel: {
    fontFamily: Typography.font.semiBold,
    fontSize: 9,
    letterSpacing: 1.4,
    color: 'rgba(255,255,255,0.40)',
  },
  row: {
    flexDirection: 'row',
    gap: 10,
  },
  btn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 7,
    height: 48,
    borderRadius: Radii.md,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.20)',
    backgroundColor: 'rgba(255,255,255,0.04)',
  },
  btnInactive: {
    borderColor: 'rgba(255,255,255,0.20)',
    backgroundColor: 'rgba(255,255,255,0.04)',
  },
  btnPressed: {
    opacity: 0.60,
  },
  btnLabel: {
    fontFamily: Typography.font.semiBold,
    fontSize: 13,
    color: Colors.textSecondary,
  },
});
