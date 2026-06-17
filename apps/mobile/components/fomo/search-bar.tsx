import {
  Bell,
  CalendarDays,
  Laugh,
  Map,
  Music,
  Palette,
  Search,
  SlidersHorizontal,
  Sparkles,
  Theater,
  Trophy,
  X,
} from 'lucide-react-native';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Animated,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

// ─── Design tokens ────────────────────────────────────────────────────────────

const NEON_PURPLE = '#BC13FE';
const NEON_CYAN = '#22D3EE';
const GLASS_BG = 'rgba(18, 18, 24, 0.75)';
const GLASS_BORDER = 'rgba(255, 255, 255, 0.1)';
const FOCUS_BORDER = 'rgba(188, 19, 254, 0.4)';
const FILTER_PANEL_MAX_HEIGHT = 160;

// ─── Category config ──────────────────────────────────────────────────────────

const CATEGORIES = [
  { id: 'music',    label: 'Music',    Icon: Music,    color: '#A855F7' },
  { id: 'arts',     label: 'Arts',     Icon: Palette,  color: '#EC4899' },
  { id: 'theater',  label: 'Theater',  Icon: Theater,  color: '#F59E0B' },
  { id: 'sports',   label: 'Sports',   Icon: Trophy,   color: '#22C55E' },
  { id: 'comedy',   label: 'Comedy',   Icon: Laugh,    color: '#F97316' },
  { id: 'festival', label: 'Festival', Icon: Sparkles, color: '#06B6D4' },
] as const;

// ─── Animated Pressable ───────────────────────────────────────────────────────

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

// ─── Sub-components ───────────────────────────────────────────────────────────

