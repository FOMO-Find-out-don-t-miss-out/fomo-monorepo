import { AlertCircle } from 'lucide-react-native';
import React from 'react';
import { Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';
import { Colors, Radii, Spacing, Typography } from '../../theme';

interface FomoErrorStateProps {
  message?: string;
  onRetry?: () => void;
  style?: StyleProp<ViewStyle>;
}

/** Centered error state with optional retry action. */
export function FomoErrorState({
  message = 'Something went wrong',
  onRetry,
  style,
}: FomoErrorStateProps) {
  return (
    <View style={[styles.container, style]}>
      <AlertCircle size={36} color={Colors.error} strokeWidth={1.5} style={styles.icon} />
      <Text style={styles.message}>{message}</Text>
      {onRetry ? (
        <Pressable
          style={({ pressed }) => [styles.retryBtn, pressed && styles.retryBtnPressed]}
          onPress={onRetry}
          accessibilityRole="button"
          accessibilityLabel="Retry"
        >
          <Text style={styles.retryLabel}>Retry</Text>
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
  icon: {
    marginBottom: Spacing.xs,
    opacity: 0.8,
  },
  message: {
    fontFamily: Typography.font.regular,
    fontSize: Typography.size.base,
    color: Colors.textMuted,
    textAlign: 'center',
    letterSpacing: 0.3,
  },
  retryBtn: {
    marginTop: Spacing.xs,
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.sm,
    borderRadius: Radii.full,
    borderWidth: 1,
    borderColor: `${Colors.purple}66`,
  },
  retryBtnPressed: {
    backgroundColor: Colors.purpleDim,
  },
  retryLabel: {
    fontFamily: Typography.font.semiBold,
    fontSize: Typography.size.base,
    color: Colors.purple,
  },
});
