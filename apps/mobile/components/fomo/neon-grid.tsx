import React, { useEffect, useRef } from 'react';
import { Animated, Dimensions, StyleSheet, View } from 'react-native';

const { width: W, height: H } = Dimensions.get('window');

// ─── Design tokens ────────────────────────────────────────────────────────────

const L_DIM   = 'rgba(188, 19, 254, 0.06)';   // minor roads
const L_MID   = 'rgba(188, 19, 254, 0.10)';   // secondary roads
const L_BRIGHT = 'rgba(188, 19, 254, 0.16)';  // major roads

// ─── Static road network (fixed positions — no Math.random in render) ─────────

// Horizontal roads  { top, thickness, color, rotation (deg) }
const H_ROADS = [
  { top: 0.13, t: 1,   c: L_DIM,    r:  1.2 },
  { top: 0.22, t: 2,   c: L_BRIGHT, r: -0.8 },  // major
  { top: 0.31, t: 1,   c: L_DIM,    r:  0.5 },
  { top: 0.42, t: 1.5, c: L_MID,    r:  1.0 },
  { top: 0.50, t: 2,   c: L_BRIGHT, r: -1.5 },  // highway
  { top: 0.60, t: 1,   c: L_DIM,    r:  0.3 },
  { top: 0.69, t: 1.5, c: L_MID,    r:  0.8 },
  { top: 0.78, t: 2,   c: L_BRIGHT, r: -0.5 },  // major
  { top: 0.87, t: 1,   c: L_DIM,    r:  1.0 },
] as const;

// Vertical roads  { left, thickness, color, rotation (deg) }
const V_ROADS = [
  { left: 0.08, t: 1,   c: L_DIM,    r:  0.5 },
  { left: 0.17, t: 2,   c: L_BRIGHT, r: -1.0 },  // major
  { left: 0.28, t: 1,   c: L_DIM,    r:  0.8 },
  { left: 0.40, t: 1.5, c: L_MID,    r: -0.4 },
  { left: 0.52, t: 1,   c: L_DIM,    r:  0.6 },
  { left: 0.63, t: 1.5, c: L_MID,    r: -0.9 },
  { left: 0.75, t: 2,   c: L_BRIGHT, r:  1.2 },  // major
  { left: 0.87, t: 1,   c: L_DIM,    r: -0.3 },
] as const;

// ─── Event markers (from v0 markerPositions) ──────────────────────────────────

const MARKERS = [
  { x: 0.15, y: 0.25, color: '#A855F7', size: 10 },  // high-hype purple
  { x: 0.75, y: 0.20, color: '#A855F7', size: 12 },  // high-hype purple (dominant)
  { x: 0.35, y: 0.45, color: '#22D3EE', size:  8 },  // trending cyan
  { x: 0.60, y: 0.35, color: '#3B82F6', size:  8 },  // calm blue
  { x: 0.25, y: 0.60, color: '#A855F7', size: 10 },  // high-hype purple
  { x: 0.80, y: 0.55, color: '#A855F7', size:  9 },  // high-hype purple
] as const;

// ─── Sub-components ───────────────────────────────────────────────────────────

function Road({
  top, left, t, c, r, horizontal,
}: {
  top?: number; left?: number; t: number; c: string; r: number; horizontal: boolean;
}) {
  if (horizontal) {
    return (
      <View
        style={{
          position: 'absolute',
          height: t,
          width: W + 40,
          left: -20,
          top: H * (top ?? 0) - t / 2,
          backgroundColor: c,
          transform: [{ rotate: `${r}deg` }],
        }}
      />
    );
  }
  return (
    <View
      style={{
        position: 'absolute',
        width: t,
        height: H + 40,
        top: -20,
        left: W * (left ?? 0) - t / 2,
        backgroundColor: c,
        transform: [{ rotate: `${r}deg` }],
      }}
    />
  );
}

interface GlowDotProps {
  x: number;
  y: number;
  color: string;
  size: number;
  pulseAnim: Animated.Value;
}

function GlowDot({ x, y, color, size, pulseAnim }: GlowDotProps) {
  const cx = W * x;
  const cy = H * y;

  // Map pulseAnim (0 → 1) to each ring's visual opacity range.
  const outerOpacity = pulseAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.2, 0.7], // requested 0.2 to 0.7
  });
  const midOpacity = pulseAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.3, 0.5],
  });

  return (
    <>
      {/* Outermost halo — breathes with pulseAnim */}
      <Animated.View
        style={{
          position: 'absolute',
          width:  size * 6,
          height: size * 6,
          borderRadius: size * 3,
          backgroundColor: color,
          opacity: outerOpacity,
          left: cx - size * 3,
          top:  cy - size * 3,
        }}
      />
      {/* Mid halo — breathes with pulseAnim */}
      <Animated.View
        style={{
          position: 'absolute',
          width:  size * 3,
          height: size * 3,
          borderRadius: size * 1.5,
          backgroundColor: color,
          opacity: midOpacity,
          left: cx - size * 1.5,
          top:  cy - size * 1.5,
        }}
      />
      {/* Core — static, always bright */}
      <View
        style={{
          position: 'absolute',
          width:  size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: color,
          opacity: 0.95,
          left: cx - size / 2,
          top:  cy - size / 2,
          shadowColor: color,
          shadowOffset: { width: 0, height: 0 },
          shadowRadius: size * 2,
          shadowOpacity: 1,
          elevation: 8,
        }}
      />
    </>
  );
}

// ─── NeonGrid ─────────────────────────────────────────────────────────────────

export function NeonGrid() {
  // Single Animated.Value shared by all markers — they breathe in unison.
  const pulseAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.0,
          duration: 1000, // 1s up → 1s down = 2s cycle
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 0.0,
          duration: 1000,
          useNativeDriver: true,
        }),
      ]),
    );
    pulse.start();
    return () => pulse.stop();
  // pulseAnim ref is stable — run once on mount only
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">

      {/* Road network */}
      {H_ROADS.map((road, i) => (
        <Road key={`h${i}`} horizontal top={road.top} t={road.t} c={road.c} r={road.r} />
      ))}
      {V_ROADS.map((road, i) => (
        <Road key={`v${i}`} horizontal={false} left={road.left} t={road.t} c={road.c} r={road.r} />
      ))}

      {/* Glow markers — each receives the shared pulseAnim */}
      {MARKERS.map((m, i) => (
        <GlowDot key={`m${i}`} {...m} pulseAnim={pulseAnim} />
      ))}

      {/* Bottom-to-top fade vignette — 4-step simulated gradient */}
      <View style={styles.vignette} pointerEvents="none">
        <View style={{ flex: 1, backgroundColor: 'rgba(11, 11, 15, 0.05)' }} />
        <View style={{ flex: 1, backgroundColor: 'rgba(11, 11, 15, 0.18)' }} />
        <View style={{ flex: 1, backgroundColor: 'rgba(11, 11, 15, 0.38)' }} />
        <View style={{ flex: 1, backgroundColor: 'rgba(11, 11, 15, 0.62)' }} />
      </View>

    </View>
  );
}

const styles = StyleSheet.create({
  vignette: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: H * 0.38,
  },
});
