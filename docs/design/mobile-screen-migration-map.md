# FOMO Mobile — Screen Migration Map

> **Step-by-step plan for migrating all mobile screens to the canonical design system.**
> Each row identifies exactly which file(s) to change, what to change, and the expected impact.
>
> **This migration covers visual styling and reusable primitives only.**
> - ✅ Colour tokens, hex→token migration, blur placement, repeated-item styling
> - ❌ No backend changes, new APIs, new features, mock data, relationship changes, auth changes, or navigation changes
> - ❌ API-backed screens (Discover, My Events, Profile) remain API-backed — never replace with mock/prototype/hard-coded implementations

---

## Phase 0 — Foundation (no visual change)

### 0.1 Add neon-green colour tokens to theme

| Detail | Value |
|--------|-------|
| **File** | `apps/mobile/theme/index.ts` |
| **Changes** | Add to `Colors`: `neonGreen: '#39FF88'`, `neonGreenDim: 'rgba(57, 255, 136, 0.20)'`, `neonGreenGlow: 'rgba(57, 255, 136, 0.45)'` |
| **Impact** | Zero visual change — new tokens only, no imports updated yet |
| **Risk** | None |

---

## Phase 1 — Intent system colour migration (Visual P0)

These changes MUST be applied as a single atomic unit — they fix the "Interested = purple, Going = green" invariant across all surfaces. Partial application would leave mismatched colours visible.

### 1.1 My Events tab bar (`apps/mobile/app/(tabs)/saved.tsx`)

| Change | Current | Target |
|--------|---------|--------|
| `TAB_COLOR.Interested` | `Colors.magenta` | `Colors.purple` |
| `TAB_COLOR.Going` | `Colors.success` | `Colors.neonGreen` |
| `TAB_EMPTY_ICON.Interested` | `<Heart color={Colors.magenta}>` | `<Heart color={Colors.purple}>` |

**Lines:**
- Line 46: `Interested: Colors.magenta` → `Interested: Colors.purple`
- Line 47: `Going: Colors.success` → `Going: Colors.neonGreen`
- Line 62: `color={Colors.magenta}` → `color={Colors.purple}`

### 1.2 IntentSelector (`apps/mobile/components/fomo/IntentSelector.tsx`)

| Change | Current | Target |
|--------|---------|--------|
| Interested button colour | `Colors.magenta` | `Colors.purple` |
| Going button colour | `Colors.cyan` | `Colors.neonGreen` |

**Line:**
- Line 18: `color: Colors.magenta` → `color: Colors.purple`
- Line 19: `color: Colors.cyan` → `color: Colors.neonGreen`

### 1.3 MyEventListItem (`apps/mobile/components/fomo/my-events/MyEventListItem.tsx`)

| Change | Current | Target |
|--------|---------|--------|
| Intent dot (interested) | `Colors.magenta` | `Colors.purple` |
| Intent dot (going) | `Colors.success` | `Colors.neonGreen` |

**Line:**
- Line 12: `interested: Colors.magenta` → `interested: Colors.purple`
- Line 13: `going: Colors.success` → `going: Colors.neonGreen`

### 1.4 Verify after Phase 1

**Manual check:**
1. Open My Events → Interested tab → tab border/label/icon are purple, not magenta
2. Open My Events → Going tab → tab border/label/icon are neon green, not standard green
3. Select an event → IntentSelector → both buttons show correct colours
4. Going dot in My Events rows → neon green, not cyan or success green

---

## Phase 2 — Cyan purge from semantic contexts (Visual P1)

### 2.1 EventCard date/time (`apps/mobile/components/fomo/event-card.tsx`)

| Change | Current | Target |
|--------|---------|--------|
| Date row colour | `#22D3EE` (hardcoded) | `Colors.textSecondary` |

