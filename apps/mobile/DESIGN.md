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
- **Cyan** (`#22D3EE`, `#06B6D4`) must never appear as a secondary button, intent indicator, navigation element, or global control. It is permitted **only** in the Festival category swatch. Calendar-view active state must use the canonical primary purple (`#BC13FE`).
- Date and time text are neutral metadata — use `Colors.textSecondary`. Neon green is reserved for Going, user location, live/available state, and success confirmation. A genuine "LIVE NOW" badge may use neon green, but a future event timestamp may not.

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

> BlurView is **optional**, not mandatory for the design identity. Native Android blur is **deferred** — no product delivery or visual migration depends on BlurView support. Existing stable BlurView surfaces (tab navigation, EventDetails sheet) may remain; new surfaces require proven visual value and physical-device testing. Cards, rows, CalendarView and screen backgrounds remain blur-free.
>
> On Android, all BlurView-backed elements pair with a translucent solid fallback (`--surface-glass` as `backgroundColor`) so the element is readable on all devices. Never let an element become invisible when blur does not render. Premium visual quality on Android comes from: surface hierarchy, translucent fills, subtle borders, restrained purple glow, clear active states, typography and spacing.

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

---

## 11. Physical-device UI validation

Visual UI changes require physical Android validation. No other validation
is sufficient.

### Mandatory gates

- **Static inspection** — JSX structure and StyleSheet completeness
- **`pnpm --filter @fomo/mobile lint`** — must pass
- **`pnpm --filter @fomo/mobile exec tsc --noEmit`** — must pass
- **Physical Android screenshot** at 360px, 390px, and 412px
- **Physical interaction check** (press, scroll, keyboard, modal open/close)

Lint is not design validation. TypeScript is not layout validation.
Static JSX structure is not rendered proof. Implementation reports are
not sufficient without physical evidence.

### Design gates

Change only one visual region per phase. Approve before moving to the next.

Regions: Discover header, Explore shell, event result cell, filter modal,
future entity states.

### Diagnostic workflow

When rendered layout contradicts JSX/styles:

1. Add temporary high-contrast diagnostic colors (red/green/blue) to root,
   fixed, and flexible children.
2. Capture a physical screenshot.
3. Interpret which styles reach native rendering.
4. Apply the smallest proven correction.
5. Remove every diagnostic color before committing.

### Production requirements

- Use semantic tokens (`Colors`, `Spacing`, `Typography`, `Radii`) — no raw
  hex or bare pixel values in UI components.
- Real and fallback media must preserve identical geometry.
- Responsive flex children must be verified at 360px, 390px, and 412px.
- Diagnostic colors must not appear in committed code.
- Do not document inferred root causes as proven unless a diagnostic
  screenshot confirms them.

See `docs/design/mobile-explore-ui.md` for the canonical Explore UI
specification and physical-validation workflow.

---

## 12. Action hierarchy and button geometry

Action footers in FOMO mobile follow a strict hierarchy: one dominant
primary action and one visibly structured secondary action. The two must
read as one deliberate composition — secondary is never loose unbounded
text when the design calls for a button.

### Geometry ownership

- **One component layer owns width, height, radius, and overflow.** The
  internal visual layer owns background/gradient and label centering.
- Do not split height ownership between a wrapper and a reusable child
  whose internal padding and flex are hidden behind its API.
- Do not apply an external `height` to a generic button component without
  inspecting its internal flex, padding, and `Pressable`/`LinearGradient`
  implementation. The generic component may not produce the requested
  geometry on a physical Android device.

### Flex rules for fixed-height action rows

- `flex: 1` may distribute horizontal width only when the parent is a
  `flexDirection: 'row'` container with constrained height.
- Fixed-height footer actions must never gain vertical flex from a
  column-direction parent or from `alignSelf: 'stretch'` on the vertical
  axis.
- Do not use percentage heights (`height: '100%'`).
- Do not use `flexGrow` on the vertical axis for action controls.

### Text centering in buttons

- `alignItems: 'center'` and `justifyContent: 'center'` on the element
  that owns the background/gradient.
- Explicit `lineHeight` matching the font size + 2–4px.
- `includeFontPadding: false` on Android.
- `textAlign: 'center'` on the label.
- Physical Android validation is mandatory — label centering must be
  verified in a screenshot, not assumed from static styles.

### Physical validation gate for action footers

- Measure that top and bottom coordinates are identical for every action.
- Verify equal visual height across all actions.
- Verify label centering on both axes.
- Verify at 360px width.
- Lint and TypeScript are not visual proof.

### When a generic button does not satisfy required geometry

A local control with `TouchableOpacity` + static `style` + `LinearGradient`
(where a gradient primary is needed) is the acceptable fallback when the
generic `FomoButton` cannot reliably produce the required fixed dimensions
on the target Android device. This is a component-specific implementation
decision, not a blanket rejection of reusable buttons elsewhere.

Do not use `Pressable` functional style callbacks (`style={({ pressed }) =>
[...]}`) for action controls that require guaranteed geometry — use
`TouchableOpacity` with a static `style` prop and native `activeOpacity`
instead.

See `docs/design/mobile-explore-ui.md` for the canonical Explore
filter-modal footer contract.
