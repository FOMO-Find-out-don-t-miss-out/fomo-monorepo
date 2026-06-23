# FOMO Mobile Theme

Design system foundation for `apps/mobile`. Established in FOMO-171.1.

---

## Visual Direction

Dark-first, modern/neon. FOMO is about energy and discovery — the UI should feel alive but readable.

- **Background**: deep near-black (`#0B0B0F`)
- **Surfaces**: dark glass cards with subtle borders and blur
- **Accents**: violet/purple primary, cyan for time/data, magenta for secondary emphasis
- **Typography**: Inter family — clean, modern, legible at all sizes
- **Glow**: used sparingly — active states, CTAs, selected pins only

---

## Token File

All tokens live in `apps/mobile/theme/index.ts`. Import from there:

```typescript
import { Colors, Gradients, Typography, Spacing, Radii, Shadows } from '../theme';
```

### Colors

| Token | Value | Use |
|---|---|---|
| `Colors.background` | `#0B0B0F` | Screen backgrounds |
| `Colors.surface` | `rgba(12,12,18,0.95)` | Modal/sheet backgrounds |
| `Colors.surfaceGlass` | `rgba(18,18,24,0.75)` | Glass input/panel backgrounds |
| `Colors.surfaceCard` | `rgba(12,12,18,0.85)` | Event card background |
| `Colors.border` | `rgba(255,255,255,0.12)` | Default borders |
| `Colors.borderGlass` | `rgba(255,255,255,0.10)` | Glass element borders |
| `Colors.borderSubtle` | `rgba(255,255,255,0.08)` | Dividers |
| `Colors.borderFocus` | `rgba(188,19,254,0.40)` | Focused/active border |
| `Colors.purple` | `#A855F7` | Primary interactive, icons, focus |
| `Colors.purpleNeon` | `#BC13FE` | CTAs, badges, glow source |
| `Colors.purpleDim` | `rgba(168,85,247,0.20)` | Active button fill, low-key highlights |
| `Colors.purpleGlow` | `rgba(168,85,247,0.45)` | Shadow/glow opacity |
| `Colors.cyan` | `#22D3EE` | Time, date, data fields |
| `Colors.magenta` | `#EC4899` | Secondary accent |
| `Colors.textPrimary` | `#FFFFFF` | Headings, titles |
| `Colors.textSecondary` | `rgba(255,255,255,0.60)` | Body text, labels |
| `Colors.textMuted` | `rgba(255,255,255,0.35)` | Captions, placeholders |
| `Colors.textDisabled` | `rgba(255,255,255,0.20)` | Disabled elements |
| `Colors.error` | `#F87171` | Errors, destructive |
| `Colors.success` | `#4ADE80` | Confirmations |
| `Colors.warning` | `#FBBF24` | Warnings |

### Category Swatches

```typescript
Colors.category['Music']    // { border, text, bg }
Colors.category['Arts']
Colors.category['Theater']
Colors.category['Sports']
Colors.category['Comedy']
Colors.category['Festival']
```

Each swatch provides `border`, `text`, and `bg` fields. Use:
- `border` for badge/chip border
- `text` for label color
- `bg` for badge fill

### Gradients

```typescript
Gradients.primaryCta    // ['#BC13FE', '#9333EA'] — primary action buttons
Gradients.purpleSubtle  // ['rgba(188,19,254,0.3)', ...] — active fill overlays
```

### Typography

```typescript
Typography.font.regular     // 'Inter_400Regular'
Typography.font.medium      // 'Inter_500Medium'
Typography.font.semiBold    // 'Inter_600SemiBold'
Typography.font.bold        // 'Inter_700Bold'
Typography.font.extraBold   // 'Inter_800ExtraBold'

Typography.size.xs          // 9
Typography.size.sm          // 11
Typography.size.base        // 13
Typography.size.md          // 14
Typography.size.lg          // 15
Typography.size.xl          // 18
Typography.size['2xl']      // 20
Typography.size['3xl']      // 22
Typography.size.hero        // 36
```

### Spacing

```typescript
Spacing.xs    // 4
Spacing.sm    // 8
Spacing.md    // 12
Spacing.base  // 16
Spacing.lg    // 20
Spacing.xl    // 24
Spacing['2xl'] // 32
```

### Radii

```typescript
Radii.sm    // 8
Radii.md    // 12
Radii.lg    // 14
Radii.xl    // 16
Radii['2xl'] // 20
Radii.full  // 9999 — pills, circles
```

### Shadows

```typescript
Shadows.cardActive   // Purple glow on active/selected card
Shadows.ctaGlow      // Neon purple glow on CTA buttons
```

Use spread: `style={{ ...Shadows.ctaGlow, borderRadius: 12 }}`.

---

## UI Primitives

Located in `apps/mobile/components/ui/`. Import from the barrel:

```typescript
import { FomoButton, FomoEmptyState, FomoErrorState, FomoIconButton, FomoLoadingState, FomoScreen } from '../../components/ui';
```

### `FomoScreen`

