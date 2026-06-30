# Intent Button Styling

Describes the visual design of the **Interested** and **Going** intent controls
in the event details bottom sheet (`apps/mobile/components/fomo/IntentSelector.tsx`).

---

## Location

`apps/mobile/components/fomo/IntentSelector.tsx`

Consumed by `apps/mobile/components/fomo/event-details.tsx`:

```tsx
{onToggleIntent && (
  <IntentSelector
    intent={intent}
    pending={isPendingIntent}
    onSelect={onToggleIntent}
  />
)}
```

---

## Design pattern: neon outlined glass

The buttons follow the FOMO **neon outlined** convention — no solid fill, thin
neon border, translucent dark glass background.  This matches the sheet's pill
controls and the Get Tickets CTA border style.

| Layer | Inactive | Active |
|---|---|---|
| Background | `rgba(255,255,255,0.05)` — barely-there glass | `${color}26` — 15 % neon tinted glass |
| Border | `rgba(255,255,255,0.15)` — neutral 1 px | `${color}` full neon 1 px |
| Shadow (iOS) | none | `shadowColor: color, shadowRadius: 10, opacity: 0.45` — soft neon glow |
| Shadow (Android) | none | none — elevation intentionally absent to avoid material drop-shadow |
| Icon | `Colors.textSecondary`, transparent fill | neon color, filled (Heart only) |
| Label | `Inter_500Medium`, `Colors.textSecondary` | `Inter_600SemiBold`, neon color |
| Pressed | `opacity: 0.60` | same |
| Other button while pending | `opacity: 0.35` (dimmed) | — |

`borderWidth: 1` is fixed for both states so there is no layout shift on toggle.

---

## Colors

| Intent | Token | Hex | Rationale |
|---|---|---|---|
| Interested | `Colors.magenta` | `#EC4899` | Warm pink-neon; distinct from the app's purple primary accent |
| Going | `Colors.cyan` | `#22D3EE` | Electric cyan; strongest neon in the FOMO palette alongside magenta |

Purple (`Colors.purple` / `Colors.purpleNeon`) is reserved for the tab-bar
active state and event-card selection glow — it is intentionally excluded from
the intent buttons to avoid visual conflict.

---

## States

- **Inactive** — both buttons show a neutral glass outline.  Neither appears
  selected.
- **One active** — the matching button shows its neon border + tint + iOS glow.
  The other button remains in neutral inactive style.
- **Pending (API in flight)** — the active button shows an `ActivityIndicator`
  in the neon color; the inactive button dims to 35 % opacity to communicate
  that only one action is possible at a time.
- **Not authenticated** — the parent passes `onToggleIntent={undefined}`; the
  `IntentSelector` is not rendered at all (controlled by `event-details.tsx`).

---

## Press feedback

`android_ripple={null}` disables the Android ink ripple, which does not
render cleanly inside a `BlurView` and overflows the border radius on older
API levels.  Press feedback is provided via `opacity: 0.60` on the pressed
state instead, which is consistent across platforms.
