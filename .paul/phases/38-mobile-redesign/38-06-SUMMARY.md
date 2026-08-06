# 38-06 SUMMARY — Record flow restyle + units wiring + Devices/Diagnostics (FINAL plan)

**Status:** Code-complete; device verification DEFERRED (38-TEST-PLAN.md). `npx expo export
--platform ios` exits 0 (3.2MB). No new native dep. **Phase 38 is now code-complete (6/6).**

## What shipped (swimnetics-mobile)
- `components/VelocityChart.js` — now **theme-aware**: `dark` prop + `CHART_COLORS` light/dark sets;
  light on ReportCard/VideoOverlay, dark (cyan line) on the active record screen. Tokens throughout.
- **Finding A (units) resolved** — `ReportCardScreen` + `RecordScreen` read the global m/yd
  `UnitsContext` (derive `imperial` when pref `yd`; in-screen toggles call `setUnitPref`; local
  `useState` retired). Settings ↔ screens no longer diverge.
- `RecordingConfigScreen.js` — rewritten to light + **athlete picker** (seeded from route params
  when launched from an athlete; supabase pick-from-list when cold from the Record island; sets
  default stroke; Start gated on athlete + connected). BLE/device logic unchanged.
- `RecordScreen.js` — **dark/immersive** restyle (bg = brand `text` purple; white metric cards
  float; light text on bg; cyan VelocityChart via `dark`; stop=needsWork; primary buttons). Inline
  spinner/status colors mapped to tokens + new `dangerOnDark`. **BLE/camera logic untouched** —
  StyleSheet/color-only.
- `VideoOverlayScreen.js` — restyled to light tokens (video element keeps `#000` letterbox).
- **Finding B** — `DevicesScreen.js` + `DiagnosticsScreen.js` restyled to light tokens; Diagnostics
  verdict colors (NOT DETECTED / Too weak-strong / Detected) mapped to needsWork/ok/good.
- `theme/tokens.js` — added `dangerOnDark` (#ff8a8a) for the dark record screen.

## Deviations / follow-ups
- Status bar on the dark record screen: App.js sets `StatusBar dark` globally; icons may be low-
  contrast on the dark screen. Flagged in 38-TEST-PLAN — a per-screen `StatusBar light` is a small
  follow-up if device verification shows it.
- VideoOverlay readout is fixed "m/s" (niche screen; not wired to UnitsContext) — acceptable.

## Verified at code level
- export green; touched files use tokens only (legit exceptions: `#000` video letterbox; `rgba()`
  translucents on the dark screen). VelocityChart dark/light verified by prop. No logic changes to
  BLE/camera/recording.

## Phase 38 status
ALL 6 plans code-complete (38-01…38-06), each export-green. Cross-plan review clean (nav/tokens/
  contracts); Findings A + B resolved here. Device verification batched → ONE end-of-phase EAS build
  (must include `expo-crypto`); full checklist in 38-TEST-PLAN.md.