**Lines:**
- Line 155: `color="#22D3EE"` on Calendar icon → keep (icon inherits from text)
- Line 156: `color="#22D3EE"` → `color={Colors.textSecondary}`
- Line 159: dateText uses `#22D3EE` in styles → change to `Colors.textSecondary` (all dates/times are neutral metadata)

### 2.2 EventCard price (`apps/mobile/components/fomo/event-card.tsx`)

| Change | Current | Target |
|--------|---------|--------|
| Price colour | `#22D3EE` | `Colors.textSecondary` or remove (no real data) |

**Line:**
- Line 226: `color: '#22D3EE'` → `color: Colors.textSecondary`

### 2.3 EventDetails date/time pills (`apps/mobile/components/fomo/event-details.tsx`)

| Change | Current | Target |
|--------|---------|--------|
| Pill icon colour | `#22D3EE` | `Colors.textSecondary` |
| Pill text colour | `#22D3EE` | `Colors.textSecondary` |

**Lines:**
- Line 236: `color="#22D3EE"` → `color={Colors.textSecondary}`
- Line 240: `color="#22D3EE"` → `color={Colors.textSecondary}`
- Line 416: `color: '#22D3EE'` → `color: Colors.textSecondary`

---

## Phase 3 — Hardcoded hex migration to theme tokens (Visual P1/P2)

### 3.1 Inline rgba values in event-card.tsx

| Current | Target |
|---------|--------|
| `rgba(255,255,255,0.5)` | `Colors.textSecondary` |
| `rgba(255,255,255,0.35)` | `Colors.textMuted` |
| `rgba(188, 19, 254, 0.3)` | `Colors.borderFocus` or `Colors.purpleDim` |
| `rgba(18, 18, 24, 0.85)` | `Colors.surfaceCard` |

### 3.2 Inline rgba values in event-details.tsx

| Current | Target |
|---------|--------|
| `rgba(255, 255, 255, 0.6)` | `Colors.textSecondary` |
| `rgba(255, 255, 255, 0.4)` | `Colors.textMuted` |
| `rgba(0, 0, 0, 0.6)` (backdrop) | Keep (not a surface token) |

### 3.3 Inline rgba in saved.tsx

| Current | Target |
|---------|--------|
| `rgba(255,255,255,0.4)` (infoLabel) | `Colors.textMuted` |
| `rgba(255,255,255,0.85)` (infoValue) | `Colors.textSecondary` |

### 3C — Calendar and date-control semantic migration ✅ (Phase 3C complete)

**calendar-view.tsx** — 10 hardcoded values migrated:
- Clock icon: `rgba(34,211,238,0.7)` → `Colors.textSecondary` (cyan purge)
- timeText: `Colors.cyan` → `Colors.textSecondary` (cyan purge)
- priceText: `Colors.cyan` → `Colors.textPrimary` (important value, not neutral metadata)
- #fff × 2 → `Colors.textPrimary`
- `rgba(255,255,255,0.4)` × 2 → `Colors.textMuted`
- `rgba(255,255,255,0.5)` → `Colors.textSecondary`
- `rgba(255,255,255,0.3)` → `Colors.textMuted`

**date-strip-picker.tsx** — 8 hardcoded values migrated:
- Added `import { Colors }` (was not imported)
- Removed `NEON_PURPLE` constant, replaced with `Colors.brandPrimary`
- Month active text: `#67E8F9` (cyan) → `Colors.brandPrimary` (cyan purge)
- `#fff` × 2 → `Colors.textPrimary`
- `rgba(255,255,255,0.35)` → `Colors.textMuted`
- `rgba(255,255,255,0.4)` → `Colors.textMuted`
- `rgba(255,255,255,0.1)` → `Colors.borderGlass`

**Retained technical exceptions (no matching token):**
- `rgba(11,11,15,0.78)` backdrop — specific alpha, no token
- `rgba(255,255,255,0.03)` × 2 — 3% opacity, no token
- `rgba(255,255,255,0.8)` dateTextInactive — 80% opacity between tokens
- `rgba(255,255,255,0.15)` badgeInactive — 15% opacity, no token

