---
phase: 18-design-refresh
plan: 01
subsystem: ios-ux
tags: [ios, react-native, design, branding, avatars]

requires: []
provides:
  - LoginScreen: wave SVG logo + VELOCITY INTELLIGENCE amber tagline
  - AthletesScreen: letter avatar circles; Edit offset button removed from card face
affects: [iOS EAS build needed to ship]

tech-stack:
  patterns:
    - "react-native-svg Svg/Path used for decorative logo — already a project dep via VelocityChart"
    - "Deterministic avatar color: charCodeAt(0) mod palette length — no randomness, stable across re-renders"
    - "alignItems: center on KAV inner view requires width: 100% on inputs/button to prevent shrinkage"

key-files:
  modified:
    - swimnetics-mobile/src/screens/LoginScreen.js
    - swimnetics-mobile/src/screens/AthletesScreen.js

duration: ~10min
started: 2026-06-09T00:00:00Z
completed: 2026-06-09T00:00:00Z
---

# Phase 18 Plan 01: Design Refresh — Login + Athletes

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~10 min |
| Tasks | 2 completed |
| Files modified | 2 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Login wave logo | Pass | Svg/Path wave above SWIMNETICS; VELOCITY INTELLIGENCE in #F59E0B |
| AC-2: Letter avatars on athlete cards | Pass | 40×40 circle with deterministic color + initial letter |
| AC-3: Edit offset removed from card face | Pass | editOffsetBtn JSX removed; logic retained; History › kept |

## Files Modified

| File | Changes |
|------|---------|
| `LoginScreen.js` | Added `Svg, Path` import; replaced title+subtitle with wave SVG + SWIMNETICS + VELOCITY INTELLIGENCE tagline; `alignItems: center` on inner; `width: 100%` on input/button |
| `AthletesScreen.js` | Added `avatarColor()` helper + `AVATAR_COLORS` palette; added avatar View to card; removed editOffsetBtn JSX; removed Edit offset inline editor from renderAthlete; sectionLabel → "ATHLETES" |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Keep `handleEditHW` + `editingId` state in component | Logic is correct, just the UI trigger was removed. Head-waist editing can be re-exposed via a different UX (e.g., athlete settings screen) without touching the save logic |
| `width: 100%` on input/button | Required when parent has `alignItems: center` — otherwise RN shrinks them to content width |

## Next Phase Readiness

Plan 18-02 ready: SessionHistoryScreen 3-col cards + ReportCardScreen SESSION summary card.
