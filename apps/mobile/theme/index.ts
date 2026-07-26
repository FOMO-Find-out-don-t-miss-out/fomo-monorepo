/**
 * FOMO Mobile Design System — canonical design tokens.
 *
 * Rules:
 *   - Every feature component imports from here; no bare hex literals in UI code.
 *   - Do not add tokens without a real use-case; prefer semantic names over raw values.
 *   - Category swatches are keyed by UiEventCategory — add new categories here too.
 */

// ── Colour palette ────────────────────────────────────────────────────────────

export const Colors = {
  // ── Surfaces ────────────────────────────────────────────────────────────────
  background:   '#0B0B0F',
  surface:      'rgba(12, 12, 18, 0.95)',
  surfaceGlass: 'rgba(18, 18, 24, 0.75)',
  surfaceCard:  'rgba(12, 12, 18, 0.85)',
  surfaceRaised:      'rgba(18, 18, 26, 0.95)',
  surfaceGlassStrong: 'rgba(12, 12, 18, 0.88)',
  topHighlight:       'rgba(255, 255, 255, 0.06)',

  // ── Borders ─────────────────────────────────────────────────────────────────
  border:       'rgba(255, 255, 255, 0.12)',
  borderGlass:  'rgba(255, 255, 255, 0.10)',
  borderSubtle: 'rgba(255, 255, 255, 0.08)',
  borderFocus:  'rgba(188, 19, 254, 0.40)',

  // ── Primary accent — purple ──────────────────────────────────────────────────
  purple:       '#A855F7',
  purpleNeon:   '#BC13FE',
  purpleDim:    'rgba(168, 85, 247, 0.20)',
  purpleGlow:   'rgba(168, 85, 247, 0.45)',
  neonPurpleGlow: 'rgba(188, 19, 254, 0.45)',

  // ── Neon green secondary accent ─────────────────────────────────────────────
  neonGreen:      '#39FF88',
  neonGreenDim:   'rgba(57, 255, 136, 0.20)',
  neonGreenGlow:  'rgba(57, 255, 136, 0.45)',

  // ── Secondary accents (category-only — never global) ─────────────────────────
  cyan:         '#22D3EE',
  magenta:      '#EC4899',

  // ── Text ────────────────────────────────────────────────────────────────────
  textPrimary:   '#FFFFFF',
  textSecondary: 'rgba(255, 255, 255, 0.60)',
  textMuted:     'rgba(255, 255, 255, 0.35)',
  textDisabled:  'rgba(255, 255, 255, 0.20)',

  // ── Semantic ─────────────────────────────────────────────────────────────────
  error:   '#F87171',
  success: '#4ADE80',
  warning: '#FBBF24',

  // ── Canonical semantic accent tokens ─────────────────────────────────────────
  brandPrimary:     '#BC13FE',   // neon purple — logo, primary CTA
  brandSecondary:   '#39FF88',   // neon green — secondary brand identity
  intentInterested: '#BC13FE',   // Interested = neon purple (all surfaces)
  intentGoing:      '#39FF88',   // Going = neon green (all surfaces)
  navigationActive: '#BC13FE',   // active tab = neon purple
  navigationInactive: 'rgba(255, 255, 255, 0.45)', // inactive tab icon/label
  eventSelected:    '#BC13FE',   // selected event border/glow = neon purple
  userLocation:     '#39FF88',   // user location dot = neon green
  eventLive:        '#39FF88',   // live/available state = neon green
  feedbackSuccess:  '#39FF88',   // success feedback = neon green
  feedbackWarning:  '#FBBF24',   // warning feedback = amber
  feedbackError:    '#F87171',   // error feedback = red

  // ── Category swatches (keyed by UiEventCategory — Discover 6-bucket) ────────
  category: {
    Music:    { border: 'rgba(168, 85,  247, 0.5)', text: '#A855F7', bg: 'rgba(168, 85,  247, 0.10)' },
    Arts:     { border: 'rgba(236, 72,  153, 0.5)', text: '#EC4899', bg: 'rgba(236, 72,  153, 0.10)' },
    Theater:  { border: 'rgba(245, 158, 11,  0.5)', text: '#F59E0B', bg: 'rgba(245, 158, 11,  0.10)' },
    Sports:   { border: 'rgba(34,  197, 94,  0.5)', text: '#22C55E', bg: 'rgba(34,  197, 94,  0.10)' },
    Comedy:   { border: 'rgba(249, 115, 22,  0.5)', text: '#F97316', bg: 'rgba(249, 115, 22,  0.10)' },
    Festival: { border: 'rgba(34,  211, 238, 0.5)', text: '#22D3EE', bg: 'rgba(34,  211, 238, 0.10)' },
  },

  // ── Explore category tokens (keyed by backend EventCategory — 9 entries) ────
  // Scoped to Explore result rows; does not affect Discover's 6-bucket system.
  exploreCategory: {
    Music:      { border: 'rgba(168, 85,  247, 0.40)', text: '#C084FC', bg: 'rgba(168, 85,  247, 0.15)' },
    Art:        { border: 'rgba(236, 72,  153, 0.40)', text: '#F472B6', bg: 'rgba(236, 72,  153, 0.15)' },
    Tech:       { border: 'rgba(34,  211, 238, 0.40)', text: '#22D3EE', bg: 'rgba(34,  211, 238, 0.15)' },
    Food:       { border: 'rgba(251, 191, 36,  0.40)', text: '#FBBF24', bg: 'rgba(251, 191, 36,  0.15)' },
    Nightlife:  { border: 'rgba(236, 72,  153, 0.40)', text: '#F472B6', bg: 'rgba(236, 72,  153, 0.15)' },
    Sports:     { border: 'rgba(57,  255, 136, 0.40)', text: '#39FF88', bg: 'rgba(57,  255, 136, 0.15)' },
    Business:   { border: 'rgba(249, 115, 22,  0.40)', text: '#FB923C', bg: 'rgba(249, 115, 22,  0.15)' },
    Community:  { border: 'rgba(168, 85,  247, 0.40)', text: '#C084FC', bg: 'rgba(168, 85,  247, 0.15)' },
    Other:      { border: 'rgba(156, 163, 175, 0.40)', text: '#9CA3AF', bg: 'rgba(156, 163, 175, 0.12)' },
  } as Record<string, { border: string; text: string; bg: string }>,
};

