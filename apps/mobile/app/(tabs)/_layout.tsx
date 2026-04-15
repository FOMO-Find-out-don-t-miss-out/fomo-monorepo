import { Tabs } from 'expo-router';
import { Heart, Map, Search, User } from 'lucide-react-native';
import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

// ─── Route metadata ───────────────────────────────────────────────────────────

const ROUTE_META = {
  index:   { label: 'Discover', Icon: Map   },
  search:  { label: 'Search',   Icon: Search },
  saved:   { label: 'Saved',    Icon: Heart  },
  profile: { label: 'Profile',  Icon: User   },
} as const;

// ─── Custom Tab Bar ───────────────────────────────────────────────────────────
//
// Matches v0 bottom-nav-bar.tsx exactly:
//
//   <nav class="fixed bottom-0 left-0 right-0 px-4 pb-6 pt-2">     ← navWrapper
//     <div class="glassmorphism rounded-2xl overflow-hidden">        ← pill
//       <div class="flex justify-around px-2 py-2">                  ← row
//         <button class="flex flex-col items-center gap-1 px-4 py-2 rounded-lg">
//           {isActive && <div class="absolute inset-1 bg-purple-500/20 rounded-lg" />}
//           <Icon />
//           <span>{label}</span>
//         </button>
//       </div>
//     </div>
//   </nav>

function CustomTabBar({ state, navigation }: any) {
  const insets = useSafeAreaInsets();

  return (
    <View
      style={[
        styles.navWrapper,
        // pb-6 base + safe-area (home indicator on iPhone)
        { paddingBottom: Math.max(insets.bottom, 16) + 8 },
      ]}
    >
      {/* Glass pill — glassmorphism rounded-2xl overflow-hidden */}
      <View style={styles.pill}>
        {/* Row — justify-around px-2 py-2 */}
        <View style={styles.row}>
          {state.routes.map((route: any, index: number) => {
            const isFocused = state.index === index;
            const meta = ROUTE_META[route.name as keyof typeof ROUTE_META];
            if (!meta) return null;

            const { label, Icon } = meta;
            const color = isFocused ? '#A855F7' : 'rgba(255,255,255,0.45)';

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
                    navigation.navigate(route.name);
                  }
                }}
                style={styles.tabBtn}
              >
                {/* Active fill — "absolute inset-1 bg-purple-500/20 rounded-lg" */}
                {isFocused && <View style={styles.activeBg} />}

                {/* Icon — relative z-index so it sits above activeBg */}
                <Icon size={20} color={color} strokeWidth={1.5} style={styles.icon} />

                {/* Label */}
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
        // Prevent React Navigation from adding its own safe-area padding
        // to the tab content — our content handles its own positioning
        sceneStyle: { backgroundColor: 'transparent' },
      }}
    >
      <Tabs.Screen name="index"   options={{ title: 'Discover' }} />
      <Tabs.Screen name="search"  options={{ title: 'Search'   }} />
      <Tabs.Screen name="saved"   options={{ title: 'Saved'    }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile'  }} />
    </Tabs>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({

  // ── Outer positioning wrapper ──────────────────────────────────────────────
  // v0: "fixed bottom-0 left-0 right-0 z-50 px-4 pt-2"
  navWrapper: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    paddingHorizontal: 16,   // px-4
    paddingTop: 8,           // pt-2
    zIndex: 50,
  },

  // ── Glass pill ─────────────────────────────────────────────────────────────
  // v0: "glassmorphism rounded-2xl overflow-hidden"
  // glassmorphism = rgba(18,18,24,0.75) + border rgba(255,255,255,0.1)
  // (no backdrop-filter in RN — slightly more opaque to compensate)
  pill: {
    backgroundColor: 'rgba(18, 18, 24, 0.95)',
    borderRadius: 16,        // rounded-2xl
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.10)',
    overflow: 'hidden',
  },

  // ── Inner flex row ─────────────────────────────────────────────────────────
  // v0: "flex items-center justify-around px-2 py-2"
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingHorizontal: 8,    // px-2
    paddingVertical: 8,      // py-2
  },

  // ── Individual tab button ──────────────────────────────────────────────────
  // v0: "relative flex flex-col items-center gap-1 px-4 py-2 rounded-lg"
  tabBtn: {
    position: 'relative',
    alignItems: 'center',
    gap: 4,                  // gap-1
    paddingHorizontal: 16,   // px-4
    paddingVertical: 8,      // py-2
    borderRadius: 8,         // rounded-lg
    minWidth: 60,
  },

  // ── Active background fill ─────────────────────────────────────────────────
  // v0: "absolute inset-1 bg-purple-500/20 rounded-lg"
  activeBg: {
    position: 'absolute',
    top: 4,      // inset-1 = 4px
    left: 4,
    right: 4,
    bottom: 4,
    backgroundColor: 'rgba(168, 85, 247, 0.20)',  // bg-purple-500/20
    borderRadius: 8,
  },

  // ── Icon — needs zIndex to render above activeBg ───────────────────────────
  icon: {
    zIndex: 1,
  },

  // ── Label ──────────────────────────────────────────────────────────────────
  // v0: "text-[10px] font-medium relative z-10"
  tabLabel: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.1,
    zIndex: 1,
  },

});
