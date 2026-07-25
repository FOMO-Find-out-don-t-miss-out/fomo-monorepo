import { LinearGradient } from 'expo-linear-gradient';
import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  type ViewStyle,
} from 'react-native';
import { Colors, Gradients, Radii, Spacing, Typography } from '../../theme';

type Variant = 'primary' | 'ghost' | 'danger';

interface FomoButtonProps {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  icon?: React.ReactNode;
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
}

/**
 * FOMO primary action button.
 *
 * - `primary`: neon-purple gradient — CTAs, main actions.
 * - `ghost`:   glass border — secondary actions, cancel, log-out.
 * - `danger`:  red border — destructive actions.
 */
export function FomoButton({
  label,
  onPress,
  variant = 'primary',
  icon,
  disabled = false,
  loading = false,
  style,
}: FomoButtonProps) {
  const isDisabled = disabled || loading;

  if (variant === 'primary') {
    return (
      <LinearGradient
        colors={Gradients.primaryCta}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 0 }}
        style={[styles.base, styles.primaryGradient, isDisabled && styles.disabled, style]}
      >
        <Pressable
          onPress={isDisabled ? undefined : onPress}
          style={({ pressed }) => [styles.pressable, pressed && !isDisabled && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel={label}
          disabled={isDisabled}
        >
          {loading ? (
            <ActivityIndicator size="small" color={Colors.textPrimary} />
          ) : (
            <>
              {icon}
              <Text style={styles.labelPrimary}>{label}</Text>
            </>
          )}
        </Pressable>
      </LinearGradient>
    );
  }

  const ghostBorderColor =
    variant === 'danger' ? Colors.feedbackError : Colors.border;
  const ghostTextColor =
    variant === 'danger' ? Colors.feedbackError : Colors.textSecondary;

  return (
    <Pressable
      onPress={isDisabled ? undefined : onPress}
      style={({ pressed }) => [
        styles.base,
        styles.ghost,
        { borderColor: ghostBorderColor },
        pressed && !isDisabled && styles.ghostPressed,
        isDisabled && styles.disabled,
        style,
      ]}
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={isDisabled}
    >
      {loading ? (
        <ActivityIndicator size="small" color={ghostTextColor} />
      ) : (
        <>
          {icon}
          <Text style={[styles.labelGhost, { color: ghostTextColor }]}>{label}</Text>
        </>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: Radii.md,
    overflow: 'hidden',
  },
  primaryGradient: {
    // shadow applied via Shadows.ctaGlow by callers when needed
  },
  pressable: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.xl,
  },
  pressed: {
    opacity: 0.82,
  },
  ghost: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.xl,
    borderWidth: 1,
    backgroundColor: 'transparent',
  },
  ghostPressed: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
  },
  disabled: {
    opacity: 0.45,
  },
  labelPrimary: {
    fontFamily: Typography.font.semiBold,
    fontSize: Typography.size.lg,
    color: Colors.textPrimary,
  },
  labelGhost: {
    fontFamily: Typography.font.medium,
    fontSize: Typography.size.md,
  },
});