// ── Gradients ─────────────────────────────────────────────────────────────────

export const Gradients = {
  /** Primary CTA: neon purple → grape. Used on action buttons and CTAs. */
  primaryCta: ['#BC13FE', '#9333EA'] as [string, string],
  /** Soft purple fill for active states, overlays. */
  purpleSubtle: ['rgba(188, 19, 254, 0.3)', 'rgba(147, 51, 234, 0.1)'] as [string, string],
  /** Soft green fill for active states, overlays. */
  greenSubtle: ['rgba(57, 255, 136, 0.3)', 'rgba(34, 197, 94, 0.1)'] as [string, string],
};

// ── Typography ────────────────────────────────────────────────────────────────

export const Typography = {
  font: {
    regular:   'Inter_400Regular',
    medium:    'Inter_500Medium',
    semiBold:  'Inter_600SemiBold',
    bold:      'Inter_700Bold',
    extraBold: 'Inter_800ExtraBold',
  },
  size: {
    xs:   9,
    sm:   11,
    base: 13,
    md:   14,
    lg:   15,
    xl:   18,
    '2xl': 20,
    '3xl': 22,
    '4xl': 28,
    hero: 36,
  },
};

// ── Spacing ───────────────────────────────────────────────────────────────────

export const Spacing = {
  xs:   4,
  sm:   8,
  md:   12,
  base: 16,
  lg:   20,
  xl:   24,
  '2xl': 32,
};

// ── Border radii ──────────────────────────────────────────────────────────────

export const Radii = {
  sm:   8,
  md:   12,
  lg:   14,
  xl:   16,
  '2xl': 20,
  full: 9999,
};

// ── Shadows / glow ────────────────────────────────────────────────────────────

export const Shadows = {
  /** Purple glow on active event cards. */
  cardActive: {
    shadowColor: '#A855F7',
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 16,
    shadowOpacity: 0.45,
    elevation: 12,
  },
  /** Neon CTA button glow. */
  ctaGlow: {
    shadowColor: '#BC13FE',
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 15,
    shadowOpacity: 0.50,
    elevation: 8,
  },
  /** Green glow for Going confirmation, live indicators. */
  greenGlow: {
    shadowColor: '#39FF88',
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 15,
    shadowOpacity: 0.45,
    elevation: 8,
  },
};
