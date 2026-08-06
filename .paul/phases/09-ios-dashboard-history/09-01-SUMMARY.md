---
phase: 09-ios-dashboard-history
plan: 01
subsystem: ios
tags: [react-native, expo, supabase, session-history, report-card, dashboard]

requires:
  - phase: 08-01
    provides: sessions table with metrics_json, velocity_profile, distance_profile; athlete_id linked

provides:
  - Session history list per athlete (SessionHistoryScreen)
  - Historical report card from stored session data (ReportCardScreen)
  - Last-session summary on athlete cards (AthletesScreen)
  - Debug panel removed from RecordScreen

affects: v0.3 (QR device registration, billing — builds on same navigation structure)

tech-stack:
  added: []
  patterns:
    - "Read sessions from Supabase anon client using athlete_id filter + created_at DESC"
    - "Reconstruct time array from velocity_profile length: Array.from({length: vel.length}, (_, i) => i / 100)"
    - "Duplicate VelocityChart/MetricItem/TimeToX into ReportCardScreen — no shared component file for demo"

key-files:
  created:
    - swimnetics-mobile/src/screens/SessionHistoryScreen.js
    - swimnetics-mobile/src/screens/ReportCardScreen.js
  modified:
    - swimnetics-mobile/App.js
    - swimnetics-mobile/src/screens/AthletesScreen.js
    - swimnetics-mobile/src/screens/RecordScreen.js

key-decisions:
  - "Duplicate components in ReportCardScreen rather than extract shared file — avoids structural risk before demo"
  - "History + Edit offset buttons both shown at card bottom — consistent card footer pattern"
  - "Time array reconstructed at exactly 100 Hz (i / 100) — matches actual_fs from backend decimation"

patterns-established:
  - "Sessions query: .from('sessions').select(...).eq('athlete_id', id).order('created_at', {ascending: false})"
  - "last-session map: build from full sessions query with first-wins dedup keyed by athlete_id"

duration: 1 session (2026-05-24)
started: 2026-05-24T00:00:00Z
completed: 2026-05-24T00:00:00Z
---

# Phase 9 Plan 01: iOS Dashboard + History Summary

**Session history, historical report card, and athlete last-session summary shipped — full coach demo flow complete.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | 1 session (2026-05-24) |
| Tasks | 3 auto + 1 human-verify |
| Files created | 2 |
| Files modified | 3 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Last session shown on athlete cards | **Pass** | Date + SPM or "No sessions yet" |
| AC-2: Session history list per athlete | **Pass** | Newest-first, 4 stats per row |
| AC-3: Historical report card | **Pass** | Full metrics + velocity chart + Time-to-X from stored data |
| AC-4: Debug log panel removed | **Pass** | `debugLog` state, `debugScrollRef`, `runSelfTests`, self-test effect, panel JSX, and 8 debug styles all removed |

## Accomplishments

- Coach can now tap any athlete → History → tap a session → full report card with velocity chart
- Last session date + SPM visible at a glance on every athlete card without tapping
- Recording flow cleaned up: debug panel gone, `log()` is console-only

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `swimnetics-mobile/App.js` | Modified | Added `SessionHistory` and `ReportCard` stack routes |
| `swimnetics-mobile/src/screens/AthletesScreen.js` | Modified | `lastSessions` state, sessions query post-fetch, last-session text + "History ›" button on cards |
| `swimnetics-mobile/src/screens/SessionHistoryScreen.js` | Created | Dark-theme session list per athlete, 4 stats per row, taps to ReportCard |
| `swimnetics-mobile/src/screens/ReportCardScreen.js` | Created | Light-theme report card from stored session; duplicates MetricItem, VelocityChart, TimeToX |
| `swimnetics-mobile/src/screens/RecordScreen.js` | Modified | Removed debug panel, debugLog state, debugScrollRef, runSelfTests, self-test useEffect, debug styles |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Duplicate MetricItem/VelocityChart/TimeToX in ReportCardScreen | Avoids creating shared component structure under demo time pressure | Minor code duplication; extract to shared in v0.3 |
| History + Edit offset as separate card footer buttons | Consistent with existing "Edit offset" footer pattern | Clean card layout, no ambiguity |
| Time array: `i / 100` | velocity_profile stored at 100 Hz (actual_fs after decimation) | Accurate time axis in report card |

## Deviations from Plan

None — plan executed exactly as written.

## Next Phase Readiness

**Ready:**
- v0.2 Coach Demo milestone complete: record → results → history → report card, full flow on iOS
- sessions table structure stable; v0.3 phases can build on it

**Concerns:**
- Sessions RLS policy uses `coach_id` — sessions with null `coach_id` may not appear in history (pre-existing issue from Phase 8)
- Shared components (VelocityChart etc.) are duplicated across RecordScreen and ReportCardScreen — extract to `src/components/` in v0.3

**Blockers:**
- None

---
*Phase: 09-ios-dashboard-history, Plan: 01*
*Completed: 2026-05-24*
