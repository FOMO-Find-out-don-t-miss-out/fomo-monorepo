import { BlurView } from 'expo-blur';
import { Tabs } from 'expo-router';
import { Heart, Map, Search, User } from 'lucide-react-native';
import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors } from '../../theme';
import { perfLog, perfMark } from '../../utils/performance-debug';

// ─── Route metadata ───────────────────────────────────────────────────────────

const ROUTE_META = {
  index:   { label: 'Discover', Icon: Map    },
  search:  { label: 'Search',   Icon: Search },
  saved:   { label: 'My Events', Icon: Heart  },
  profile: { label: 'Profile',  Icon: User   },
} as const;

// ─── Custom Tab Bar ───────────────────────────────────────────────────────────
//
// Matches v0 bottom-nav-bar.tsx structure exactly:
//
//   nav  [position:fixed, bottom:0, left:0, right:0, px:16, pb:24]   ← navWrapper
//     ╰── glassmorphism pill  [BlurView, rounded-2xl, border]         ← pill
//           ╰── row  [justify-around, px:8, py:8]                     ← row
//                 ╰── button  [flex-col, items-center, px:16, py:8]   ← tabBtn
//                       ├── active bg  [abs inset:4, purple-500/20]   ← activeBg
//                       ├── Icon       [size 24 active / 22 inactive]
//                       ╰── label      [Inter_600SemiBold, 10px]

function CustomTabBar({ state, navigation }: any) {
  const insets = useSafeAreaInsets();

  return (
    <View
      style={[
        styles.navWrapper,
        { paddingBottom: Math.max(insets.bottom, 16) + 8 },
      ]}
    >
      {/*
        Blur technique:
          Outer View owns borderRadius + overflow:hidden  →  clips the blur
          BlurView fills the outer View absolutely        →  frosted glass bg
          Row renders on top of the blur layer            →  content
      */}
      <View style={styles.pill}>
        <BlurView intensity={20} tint="dark" style={StyleSheet.absoluteFill} />

        <View style={styles.row}>
          {state.routes.map((route: any, index: number) => {
            const isFocused = state.index === index;
            const meta = ROUTE_META[route.name as keyof typeof ROUTE_META];
            if (!meta) return null;

            const { label, Icon } = meta;
            const color = isFocused ? Colors.navigationActive : Colors.navigationInactive;

            return (
              <Pressable
                key={route.key}
                onPress={() => {
                  const event = navigation.emit({
                    type: 'tabPress',
                    target: route.key,
                    canPreventDefault: true,
                  });
                  if (!isFocused && !event.defaultPrevented) {
                    // Correlate with the destination screen's `screen-focus` log
                    // to measure tab-press → focus latency.
                    perfLog('nav-tap', { to: route.name, t: Math.round(perfMark()) });
                    navigation.navigate(route.name);
                  }
                }}
                style={styles.tabBtn}
              >
                {/* Active bg — v0: "absolute inset-1 bg-purple-500/20 rounded-lg" */}
                {isFocused && <View style={styles.activeBg} />}

                {/* Icon — larger when active to match v0 emphasis */}
                <Icon
                  size={isFocused ? 24 : 22}
                  color={color}
                  strokeWidth={1.5}
                  style={styles.icon}
                />

                {/* Label — Inter_600SemiBold 10px */}
                <Text
                  style={[styles.tabLabel, { color }]}
                  numberOfLines={1}
                  allowFontScaling={false}
                >
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>
    </View>
  );
}

// ─── Layout ───────────────────────────────────────────────────────────────────

export default function TabsLayout() {
  return (
    <Tabs
      tabBar={(props) => <CustomTabBar {...props} />}
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: 'transparent' },
      }}
    >
      <Tabs.Screen name="index"   options={{ title: 'Discover' }} />
      <Tabs.Screen name="search"  options={{ title: 'Search'   }} />
      <Tabs.Screen name="saved"   options={{ title: 'My Events' }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile'  }} />
    </Tabs>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({

  // ── Outer wrapper ─────────────────────────────────────────────────────────
  // v0: "fixed bottom-0 left-0 right:0 z-50 px-4 pt-2"
  navWrapper: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    paddingHorizontal: 16,
    paddingTop: 8,
    zIndex: 50,
  },

  // ── Glass pill ─────────────────────────────────────────────────────────────
  // v0: "glassmorphism rounded-2xl overflow-hidden"
  // overflow:hidden clips the BlurView to the borderRadius shape
  pill: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colors.border,
    overflow: 'hidden',
    // Fallback background for platforms where BlurView renders transparent
    backgroundColor: Colors.surfaceGlassStrong,
  },

  // ── Row inside pill ────────────────────────────────────────────────────────
  // v0: "flex items-center justify-around px-2 py-2"
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingHorizontal: 8,
    paddingVertical: 8,
  },

  // ── Per-tab button ─────────────────────────────────────────────────────────
  // v0: "relative flex flex-col items-center gap-1 px-4 py-2 rounded-lg"
  tabBtn: {
    position: 'relative',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    minWidth: 60,
  },

  // ── Active fill ────────────────────────────────────────────────────────────
  // v0: "absolute inset-1 bg-purple-500/20 rounded-lg"
  activeBg: {
    position: 'absolute',
    top: 4,
    left: 4,
    right: 4,
    bottom: 4,
    backgroundColor: Colors.purpleDim,
    borderRadius: 8,
  },

  // ── Icon — rendered above activeBg via zIndex ──────────────────────────────
  icon: {
    zIndex: 1,
  },

  // ── Label — Inter_600SemiBold, v0: "text-[10px] font-medium z-10" ─────────
  tabLabel: {
    fontFamily: 'Inter_600SemiBold',
    fontSize: 10,
    letterSpacing: 0.1,
    zIndex: 1,
  },

});
