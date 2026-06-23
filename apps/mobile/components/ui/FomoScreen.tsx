import React from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import { Colors } from '../../theme';

interface FomoScreenProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}

/** Full-screen dark container. Use as the root View for every tab/screen. */
export function FomoScreen({ children, style }: FomoScreenProps) {
  return <View style={[styles.screen, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: Colors.background,
  },
});
