import React from 'react';
import { Pressable, StyleSheet, type ViewStyle } from 'react-native';
import { Colors, Radii, Spacing } from '../../theme';

interface FomoIconButtonProps {
  icon: React.ReactNode;
  onPress?: () => void;
  /** Highlight the button border — use for toggle-on state. */
  active?: boolean;
  /** Border/background tint when active. Defaults to Colors.purple. */
  activeColor?: string;
  disabled?: boolean;
  /** Override size: 'sm' | 'md' (default). */
  size?: 'sm' | 'md';
  style?: ViewStyle;
  accessibilityLabel?: string;
}

/**
 * Glass-style icon button.
 * Used for action rows (share, directions) and toggle actions (save, interested, going).
 */
export function FomoIconButton({
  icon,
  onPress,
  active = false,
  activeColor = Colors.purple,
  disabled = false,
  size = 'md',
  style,
  accessibilityLabel,
}: FomoIconButtonProps) {
  const activeBorder = active
    ? `${activeColor}66`   // 40% opacity of the accent
    : Colors.borderGlass;
  const activeBg = active
    ? `${activeColor}1A`   // 10% opacity fill
    : 'transparent';

  return (
    <Pressable
      onPress={disabled ? undefined : onPress}
      style={({ pressed }) => [
        styles.base,
        size === 'sm' ? styles.sm : styles.md,
        { borderColor: activeBorder, backgroundColor: activeBg },
        pressed && !disabled && styles.pressed,
        disabled && styles.disabled,
        style,
      ]}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      disabled={disabled}
    >
      {icon}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: Radii.md,
    backgroundColor: Colors.surfaceGlass,
  },
  md: {
    padding: Spacing.md,
  },
  sm: {
    padding: Spacing.sm,
    borderRadius: Radii.sm,
  },
  pressed: {
    opacity: 0.75,
  },
  disabled: {
    opacity: 0.35,
  },
});
