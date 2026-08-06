# 39-04 SUMMARY — Record tab button redesign (DU6)

**Status:** Code-complete; device verify DEFERRED. iOS export green (3.2MB). Build-free (no new dep —
solid lavender pill, no expo-blur). Design confirmed via mock + AskUserQuestion (2026-06-19).

## What shipped
- `src/components/ui/TabBar.js` — rewritten to the iOS-News+ reference layout:
  - **Frosted lavender pill** (`surfaceAlt` + border + card shadow, `radii.pill`) holding the three
    grouped tabs Dashboard / Team / History (filtered from `state.routes`, excluding the Record route).
  - **Detached circular Record button** on the right (60px `primary` circle + white record dot +
    island shadow), no label (per user choice).
  - Outer bar transparent; bottom-tabs still reserves the bar height so screen content doesn't underlap.
  - Tab press logic unchanged (emits tabPress, navigates) — RootTabs nav structure untouched.

## Decisions (user, 2026-06-19)
- Record button = purple, no label. Pill = solid lavender (no true blur → no expo-blur native dep).

## Known minor (note for polish)
- On Dashboard/ReportCard the floating AiBubble (bottom-right) now sits vertically above the detached
  Record circle (also bottom-right) — two purple circles stack. Not broken; nudge the bubble left in a
  later polish if it reads cluttered on device.

## Verified at code level
- export green; pill renders Dashboard/Team/History, Record detached; navigation unchanged.
