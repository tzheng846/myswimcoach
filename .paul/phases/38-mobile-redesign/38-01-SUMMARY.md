# 38-01 SUMMARY — Design system + nav skeleton + Login

**Status:** Code-complete; device verification DEFERRED to end of phase (see 38-TEST-PLAN.md).
`npx expo export --platform ios` exits 0 (1040 modules).

## What shipped (all in swimnetics-mobile)
- `src/theme/tokens.js` + `index.js` — LOCKED light palette (user-approved 2026-06-19 via 2
  mockup rounds), type scale, spacing, radii, shadows, motion. Single source of truth; components
  read token keys, never raw hex.
- `src/components/ui/` — `AppText`, `Screen` (SafeAreaView + bg + scroll/KAV), `Card` (white
  raised / `alt` lavender tile), `Button` (primary/secondary/accent/ghost/danger, solid-purple
  primary, pressed tints in tokens), `SectionHeader`, `TabIcons` (SVG: Dashboard/Team/History/
  Settings), `TabBar` (custom — Record raised island).
- `src/navigation/RootTabs.js` — bottom-tab navigator (Dashboard, Team=Athletes,
  RecordingConfig=Record island, SessionHistory=History) wrapped in a root native-stack for
  full-screen details (Record, VideoOverlay, ReportCard, Devices, Diagnostics).
- `src/screens/DashboardScreen.js` — themed stub (real content = 38-02).
- `App.js` — rewired: SafeAreaProvider, light StatusBar, RootTabs when authed / Login when not.
- `src/screens/LoginScreen.js` — restyled to tokens (light theme); auth logic unchanged.
- `package.json` — added `@react-navigation/bottom-tabs` (JS-only; no native build needed).

## Deviations from plan
- Added `SafeAreaProvider` to App.js (required for the safe-area hooks used by Screen/TabBar).
- Added pressed-tint tokens (`secondaryPressed`/`accentPressed`/`dangerPressed`) so Button has
  zero raw hex (honors AC-1).
- Route-naming: tab routes reuse existing navigate() target names (`RecordingConfig`,
  `SessionHistory`) so cross-screen navigation keeps resolving; details live on the root stack.
- Plan's human-verify checkpoint → deferred (workflow change: batch all device testing at phase
  end). Items moved to 38-TEST-PLAN.md.

## Carry-forward / known stubs
- Dashboard stub, inert Settings gear, History-tab empty-when-cold → addressed in 38-02/38-04.
- Locked design decisions for later slices recorded in 38-01-PLAN ("LOCKED palette" section):
  light theme, solid-purple buttons, accent=AI-only, Team roster = labeled table, Dashboard
  needs-attention = 2-col summary cards, pillar icons, client-derived overall/weakest.
