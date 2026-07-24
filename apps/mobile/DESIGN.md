# FOMO Mobile — Global UI Design Contract

> **Canonical authority for visual decisions across all mobile screens.**
> Layout? → Sketch. Interaction? → Prototype. Colour? → Here.

---

## 1. Design direction

### Emotional positioning

| Dimension | Target |
|-----------|--------|
| Vibe | Nocturnal · urban · alive · premium |
| Energy | Energetic · social · modern · slightly futuristic |
| Antonym | Corporate · generic SaaS · fintech · childish · gaming dashboard · AI-generated purple-gradient template |

**One-line brief:** *"The city is alive right now, and something worth attending is always close."*

### Visual pillars

1. **Near-black foundation** — `#0B0B0F` background, not charcoal, not pure black. Surfaces are translucent overlays on this void, never opaque cards on a light canvas.
2. **Restrained liquid glass** — real `BlurView` only on: floating search bar, global navigation pill, floating map controls, bottom sheets, dialogs/modals, selected elevated overlays. Never on every event card, every My Events row, every badge, whole-screen backgrounds, or long virtualized lists.
3. **Two-accent system** — neon purple (primary) + neon green (secondary). Magenta and cyan exist only as restrained category colours within the filter/search taxonomy, never as global accents.
4. **Premium restraint** — one decisive accent per screen (the primary CTA + maybe an eyebrow). Three accents on one screen is noise.

---

## 2. Canonical colour tokens

### Palette

| Token | Hex / OKLch | Usage |
|-------|-------------|-------|
| `--bg` | `#0B0B0F` | Root background |
| `--surface` | `rgba(12, 12, 18, 0.95)` | Cards, sheets, elevated panels |
| `--surface-glass` | `rgba(18, 18, 24, 0.75)` | Blur-backed surfaces (search, nav, modals) |
| `--surface-card` | `rgba(12, 12, 18, 0.85)` | Event cards, list items |
| `--border` | `rgba(255, 255, 255, 0.12)` | Standard borders |
| `--border-subtle` | `rgba(255, 255, 255, 0.08)` | Dividers, section separators |
| `--border-focus` | `rgba(188, 19, 254, 0.40)` | Focus rings, active search state |
| `--neon-purple` | `#BC13FE` | Brand, primary CTA, active navigation, selected event, "Interested" |
| `--purple` | `#A855F7` | Secondary purple (category, softer accent) |
| `--purple-dim` | `rgba(168, 85, 247, 0.20)` | Subtle purple fills, active backgrounds |
| `--purple-glow` | `rgba(168, 85, 247, 0.45)` | Shadow glow for active cards |
| `--neon-green` | `#39FF88` | Brand secondary, "Going", user location, live/available state, success |
| `--green` | `#4ADE80` | Softer green (Sports category) |
| `--text-primary` | `#FFFFFF` | Primary body/headline |
| `--text-secondary` | `rgba(255, 255, 255, 0.60)` | Secondary copy |
| `--text-muted` | `rgba(255, 255, 255, 0.35)` | Captions, hints |
| `--text-disabled` | `rgba(255, 255, 255, 0.20)` | Disabled states |
| `--error` | `#F87171` | Error text, destructive actions |

### Accent binding (canonical — enforce throughout)

| Element | Colour |
|---------|--------|
| Brand / logo | `--neon-purple` |
| Primary CTA | `--neon-purple` gradient (`#BC13FE` → `#9333EA`) |
| Active navigation tab | `--neon-purple` |
| Selected event card border/glow | `--neon-purple` / `--purple-glow` |
| **Interested** (all surfaces) | `--neon-purple` |
| **Going** (all surfaces) | `--neon-green` |
| User location dot | `--neon-green` |
| Live / available state | `--neon-green` |
| Success feedback | `--neon-green` |
| Category: Music | `--purple` |
| Category: Arts | `--magenta` (`#EC4899`) — restrained |
| Category: Theater | `--amber` (`#F59E0B`) |
| Category: Sports | `--green` (`#22C55E`) |
| Category: Comedy | `--orange` (`#F97316`) |
| Category: Festival | `--cyan` (`#06B6D4`) — restrained |

### Prohibitions

- **Magenta** (`#EC4899`) must never appear as a global accent. It is permitted **only** in the Arts category swatch.
- **Cyan** (`#22D3EE`, `#06B6D4`) must never appear as a secondary button or intent indicator. It is permitted only in the Festival category swatch and the calendar-view toggle.
- No bare hex `#22D3EE` on date/time text, event prices, or pill backgrounds. Those belong to neon green (`#39FF88`) when carrying semantic weight.

---

## 3. Typography

| Role | Family | Weight | Size (px) |
|------|--------|--------|-----------|
| Display (section titles, hero) | Inter | ExtraBold (800) | 20–36 |
| Headline (card title, sheet title) | Inter | Bold (700) | 14–20 |
| Body | Inter | Regular (400) | 13–15 |
| Caption / badge | Inter | SemiBold (600) | 9–11 |
| Small label / eyebrow | Inter | Bold (700) | 9–10 |
| Numerics (distance, price, counts) | Inter | Bold (700) | 9–13 |

All weights loaded: `Inter_400Regular`, `Inter_500Medium`, `Inter_600SemiBold`, `Inter_700Bold`, `Inter_800ExtraBold`.

---

## 4. Liquid-glass placement

> **Do not remove expo-blur.** Blur is part of the design identity. The rules below limit blur to elevated surfaces where it adds value; repeated/virtualised items use translucent solid fills instead.

### Allow blur on

