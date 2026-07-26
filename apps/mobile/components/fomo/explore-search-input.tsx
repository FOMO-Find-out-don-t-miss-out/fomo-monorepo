import { Search as SearchIcon, X } from 'lucide-react-native';
import React, { useState } from 'react';
import { Pressable, StyleSheet, TextInput, View } from 'react-native';
import { Colors, Radii, Spacing } from '../../theme';

interface ExploreSearchInputProps {
  value: string;
  onChangeText: (text: string) => void;
  onClear: () => void;
}

/**
 * Screen-embedded Explore search field. Deliberately not the Discover
 * SearchBar: no floating/absolute layout, no BlurView, no filter/calendar/
 * bell controls — just a plain, focus-aware text input matching the design
 * system's semantic tokens.
 */
export function ExploreSearchInput({ value, onChangeText, onClear }: ExploreSearchInputProps) {
  const [focused, setFocused] = useState(false);

  return (
    <View
      style={[
        styles.container,
        { borderColor: focused ? Colors.borderFocus : Colors.borderGlass },
      ]}
    >
      <SearchIcon size={18} color={Colors.textSecondary} strokeWidth={2} />
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder="Search events by name, venue, or organizer"
        placeholderTextColor={Colors.textMuted}
        returnKeyType="search"
        autoCorrect={false}
        autoCapitalize="none"
      />
      {value.length > 0 && (
        <Pressable
          onPress={onClear}
          hitSlop={8}
          accessibilityRole="button"
          accessibilityLabel="Clear search"
        >
          <X size={16} color={Colors.textSecondary} strokeWidth={2} />
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    height: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    paddingHorizontal: Spacing.md,
    borderRadius: Radii.lg,
    borderWidth: 1,
    backgroundColor: Colors.surfaceGlass,
  },
  input: {
    flex: 1,
    fontSize: 15,
    color: Colors.textPrimary,
    padding: 0,
    margin: 0,
    textAlignVertical: 'center',
  },
});
