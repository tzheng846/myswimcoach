---
phase: 18-design-refresh
plan: 02
subsystem: ios-ux
tags: [ios, react-native, design, history-cards, report-card]

requires: [18-01]
provides:
  - SessionHistoryScreen: 3-col session cards (RATE/SPEED/DIST); stroke badge always visible with abbreviations
  - ReportCardScreen: SESSION summary card (LAP TIME / RATE / SPEED) as first content block
affects: [iOS EAS build needed to ship]

key-files:
  modified:
    - swimnetics-mobile/src/screens/SessionHistoryScreen.js
    - swimnetics-mobile/src/screens/ReportCardScreen.js

duration: ~10min
started: 2026-06-09T00:00:00Z
completed: 2026-06-09T00:00:00Z
---

# Phase 18 Plan 02: Design Refresh — History + Report

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~10 min |
| Tasks | 2 completed |
| Files modified | 2 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: History card 3-col + always-visible stroke badge | Pass | STROKE_ABBR map; Strokes column removed; badge shown for all stroke types |
| AC-2: Report SESSION summary card at top | Pass | SessionSummaryCard component inserted before analytics section; respects unit toggle |

## Files Modified

| File | Changes |
|------|---------|
| `SessionHistoryScreen.js` | Added `STROKE_ABBR` map; removed Strokes column from StatItem row; updated labels to uppercase RATE/SPEED/DIST; stroke badge now always shown using abbr, not conditional on non-breaststroke |
| `ReportCardScreen.js` | Added `SessionSummaryCard` component + `ssc` StyleSheet above main export; inserted `<SessionSummaryCard>` as first item in ScrollView content |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Remove Strokes column (was 4th column) | Design shows 3 columns only; Strokes is accessible in the full report anyway |
| Always show stroke badge | Design shows it on all cards; previously hidden for breaststroke (the default) |
| LAP TIME mm:ss format for sessions ≥60s | Lap times over a minute are more readable in clock format (1:23 vs 83.0) |

## Phase 18 Complete

All 4 design changes delivered:
- ✅ Login: wave SVG logo + VELOCITY INTELLIGENCE tagline
- ✅ Athletes: letter avatar circles + simplified card
- ✅ History: 3-col RATE/SPEED/DIST cards + abbreviated stroke badges
- ✅ Report: SESSION summary card at top

EAS build needed to ship Phases 14/15/17/18 iOS changes.
