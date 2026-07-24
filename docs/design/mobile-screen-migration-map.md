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

### 0.2 Add neon-green gradient tokens (optional)

| Detail | Value |
|--------|-------|
| **File** | `apps/mobile/theme/index.ts` |
| **Changes** | Add `Gradients.goingCta: ['#39FF88', '#22C55E'] as [string, string]` |
| **Impact** | Zero — consumed only when intent selector uses it |
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
- Line 159: dateText uses `#22D3EE` in styles → change to `Colors.neonGreen` (if carrying temporal weight) or `Colors.textSecondary`

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

---

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
- `apps/mobile/components/fomo/calendar-view.tsx` — minor cyan usage in event rows (accepted as category-related)

---

## Rollback plan

Each phase is independently revertible:

- **Phase 0:** Revert `theme/index.ts` changes
- **Phase 1:** Revert IntentSelector.tsx + saved.tsx + MyEventListItem.tsx
- **Phase 2:** Revert event-card.tsx + event-details.tsx colour lines
- **Phase 3:** Revert inline hex → token mappings
- **Phase 4:** Revert BlurView wrapping

No phase depends on a previous phase's runtime behaviour (Phase 0 is the sole dependency through import).