| Element | Rationale |
|---------|-----------|
| Floating search bar | Scrim effect over map content |
| Global navigation pill | Always-on-bottom UI chrome |
| Floating map controls | Locate-me, view toggle |
| Bottom sheets (EventDetails) | Sheet backdrop over full-screen content |
| Dialogs and modals | Focus/elevation affordance |
| Selected elevated overlays | Highlighted state |

**Android note:** `BlurView` has variable support on Android (hardware-dependent). Always pair blur with a translucent solid fallback (`--surface-glass` as `backgroundColor`) so the element is readable on all devices. Never let an element become invisible when blur does not render.

### Do NOT use blur on

| Element | Alternative |
|---------|-------------|
| Every event card | Translucent fill (`--surface-card`) + subtle border + top highlight |
| Every My Events row | Translucent fill (`--surface-card`) + left accent bar |
| Badges | Solid fill with accent colour |
| Whole-screen backgrounds | Solid `--bg` (`#0B0B0F`) |
| Long virtualized lists | None — neither individual nor collective blur |
| Category chips | Translucent fill, no blur |

### Repeated-item styling (no blur)

- Translucent background (`--surface-card`)
- 1px subtle border (`--border-subtle`)
- Optional: left accent bar for list items (3px, category-colour or intent-colour)
- Active-state: increased border opacity + subtle background tint (`--purple-dim` for primary, accent-dim for others)
- No per-row shadow on virtualized lists

---

## 5. Search — visual treatment only (deferred to FOMO-172)

The Search tab (`apps/mobile/app/(tabs)/search.tsx`) is currently a placeholder rendering `FomoEmptyState` with "Search is coming soon".

**This design task defines only the visual treatment:**
- Search bar styling (already covered by SearchBar component in §4)
- Search screen layout chrome
- Empty/focused states as static visual references

**Explicitly out of scope:**
- Search functionality, query logic, autocomplete
- Mock recent searches, trending events, or hard-coded results
- Any network requests or search API integration (FOMO-172)
- Search history or persistence

The functional search implementation belongs to FOMO-172 (not part of this global UI migration).

---

## 6. Design scope — visual styling and reusable primitives only

This migration covers:

✅ Colour token corrections (neon green, intent colours, cyan purge)
✅ Hardcoded hex → theme token migration
✅ BlurView placement for elevated surfaces
✅ Repeated-item styling (translucent fills, borders, active-state glow)

**Never implement:**

❌ Backend changes, new APIs, or contract modifications
❌ New product features or search functionality
❌ Mock data replacing API-backed screens
❌ Relationship semantics or auth behaviour changes
❌ Navigation architecture changes
❌ New state-management frameworks

API-backed screens (Discover, My Events, Profile) remain API-backed. No screen is replaced with a mock, prototype, or hard-coded implementation.

---

## 7. Current deviations from canonical (summary)

| # | Location | Current | Canonical | Severity |
|---|----------|---------|-----------|----------|
| 1 | Theme `Colors` | No `neonGreen` token | Add `#39FF88` as `neonGreen` | P0 |
| 2 | `saved.tsx` tab bar | Interested = `Colors.magenta` | Interested = `Colors.purple` / `neonPurple` | P0 |
| 3 | `saved.tsx` tab bar | Going = `Colors.success` | Going = `Colors.neonGreen` | P0 |
| 4 | `IntentSelector.tsx` | Interested = `Colors.magenta` | Interested = `Colors.purple` | P1 |
| 5 | `IntentSelector.tsx` | Going = `Colors.cyan` | Going = `Colors.neonGreen` | P1 |
| 6 | `MyEventListItem.tsx` | Intent dot = `Colors.magenta` (interested) | Intent dot = `Colors.purple` | P1 |
| 7 | `event-card.tsx` | Date/time = `#22D3EE` (cyan) | Date/time = `Colors.neonGreen` or `Colors.textSecondary` | P1 |
| 8 | `event-card.tsx` | Price = `#22D3EE` (cyan) | Price = `Colors.textPrimary` or removed (no real data) | P2 |
| 9 | `event-details.tsx` | Date/time pills = `#22D3EE` (cyan) | Date/time pills = `Colors.textSecondary` | P1 |
| 10 | `event-details.tsx` hype badge | Purple fill | Keep (already correct — uses `#A855F7`) | — |

---

## 8. Implementation priority

### P0 — Before ship-blocking
1. Add `neonGreen` (`#39FF88`) and `neonGreenDim`/`neonGreenGlow` to theme
2. Fix My Events tab bar colours (saved.tsx: magenta→purple for Interested, success→neonGreen for Going)
3. Fix IntentSelector (magenta→purple for Interested, cyan→neonGreen for Going)
4. Fix MyEventListItem intent dot colours
5. Remove `#22D3EE` hardcodes from event cards and event details date/time

### P1 — Polish pass
1. Convert remaining `#22D3EE` hardcodes in event-details and calendar-view to canonical tokens
2. Review and standardise all inline `rgba(255,255,255,…)` border/background values to theme tokens

### P2 — Cleanup
1. Remove unused `Colors.cyan` if no legitimate category-only usage remains
2. Verify `Colors.magenta` is only used for Arts category

---

## 9. Performance invariants (do not violate)

- Discover FlatList virtualization intact
- memoized EventCard and MyEventListItem
- Stable callbacks — `onPress` receives id, creates no per-row closures
- One initial discovery request (no duplicate startup fetch — FOMO-176)
- Optimised relationship synchronisation (revision-counter gating — FOMO-177)
- Optimised My Events fetching (parallel hooks, local-intent application — FOMO-178)
- Non-blocking authenticated profile sync (FOMO-179)

---

## 10. Product invariants (do not change)

- API contracts
- Discovery behaviour
- Map behaviour
- Event ordering
- Navigation behaviour
- Interested/Going semantics
- Authentication behaviour
- Loading/error semantics
- Accessibility semantics