Root wrapper for every screen. Sets `flex:1` and `Colors.background`.

```tsx
<FomoScreen style={optionalOverride}>
  {children}
</FomoScreen>
```

### `FomoButton`

```tsx
// Primary — gradient CTA
<FomoButton label="Save" onPress={handleSave} />

// Ghost — secondary/cancel/logout
<FomoButton label="Log Out" variant="ghost" icon={<LogOut />} onPress={logout} />

// Danger — destructive
<FomoButton label="Delete" variant="danger" onPress={handleDelete} />

// Loading state
<FomoButton label="Saving…" loading />

// Disabled
<FomoButton label="Go" disabled />
```

### `FomoIconButton`

For single-icon actions and toggleable relationship buttons (Saved, Interested, Going).

```tsx
// Default (not active)
<FomoIconButton icon={<Bookmark size={18} color={Colors.textSecondary} />} onPress={handleSave} />

// Active (bookmarked/saved)
<FomoIconButton
  icon={<Bookmark size={18} color={Colors.purple} />}
  active
  onPress={handleSave}
  accessibilityLabel="Remove from saved"
/>

// Custom active color
<FomoIconButton icon={<Heart />} active activeColor={Colors.magenta} onPress={handleInterested} />

// Small variant
<FomoIconButton size="sm" icon={<Share2 size={14} />} onPress={share} />
```

### `FomoEmptyState`

```tsx
<FomoEmptyState
  icon={<Heart size={48} color={Colors.purple} strokeWidth={1.2} />}
  message="No saved events yet"
  sub="Tap the bookmark on any event to save it here."
  action={{ label: 'Explore Events', onPress: navigateToDiscover }}
/>
```

### `FomoLoadingState`

```tsx
<FomoLoadingState />
// or with custom color:
<FomoLoadingState color={Colors.cyan} />
```

### `FomoErrorState`

```tsx
<FomoErrorState message="Could not load events" onRetry={refetch} />
```

---

## How Future Features Should Use the Theme

### Adding a new screen

```tsx
import { FomoScreen } from '../../components/ui';

export default function MyScreen() {
  return (
    <FomoScreen>
      {/* content */}
    </FomoScreen>
  );
}
```

### Adding an action button

```tsx
import { FomoButton } from '../../components/ui';
import { Colors } from '../../theme';

<FomoButton label="Mark Interested" onPress={handleInterested} />
```

### Adding a toggle icon button (relationship action)

```tsx
import { FomoIconButton } from '../../components/ui';
import { Heart } from 'lucide-react-native';
import { Colors } from '../../theme';

<FomoIconButton
  icon={<Heart size={18} color={isInterested ? Colors.magenta : Colors.textMuted} strokeWidth={1.5} />}
  active={isInterested}
  activeColor={Colors.magenta}
  onPress={toggleInterested}
  accessibilityLabel={isInterested ? 'Remove interest' : 'Mark interested'}
/>
```

### Adding a category badge

```tsx
import { Colors } from '../../theme';

const cat = Colors.category[event.category];
<View style={{ borderWidth: 1, borderColor: cat.border, backgroundColor: cat.bg, borderRadius: Radii.full, paddingHorizontal: 8, paddingVertical: 2 }}>
  <Text style={{ color: cat.text, fontSize: Typography.size.xs, fontFamily: Typography.font.semiBold }}>
    {event.category}
  </Text>
</View>
```

---

## Anti-Patterns

**Do not do these:**

```typescript
// ❌ Bare hex literal in a component
backgroundColor: '#BC13FE'

// ✅ Use token
backgroundColor: Colors.purpleNeon

// ❌ One-off button style copied from another component
const styles = StyleSheet.create({ btn: { backgroundColor: '#A855F7', borderRadius: 12, ... } })

// ✅ Use FomoButton
<FomoButton label="Action" onPress={...} />

// ❌ Fake local visual state pretending to be persisted data
const [isSaved, setIsSaved] = useState(false);  // stored only in component memory

// ✅ Wire to backend via authenticated API call; derive state from server response

// ❌ Neon glow on every element
shadowColor: '#BC13FE', shadowRadius: 20, shadowOpacity: 1.0

// ✅ Glow is reserved for active card state and CTA buttons — use Shadows.cardActive or Shadows.ctaGlow

// ❌ Random locally-defined color constants duplicating theme values
const NEON_PURPLE = '#BC13FE';
const GLASS_BG = 'rgba(18,18,24,0.75)';

// ✅ Import from theme
import { Colors } from '../../theme';
```

---

## Component State Reference

| State | Visual treatment |
|---|---|
| Default | `Colors.borderGlass`, `Colors.surfaceGlass` background |
| Pressed | `opacity: 0.75–0.85` |
| Active/Selected | `Colors.purple` or `activeColor` border, `purpleDim` fill |
| Disabled | `opacity: 0.35–0.45` |
| Loading | `ActivityIndicator` in `Colors.purple` |
| Error | `Colors.error` text and icon |
| Success | `Colors.success` text or icon flash |
