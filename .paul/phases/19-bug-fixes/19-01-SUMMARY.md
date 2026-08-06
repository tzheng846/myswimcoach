---
phase: 19-bug-fixes
plan: 01
subsystem: ios-ux
tags: [ios, react-native, swipe, dark-theme, navigation]

requires: []
provides:
  - SessionHistoryScreen: pill-shaped filter chips; swipe snaps fully open + tap-to-close; star reflects on return from ReportCard; red action button clipped to card corners
  - ReportCardScreen: full dark theme (#000 bg, #1a1a1a cards, #fff metric values)
affects: [iOS EAS build needed to ship]

key-files:
  modified:
    - swimnetics-mobile/src/screens/SessionHistoryScreen.js
    - swimnetics-mobile/src/screens/ReportCardScreen.js

key-decisions:
  - "focus listener for star sync: navigation.addListener('focus', fetchSessions) — refetches on every back-navigation, simplest correct approach"
  - "borderRadius on sr.wrap clips action buttons: overflow:hidden already present, adding borderRadius:10 is all that's needed"

duration: ~15min
started: 2026-06-09T00:00:00Z
completed: 2026-06-09T00:00:00Z
---

# Phase 19 Plan 01: iOS Bug Fixes

**Pill chips, working swipe, dark ReportCard, and two scope additions: star sync + action button clipping.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~15 min |
| Tasks | 2 planned + 2 scope additions |
| Files modified | 2 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Chips consistent pill shape | Pass | height:34, borderRadius:17, justifyContent:'center'; filterRow alignItems:'center' |
| AC-2: Swipe opens fully + tap-to-close | Pass | terminate uses threshold; release has tap guard (|dx|<5 + |dy|<5 → close) |
| AC-3: ReportCardScreen dark theme | Pass | container #000, sectionCard #1a1a1a, metricValue #fff, buttons #252525→#2563EB active |

## Files Modified

| File | Changes |
|------|---------|
| `SessionHistoryScreen.js` | Chip: height:34/borderRadius:17; filterRow: alignItems:center; swipe terminate threshold; swipe tap guard; focus refetch; sr.wrap borderRadius:10 |
| `ReportCardScreen.js` | Full st StyleSheet dark-themed; placeholderTextColor #555 |

## Deviations from Plan

### Scope Additions (2)

**1. Star sync on back-navigation**
- **Found during:** Post-apply review (user reported)
- **Issue:** `isStarred` toggled in ReportCardScreen PATCHes the backend but SessionHistoryScreen never refetches — stale star shown when navigating back
- **Fix:** `navigation.addListener('focus', fetchSessions)` in SessionHistoryScreen
- **Files:** SessionHistoryScreen.js

**2. Red action button leaks past card corners**
- **Found during:** Post-apply review (user reported)
- **Issue:** Absolute-positioned red delete button shows through transparent rounded corners of the card (borderRadius:10 on card, but sr.wrap had no radius)
- **Fix:** Added `borderRadius: 10` to `sr.wrap` — `overflow: 'hidden'` already present clips the buttons
- **Files:** SessionHistoryScreen.js

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| focus listener for star sync | Simplest correct approach; no need to thread callbacks through nav params | SessionHistory always fresh after any ReportCard visit |
| borderRadius on sr.wrap clips actions | overflow:hidden already on wrap; borderRadius alone is the one missing piece | No layout changes needed |
| Keep red delete button | User confirmed: fix the visual leak, keep the button | swipe-left still has star + delete |

## Next Phase Readiness

**Ready:**
- Phase 19 complete — EAS build can now ship Phases 14/15/17/18/19 changes
- Phase 16 (Freestyle Support — wavelet/CWT segmentation) is the next feature phase

**Blockers:** None
