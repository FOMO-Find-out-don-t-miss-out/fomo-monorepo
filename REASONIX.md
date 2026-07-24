# FOMO Mobile Design Work

## Scope

The current design task applies only to:

- apps/mobile
- docs/design
- apps/mobile/DESIGN.md
- project-level Reasonix/Open Design configuration

Do not modify backend, infrastructure, dashboard, generated API contracts, or
business logic unless explicitly requested.

## Repository behavior

- Work directly on the current main branch.
- Never run git commit, git push, git reset, git clean, or destructive Git
  operations without explicit user approval.
- Keep every iteration reviewable.
- Show the exact diff before requesting approval to commit.
- Do not overwrite existing behavior merely to simplify styling.

## Mobile architecture

- Expo / React Native
- Expo Router
- TypeScript
- central theme in apps/mobile/theme
- shared primitives in apps/mobile/components/ui
- feature components in apps/mobile/components/fomo
- Inter typography
- existing Expo Blur and Expo Linear Gradient dependencies
- physical Android device is the final native validation target

## Required visual direction

FOMO is:

- nocturnal
- urban
- alive
- premium
- energetic
- social
- modern
- slightly futuristic

FOMO is not:

- corporate
- generic SaaS
- fintech
- childish
- a gaming dashboard
- visual cyberpunk clutter
- an AI-generated purple-gradient template

The emotional idea is:

"The city is alive right now, and something worth attending is always close."

## Canonical accents

Primary:
- neon purple
- brand, primary CTA, Interested, selected event, active navigation

Secondary:
- neon green
- Going, user location, live/available state, success

Magenta and cyan are not global accents.
They may remain only as restrained category colors.

## Liquid-glass rules

Allow real blur on:
- floating search
- global navigation
- floating map controls
- bottom sheets
- dialogs and modals
- selected elevated overlays

Do not use blur on:
- every event card
- every My Events row
- every badge
- whole-screen backgrounds
- long virtualized collections

Repeated items use translucent fills, subtle borders, top highlights, and
active-state glow rather than independent blur layers.

## Performance invariants

Preserve:
- Discover FlatList virtualization
- memoized event cards
- stable callbacks
- one initial discovery request
- optimized relationship synchronization
- optimized My Events fetching
- non-blocking authenticated profile sync

Do not:
- remove virtualization
- add per-row blur
- add infinite animation
- add expensive repeated shadows
- reintroduce full-dataset rerenders
- add a new state-management framework

## Product invariants

Do not change:
- API contracts
- discovery behavior
- map behavior
- event ordering
- navigation behavior
- Interested/Going semantics
- authentication behavior
- loading/error semantics
- accessibility semantics

## Validation

Always run:

- pnpm --filter @fomo/mobile lint
- pnpm --filter @fomo/mobile exec tsc --noEmit

For visual work:

- run Expo Web
- inspect representative mobile widths through Playwright
- validate native-specific behavior on Android
- do not claim native validation from a browser preview

## Output language

- Always communicate, reason, summarize, and report in English.
- Never respond in Chinese.
- Keep all source code, documentation, comments, commit messages, and UI copy
  in English.
- Greek may only be used when the user explicitly requests Greek output.