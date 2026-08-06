---
phase: 17-ux-polish
plan: 01
subsystem: ios-ux
tags: [ios, react-native, gesture, keyboard, ux]

requires: []
provides:
  - SessionHistoryScreen: dynamic stroke filter chips (present strokes only)
  - SessionHistoryScreen: swipe row snaps on gesture interruption
  - VelocityChart: horizontal-only gesture claim; scroll/chart conflict resolved
  - ReportCardScreen: ScrollView locked during chart interaction
  - ReportCardScreen: keyboard avoidance for notes field
affects: [iOS EAS build needed to ship]

tech-stack:
  patterns:
    - "PanResponder onPanResponderTerminate: always add this when PanResponder is inside a ScrollView or FlatList"
    - "onStartShouldSetPanResponder: () => false + onMoveShouldSetPanResponder with direction check — correct pattern for interactive element inside ScrollView"
    - "Frozen PanResponder callbacks: always use ref pattern (ref.current?.()) for any callback that may change across renders"
    - "KeyboardAvoidingView wraps ScrollView (not SafeAreaView) — header stays fixed, only scrollable content adjusts"

key-files:
  modified:
    - swimnetics-mobile/src/screens/SessionHistoryScreen.js
    - swimnetics-mobile/src/components/VelocityChart.js
    - swimnetics-mobile/src/screens/ReportCardScreen.js

duration: ~20min
started: 2026-06-09T00:00:00Z
completed: 2026-06-09T00:00:00Z
---

# Phase 17 Plan 01: UX Polish Summary

**Four confirmed UX bugs fixed across three files: dynamic filter chips, swipe snap, velocity chart scroll conflict, and keyboard-covered notes.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~20 min |
| Tasks | 2 completed |
| Files modified | 3 |
| Tests | N/A (iOS-only changes; no backend tests affected) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Filter chips show only present strokes | Pass | useMemo derives chip list from sessions state |
| AC-2: Chip touch targets ≥ 44pt | Pass | paddingVertical 6→10, paddingHorizontal 12→14 |
| AC-3: Swipe row snaps on gesture interruption | Pass | onPanResponderTerminate snaps to open/closed |
| AC-4: Chart scrub does not trigger page scroll | Pass | onStartShouldSetPanResponder→false; onMoveShouldSetPanResponder checks direction; scrollEnabled toggled |
| AC-5: Notes keyboard avoidance | Pass | KeyboardAvoidingView + scrollToEnd on focus |
| AC-6: Pinch-to-zoom and pan still work | Pass | onMoveShouldSetPanResponder allows touches.length >= 2 (pinch) |

## Files Modified

| File | Changes |
|------|---------|
| `SessionHistoryScreen.js` | useMemo import; presentStrokeKeys + visibleStrokes derived from sessions; auto-reset filter effect; data={visibleStrokes}; chip padding fix; onPanResponderTerminate |
| `VelocityChart.js` | onInteractionStart/End props + refs; onStartShouldSetPanResponder→false; onMoveShouldSetPanResponder direction check; onInteractionStartRef.current?.() in grant; onInteractionEndRef.current?.() in release + terminate; onPanResponderTerminate added |
| `ReportCardScreen.js` | useRef, KeyboardAvoidingView, Platform imports; scrollViewRef + scrollEnabled state; KAV wraps ScrollView; scrollEnabled + ref on ScrollView; onInteractionStart/End to VelocityChart; onFocus scrollToEnd on notes TextInput |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `onStartShouldSetPanResponder: () => false` | Returning true here beats ScrollView in bubble phase but can cause taps to be swallowed; false + move-phase claim is the correct pattern for nested interactive elements |
| `onMoveShouldSetPanResponder` checks `touches.length >= 2` first | Pinch gesture has near-equal dx/dy so the dx>dy check alone would miss it |
| KAV wraps ScrollView only (not full SafeAreaView) | Header/date/name are fixed; only the scrollable body should adjust for keyboard |
| `scrollToEnd` on notes focus | Notes is the last element in the ScrollView; scrollToEnd is correct and simpler than computing the notes field's exact scroll offset |

## Deviations from Plan

None.

## Next Phase Readiness

**EAS build needed** to ship all three screens to device (Phases 14-15-17 iOS changes all pending since last build).

Phase 16 (Freestyle Support) and further phases remain unblocked.

---
*Phase: 17-ux-polish, Plan: 01*
*Completed: 2026-06-09*
