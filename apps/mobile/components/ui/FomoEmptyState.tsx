import React from 'react';
import { Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';
import { Colors, Radii, Spacing, Typography } from '../../theme';

interface FomoEmptyStateProps {
  icon: React.ReactNode;
  message: string;
  sub?: string;
  action?: { label: string; onPress: () => void };
  style?: StyleProp<ViewStyle>;
}

/** Centered empty-state: icon + heading + optional sub-text + optional action button. */
export function FomoEmptyState({ icon, message, sub, action, style }: FomoEmptyStateProps) {
  return (
    <View style={[styles.container, style]}>
      <View style={styles.iconWrap}>{icon}</View>
      <Text style={styles.message}>{message}</Text>
      {sub ? <Text style={styles.sub}>{sub}</Text> : null}
      {action ? (
        <Pressable
          style={({ pressed }) => [styles.actionBtn, pressed && styles.actionBtnPressed]}
          onPress={action.onPress}
          accessibilityRole="button"
        >
          <Text style={styles.actionLabel}>{action.label}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Spacing['2xl'],
    gap: Spacing.md,
  },
  iconWrap: {
    marginBottom: Spacing.sm,
    opacity: 0.5,
  },
  message: {
    fontFamily: Typography.font.semiBold,
    fontSize: Typography.size.lg,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
  sub: {
    fontFamily: Typography.font.regular,
    fontSize: Typography.size.base,
    color: Colors.textMuted,
    textAlign: 'center',
    lineHeight: 20,
  },
  actionBtn: {
    marginTop: Spacing.xs,
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.sm,
    borderRadius: Radii.full,
    borderWidth: 1,
    borderColor: Colors.borderFocus,
  },
  actionBtnPressed: {
    backgroundColor: Colors.purpleDim,
  },
  actionLabel: {
    fontFamily: Typography.font.semiBold,
    fontSize: Typography.size.base,
    color: Colors.brandPrimary,
  },
});