function FOMOLogo() {
  return <Text style={styles.logo}>FOMO</Text>;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function springPress(value: Animated.Value, toValue: number) {
  Animated.spring(value, {
    toValue,
    speed: 50,
    bounciness: 4,
    useNativeDriver: true,  // scale/transform only → native driver safe
  }).start();
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface SearchBarProps {
  onFilterChange?: (filters: string[]) => void;
  onSearchChange?: (text: string) => void;
  isCalendarView?: boolean;
  onViewToggle?: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function SearchBar({
  onFilterChange,
  onSearchChange,
  isCalendarView,
  onViewToggle,
}: SearchBarProps) {
  const insets = useSafeAreaInsets();
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [selectedFilters, setSelectedFilters] = useState<string[]>([]);

  // ── Animated values ────────────────────────────────────────────────────────
  // Mount — opacity + slide (useNativeDriver: true, transform/opacity only)
  const mountOpacity   = useRef(new Animated.Value(0)).current;
  const mountTranslateY = useRef(new Animated.Value(-16)).current;

  // Focus border — color interpolation (useNativeDriver: false, color prop)
  const focusProgress = useRef(new Animated.Value(0)).current;

  // Filter panel — maxHeight + opacity (useNativeDriver: false, layout prop)
  const panelMaxHeight = useRef(new Animated.Value(0)).current;
  const panelOpacity   = useRef(new Animated.Value(0)).current;

  // Button press scale (useNativeDriver: true, transform only)
  const filterScale = useRef(new Animated.Value(1)).current;
  const calScale    = useRef(new Animated.Value(1)).current;
  const bellScale   = useRef(new Animated.Value(1)).current;

  // ── Entry animation on mount ───────────────────────────────────────────────
  useEffect(() => {
    Animated.parallel([
      Animated.timing(mountOpacity, {
        toValue: 1,
        duration: 350,
        useNativeDriver: true,
      }),
      Animated.spring(mountTranslateY, {
        toValue: 0,
        tension: 80,
        friction: 12,
        useNativeDriver: true,
      }),
    ]).start();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Derived animated styles ────────────────────────────────────────────────
  const animatedBorderColor = focusProgress.interpolate({
    inputRange: [0, 1],
    outputRange: [GLASS_BORDER, FOCUS_BORDER],
  });

  // ── Handlers ───────────────────────────────────────────────────────────────
  const handleFocus = useCallback(() => {
    Animated.timing(focusProgress, {
      toValue: 1,
      duration: 200,
      useNativeDriver: false,
    }).start();
  }, [focusProgress]);

  const handleBlur = useCallback(() => {
    Animated.timing(focusProgress, {
      toValue: 0,
      duration: 200,
      useNativeDriver: false,
    }).start();
  }, [focusProgress]);

  const handleToggleFilter = useCallback(() => {
    const opening = !isFilterOpen;
    setIsFilterOpen(opening);
    Animated.parallel([
      Animated.timing(panelMaxHeight, {
        toValue: opening ? FILTER_PANEL_MAX_HEIGHT : 0,
        duration: 300,
        useNativeDriver: false,
      }),
      Animated.timing(panelOpacity, {
        toValue: opening ? 1 : 0,
        duration: 250,
        useNativeDriver: false,
      }),
    ]).start();
  }, [isFilterOpen, panelMaxHeight, panelOpacity]);

  const handleToggleCategory = useCallback(
    (id: string) => {
      setSelectedFilters((prev) => {
        const next = prev.includes(id)
          ? prev.filter((f) => f !== id)
          : [...prev, id];
        onFilterChange?.(next);
        return next;
      });
    },
    [onFilterChange],
  );

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <Animated.View
      style={[
        styles.container,
        // Safe-area-aware top padding: clears status bar + notch on all devices
        { paddingTop: insets.top + 8 },
        { opacity: mountOpacity, transform: [{ translateY: mountTranslateY }] },
      ]}
    >

      {/* ── Top row ──────────────────────────────────────────────────────── */}
      <View style={styles.row}>

        {/* Search input — animated border color */}
        <Animated.View style={[styles.inputContainer, { borderColor: animatedBorderColor }]}>
          <FOMOLogo />
          <View style={styles.divider} />
          <Search size={20} color="rgba(255,255,255,0.5)" strokeWidth={2} />
          <TextInput
            style={styles.input}
            placeholder="Search events..."
            placeholderTextColor="rgba(255,255,255,0.4)"
            onFocus={handleFocus}
            onBlur={handleBlur}
            onChangeText={onSearchChange}
            returnKeyType="search"
            autoCorrect={false}
          />
        </Animated.View>

        {/* Filter toggle — scale on press */}
        <AnimatedPressable
          onPress={handleToggleFilter}
          onPressIn={() => springPress(filterScale, 0.88)}
          onPressOut={() => springPress(filterScale, 1)}
          style={[
            styles.iconBtn,
            isFilterOpen && styles.iconBtnActive,
            { transform: [{ scale: filterScale }] },
          ]}
        >
          {isFilterOpen
            ? <X size={20} color={NEON_PURPLE} strokeWidth={2} />
            : <SlidersHorizontal size={20} color="rgba(255,255,255,0.7)" strokeWidth={2} />}
          {selectedFilters.length > 0 && !isFilterOpen && (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{selectedFilters.length}</Text>
            </View>
          )}
        </AnimatedPressable>

        {/* Calendar / Map toggle */}
        <AnimatedPressable
          onPress={onViewToggle}
          onPressIn={() => springPress(calScale, 0.88)}
          onPressOut={() => springPress(calScale, 1)}
          style={[
            styles.iconBtn,
            isCalendarView && styles.calBtnActive,
            { transform: [{ scale: calScale }] },
          ]}
        >
          {isCalendarView
            ? <Map size={20} color={NEON_CYAN} strokeWidth={2} />
            : <CalendarDays size={20} color="rgba(255,255,255,0.7)" strokeWidth={2} />}
        </AnimatedPressable>

        {/* Bell */}
        <AnimatedPressable
          onPressIn={() => springPress(bellScale, 0.88)}
          onPressOut={() => springPress(bellScale, 1)}
          style={[styles.iconBtn, { transform: [{ scale: bellScale }] }]}
        >
          <Bell size={20} color="rgba(255,255,255,0.7)" strokeWidth={2} />
          <View style={styles.bellDot} />
        </AnimatedPressable>

      </View>

      {/* ── Filter panel ─────────────────────────────────────────────────── */}
      <Animated.View style={[styles.filterPanel, { maxHeight: panelMaxHeight, opacity: panelOpacity }]}>
        <View style={styles.filterPanelInner}>
          <Text style={styles.categoryLabel}>CATEGORIES</Text>
          <View style={styles.categoryRow}>
            {CATEGORIES.map(({ id, label, Icon, color }) => {
              const active = selectedFilters.includes(id);
              return (
                <Pressable
                  key={id}
                  onPress={() => handleToggleCategory(id)}
                  style={[
                    styles.chip,
                    active ? { backgroundColor: color } : styles.chipInactive,
                  ]}
                >
                  <Icon size={12} color={active ? '#fff' : 'rgba(255,255,255,0.6)'} />
                  <Text style={[styles.chipLabel, !active && styles.chipLabelDim]}>
                    {label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>
      </Animated.View>

    </Animated.View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 30,
    paddingHorizontal: 24,
    // paddingTop is set dynamically from useSafeAreaInsets (insets.top + 8)
    paddingBottom: 8,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  // ── Search input ──────────────────────────────────────────────────────────
  inputContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 12, // Increased from 10 to reach ~56px
    backgroundColor: GLASS_BG,
    borderWidth: 1,
    borderRadius: 14, // Slightly more rounded for premium look
    // borderColor animated via Animated.Value — do not set here
  },
  logo: {
    fontSize: 13,
    fontWeight: '900',
    color: '#C084FC', // Exact purple-400 from v0
    letterSpacing: -0.5, // tighter tracking like v0
    textShadowColor: 'rgba(192, 132, 252, 0.5)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 8,
  },
  divider: {
    width: 1,
    height: 20,
    backgroundColor: 'rgba(255,255,255,0.1)',
  },
  input: {
    flex: 1,
    fontSize: 13,
    color: '#fff',
    padding: 0,
    margin: 0,
  },
  // ── Icon buttons ──────────────────────────────────────────────────────────
  iconBtn: {
    padding: 10,
    backgroundColor: GLASS_BG,
    borderWidth: 1,
    borderColor: GLASS_BORDER,
    borderRadius: 12,
  },
  iconBtnActive: {
    borderColor: 'rgba(188, 19, 254, 0.4)',
  },
  calBtnActive: {
    borderColor: 'rgba(34, 211, 238, 0.6)',
    backgroundColor: 'rgba(34, 211, 238, 0.15)',
  },
  // ── Filter count badge ────────────────────────────────────────────────────
  badge: {
    position: 'absolute',
    top: -5,
    right: -5,
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: NEON_PURPLE,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: {
    fontSize: 9,
    fontWeight: '700',
    color: '#fff',
  },
  // ── Bell indicator dot ────────────────────────────────────────────────────
  bellDot: {
    position: 'absolute',
    top: 7,
    right: 7,
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: NEON_PURPLE,
  },
  // ── Filter panel ──────────────────────────────────────────────────────────
  filterPanel: {
    overflow: 'hidden',
    marginTop: 8,
  },
  filterPanelInner: {
    backgroundColor: GLASS_BG,
    borderWidth: 1,
    borderColor: GLASS_BORDER,
    borderRadius: 12,
    padding: 12,
  },
  categoryLabel: {
    fontSize: 10,
    color: 'rgba(255,255,255,0.5)',
    letterSpacing: 1.5,
    fontWeight: '600',
    marginBottom: 8,
  },
  categoryRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
  },
  chipInactive: {
    backgroundColor: 'rgba(255,255,255,0.06)',
  },
  chipLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: '#fff',
  },
  chipLabelDim: {
    color: 'rgba(255,255,255,0.6)',
  },
});