---

---

## Phase 3D — Event surface semantic token migration ✅

### 3D.1 event-card.tsx

| Current | Target | Rationale |
|---------|--------|-----------|
| `rgba(255,255,255,0.45)` (MapPin icon) | `Colors.textMuted` | Neutral icon colour (35% white) |
| `rgba(255,255,255,0.5)` (venueText) | `Colors.textSecondary` | Secondary metadata (60% white) |
| `rgba(255,255,255,0.35)` (distanceText) | `Colors.textMuted` | Tertiary metadata (35% white) |
| `rgba(255,255,255,0.3)` (atText) | `Colors.textMuted` | Tertiary metadata (35% white) |
| `'#fff'` × 3 (title, ctaText, Ticket icon) | `Colors.textPrimary` | Primary text (white) |
| `rgba(188,19,254,0.3)` (card border) | `Colors.borderFocus` | Brand-tinted active border (40% neon purple) |
| `rgba(18,18,24,0.85)` (card bg) | `Colors.surfaceCard` | Canonical card surface |
| `rgba(168,85,247,0.6)` (active border) | `Colors.eventSelected` | Selected-event accent |

### 3D.2 event-details.tsx

| Current | Target | Rationale |
|---------|--------|-----------|
| `rgba(255,255,255,0.7)` (closeBtn icon inline) | *(unmigrated — convertible to `Colors.textSecondary`)* | Inline SVG prop, missed in Phase 3D |
| `rgba(255,255,255,0.6)` × 3 (MapPin/Nav/Share icons inline) | *(unmigrated — convertible to `Colors.textSecondary`)* | Inline SVG props, missed in Phase 3D |
| `#A855F7` (hypeText style) | *(unmigrated — matches `Colors.purple`)* | Matches existing token, missed in Phase 3D |
| `rgba(12,12,18,0.95)` (sheet bg) | `Colors.surface` ✅ | Exact match |
| `rgba(255,255,255,0.12)` (sheet border) | `Colors.border` ✅ | Exact match |
| `rgba(255,255,255,0.10)` (closeBtn bg) | `Colors.borderGlass` ✅ | Exact match |
| `rgba(255,255,255,0.6)` (venueText style) | `Colors.textSecondary` ✅ | Secondary metadata |
| `rgba(255,255,255,0.4)` (distanceText style) | `Colors.textMuted` ✅ | Tertiary metadata |
| `'#fff'` × 3 (title, Ticket icon inline, ctaText) | `Colors.textPrimary` ✅ | Primary text |
| `#A855F7` (hypeBadge star/text) | *(unmigrated — matches `Colors.purple`)* | Matches existing token |

**Retained exceptions (no matching semantic token — 6 total):**
- `rgba(0,0,0,0.6)` backdrop — specific overlay alpha
- `rgba(255,255,255,0.20)` handleBar — between `textDisabled` (20%) and no surface token
- `rgba(168,85,247,0.15)` hypeBadge bg — specific purple alpha
- `rgba(255,255,255,0.05)` × 2 (pill bg, actionBtn bg) — 5% opacity
- `rgba(255,255,255,0.06)` (ctaWrapper border) — 6% opacity

**Phase 3D results: 8 style-level values migrated, 4 inline+1 style convertible values unmigrated, 6 true technical exceptions.**

**Phase 3D per-file retained raw counts:**
| File | Raw values remaining | Convertible (missed) | True exceptions |
|------|--------------------|---------------------|-----------------|
| event-card.tsx | 0 | 0 | 0 |
| event-details.tsx | 11 | 5 (4 inline + 1 `#A855F7` style) | 6 |
| MyEventListItem.tsx | 1 | 0 | 1 (`rgba(255,255,255,0.05)`) |
| saved.tsx | 0 | 0 | 0 |

### 3D.3 MyEventListItem.tsx

