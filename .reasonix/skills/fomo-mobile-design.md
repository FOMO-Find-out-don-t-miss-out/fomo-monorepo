---
description: Define, review, and implement the canonical global visual design system for the FOMO Expo mobile application.
---

# FOMO Mobile Global Design Skill

Use this skill for any task that defines or changes the visual language of the
FOMO mobile application.

Read before acting:

- REASONIX.md
- apps/mobile/DESIGN.md, when present
- apps/mobile/theme
- apps/mobile/components/ui
- apps/mobile/components/fomo
- apps/mobile/app
- docs/mobile/mobile-performance-baseline.md

## Required process

1. Audit before editing.
2. Identify existing shared primitives and semantic tokens.
3. Propose the design contract before broad implementation.
4. Render and inspect the result rather than only checking compilation.
5. Work in small reviewable iterations.
6. Preserve all product and performance behavior.
7. Never commit or push without explicit approval.

## Visual direction

- near-black dark UI
- restrained liquid glass
- neon purple primary accent
- neon green secondary accent
- strong event imagery and map hierarchy
- limited, purposeful glow
- no generic AI visual patterns

## Semantic mapping

- brand.primary: purple
- brand.secondary: green
- intent.interested: purple
- intent.going: green
- navigation.active: purple
- event.selected: purple
- location.user: green
- event.live: green
- feedback.success: green
- feedback.warning: amber
- feedback.error: red

## Design constraints

Avoid:

- rainbow gradients
- excessive rounded cards
- nested glass without hierarchy
- giant bloom effects
- tiny low-contrast text
- arbitrary screen-level colors
- full-screen blur
- per-list-row blur
- decorative effects competing with event imagery
- new UI copy that exposes internal instructions

## Required component system

Define and reuse canonical forms of:

- FomoScreen
- ScreenHeader
- GlassSurface
- GlassCard
- GlassBottomSheet
- GlassTabBar
- GlassSegmentedControl
- SearchField
- PrimaryNeonButton
- SecondaryNeonButton
- GhostButton
- NeonIconButton
- EventCard
- MyEventListItem
- IntentSelector
- CategoryChip
- StatusBadge
- CountBadge
- EmptyState
- ErrorState
- LoadingState
- SkeletonState
- OfflineState

## Review checklist

For each changed screen confirm:

- it follows apps/mobile/DESIGN.md
- purple and green have consistent semantic meaning
- text contrast is readable
- touch targets are at least 44x44
- loading, empty, error and disabled states are covered
- no bare hex value was added outside canonical token files
- no performance regression was introduced
- browser and Android behavior are distinguished honestly
