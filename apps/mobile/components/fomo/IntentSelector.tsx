import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { CheckCircle, Heart } from 'lucide-react-native';
import React from 'react';

import { Colors, Radii, Typography } from '../../theme';
import { perfCountRender } from '../../utils/performance-debug';
import type { EventIntent } from '../../types/ui';

type ButtonDef = {
  type:         'interested' | 'going';
  label:        string;
  Icon:         React.FC<{ size: number; color: string; fill?: string; strokeWidth?: number }>;
  color:        string;
  fillOnActive: boolean;
};

const BUTTONS: ButtonDef[] = [
  { type: 'interested', label: 'Interested', Icon: Heart,       color: Colors.magenta, fillOnActive: true  },
  { type: 'going',      label: 'Going',      Icon: CheckCircle, color: Colors.cyan,    fillOnActive: false },
];

export interface IntentSelectorProps {
  intent:   EventIntent;
  pending?: boolean;
  onSelect: (intent: 'interested' | 'going') => void;
}

export function IntentSelector({ intent, pending = false, onSelect }: IntentSelectorProps) {
  perfCountRender('IntentSelector');
  return (
    <View style={styles.section}>
      <Text style={styles.label}>YOUR INTENT</Text>

      <View style={styles.row}>
        {BUTTONS.map(({ type, label, Icon, color, fillOnActive }) => {
          const isActive    = intent === type;
          const showSpinner = pending && isActive;
          const isDimmed    = pending && !isActive;

          return (
            // Pressable = touch target only (no visual styles here — avoids
            // Android issues where styles on Pressable itself can be ignored).
            <Pressable
              key={type}
              android_ripple={null}
              onPress={() => { if (!pending) onSelect(type); }}
              style={styles.pressable}
              accessibilityRole="button"
              accessibilityLabel={isActive ? `Remove ${label}` : `Mark as ${label}`}
              accessibilityState={{ checked: isActive, busy: showSpinner }}
            >
              {({ pressed }) => (
                // Inner View carries all visual styling.
                <View
                  style={[
                    styles.btn,
                    isActive && { borderColor: color, backgroundColor: `${color}33` },
                    isDimmed && styles.btnDimmed,
                    pressed && !pending && styles.btnPressed,
                  ]}
                >
                  {showSpinner ? (
                    <ActivityIndicator size={16} color={color} />
                  ) : (
                    <Icon
                      size={18}
                      color={isActive ? color : Colors.textSecondary}
                      fill={fillOnActive && isActive ? color : 'transparent'}
                      strokeWidth={2}
                    />
                  )}
                  <Text style={[styles.btnLabel, isActive && { color, fontFamily: Typography.font.semiBold }]}>
                    {label}
                  </Text>
                </View>
              )}
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    gap:          10,
    marginBottom: 12,
  },

  label: {
    fontFamily:    Typography.font.semiBold,
    fontSize:      9,
    letterSpacing: 1.6,
    color:         'rgba(255,255,255,0.35)',
  },

  row: {
    flexDirection: 'row',
    gap:           10,
  },

  // Touch target — flex:1 so both buttons share equal width.
  pressable: {
    flex: 1,
  },

  // Visual button shell — all border/bg/layout lives here, not on Pressable.
  btn: {
    flexDirection:   'row',
    alignItems:      'center',
    justifyContent:  'center',
    gap:             8,
    paddingVertical: 13,
    borderRadius:    Radii.md,
    borderWidth:     1.5,
    borderColor:     'rgba(255,255,255,0.35)',
    backgroundColor: 'rgba(255,255,255,0.08)',
  },

  btnPressed: {
    opacity: 0.60,
  },

  btnDimmed: {
    opacity: 0.35,
  },

  btnLabel: {
    fontFamily:    Typography.font.medium,
    fontSize:      13,
    letterSpacing: 0.3,
    color:         Colors.textSecondary,
  },
});
