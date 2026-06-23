import React from 'react';
import { ActivityIndicator, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import { Colors } from '../../theme';

interface FomoLoadingStateProps {
  /** Override spinner color. Defaults to Colors.purple. */
  color?: string;
  style?: StyleProp<ViewStyle>;
}

/** Centered ActivityIndicator for full-screen or section loading states. */
export function FomoLoadingState({ color = Colors.purple, style }: FomoLoadingStateProps) {
  return (
    <View style={[styles.container, style]}>
      <ActivityIndicator color={color} size="large" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