| Current | Target | Rationale |
|---------|--------|-----------|
| `#22D3EE` (time) | `Colors.textSecondary` | Cyan purge — ordinary date/time metadata |

### 3D.4 saved.tsx

| Current | Target | Rationale |
|---------|--------|-----------|
| `'#fff'` (countText) | `Colors.textPrimary` | Primary text |
| `Colors.purple` (sectionLabel) | `Colors.navigationActive` | Active accent for section headers |

## Phase 4 — Blur placement enhancements (P2)

### 4.1 Search bar blur

| Detail | Value |
|--------|-------|
| **File** | `apps/mobile/components/fomo/search-bar.tsx` |
| **Change** | Wrap `Animated.View` with `BlurView intensity={20}` for true frosted glass |
| **Current** | `Colors.surfaceGlass` (translucent rgba, no blur) |
| **Target** | `BlurView` with `Colors.surfaceGlass` as fallback bg |

### 4.2 Locate-me button blur

> **Android safety:** All BlurView additions must include a translucent solid fallback (`Colors.surfaceGlass`) as `backgroundColor` so the element remains readable on devices where blur does not render.



| Detail | Value |
|--------|-------|
| **File** | `apps/mobile/app/(tabs)/index.tsx` |
| **Change** | Wrap locate-me `Pressable` with `BlurView intensity={15}` |
| **Current** | Solid translucent `rgba(12, 12, 18, 0.85)` fill |
| **Target** | Blur-backed floating control |

---

## Dependency order

```
Phase 0 (tokens) ─┐
                  ├── Phase 1 (intent colours) ──── Phase 2 (cyan purge) ──── Phase 3 (hex cleanup) ──── Phase 4 (blur)
                  │       (single atomic change)         (per-component)
                  │
Phase 0.1 (neonGreen tokens)
Phase 0.2 (neonGreen gradient, optional)

Phase 1.1 (saved.tsx) ── requires Phase 0.1
Phase 1.2 (IntentSelector.tsx) ── requires Phase 0.1
Phase 1.3 (MyEventListItem.tsx) ── requires Phase 0.1
   └── all three can be done in parallel
```

---

## Files not in scope for any phase

- `apps/mobile/providers/auth-provider.tsx` — auth logic, no visual tokens
- `apps/mobile/hooks/*` — business logic, no visual tokens
- `apps/mobile/utils/*` — utilities, no visual tokens
- `apps/mobile/app/auth/callback.tsx` — no UI
- `apps/mobile/app/_layout.tsx` — only `StatusBar` and `Colors.background`, already correct
- `apps/mobile/app/(tabs)/_layout.tsx` — custom tab bar, already correct (purple active, glass blur)
- `apps/mobile/app/login.tsx` — already follows design system, no changes needed
- `apps/mobile/app/(tabs)/search.tsx` — placeholder, visual treatment only (deferred to FOMO-172)
- `apps/mobile/app/(tabs)/profile.tsx` — already follows design system
- `apps/mobile/components/fomo/fomo-map.tsx` — map pins already purple, correct
- `apps/mobile/components/fomo/calendar-view.tsx` — Phase 3C: migrated from cyan to semantic tokens; remaining rgba values are technical exceptions (see §3C)
- `apps/mobile/components/fomo/date-strip-picker.tsx` — Phase 3C: migrated from cyan/hardcoded NEON_PURPLE to semantic tokens

---

## Rollback plan

Each phase is independently revertible:

- **Phase 0:** Revert `theme/index.ts` changes
- **Phase 1:** Revert IntentSelector.tsx + saved.tsx + MyEventListItem.tsx
- **Phase 2:** Revert event-card.tsx + event-details.tsx colour lines
- **Phase 3:** Revert inline hex → token mappings
- **Phase 4:** Revert BlurView wrapping

No phase depends on a previous phase's runtime behaviour (Phase 0 is the sole dependency through import).
