---
phase: 39-redesign-fixes
plan: 05
subsystem: ui
tags: [react-native, svg, velocity-chart, segmentation, breaststroke]

requires:
  - phase: 16-freestyle-support
    provides: segment_cycles_wavelet cycle dicts (start_idx/end_idx) in metrics_json.cycles
  - phase: 38-mobile-redesign
    provides: theme-aware VelocityChart (dark prop + CHART_COLORS), light ReportCardScreen
provides:
  - VelocityChart cycleBoundaries overlay (faint dashed zoom-aware vertical lines under the trace)
  - ReportCardScreen Advanced-view segmentation overlay + experimental caption
affects: [39-06, future iOS-parity, 16-06 wavelet tuning]

tech-stack:
  added: []
  patterns:
    - "Chart annotations passed in as prop arrays (times in seconds), drawn under the trace, zoom-filtered by tMin/tMax"

key-files:
  created: []
  modified:
    - swimnetics-mobile/src/components/VelocityChart.js
    - swimnetics-mobile/src/screens/ReportCardScreen.js

key-decisions:
  - "Dashed boundary LINES (not shaded regions) — least clutter vs trace+cursor+marker; matches 'see what the segmenter sees'"
  - "Overlay gated to ReportCard Advanced view only; RecordScreen parity left as a noted follow-up (fragile ~950-line file)"

patterns-established:
  - "Overlay opt-in by passing [] when not wanted (Simple view) rather than a separate boolean flag"

duration: ~10min
started: 2026-06-20T00:00:00Z
completed: 2026-06-20T00:10:00Z
---

# Phase 39 Plan 05: Segmentation Overlay (DU7) Summary

**The session velocity chart now draws the wavelet segmenter's per-stroke cycle boundaries as faint dashed zoom-aware vertical lines in the Advanced view, with an honest "segmentation is experimental" caption.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~10 min |
| Tasks | 2 completed |
| Files modified | 2 (mobile repo) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Boundaries render in Advanced view | Pass (code) | Dashed lines drawn between zero-line and Polyline (under trace); caption present. Device check deferred. |
| AC-2: No overlay in Simple view / no-cycle sessions | Pass | `cycleBoundaries = []` when `view !== 'advanced'`; caption guarded by `.length > 0`; empty cycles → empty array. |
| AC-3: Overlay respects zoom | Pass (code) | `bt < tMin || bt > tMax` filter reuses live zoom window; `px(bt)` reuses the existing scale. |

## Accomplishments

- `VelocityChart.js`: new `cycleBoundaries` prop (default `[]`); `cycle` color added to both light
  (`colors.periwinkle`) and dark (`rgba(255,255,255,0.35)`) `CHART_COLORS`; dashed lines
  (`strokeDasharray="3,3"`, opacity 0.55) drawn immediately after the zero-line and before the
  `<Polyline>` so the trace stays on top. PanResponder / cursor / marker / zoom logic untouched.
- `ReportCardScreen.js`: `cycleBoundaries` computed from `metrics.cycles` `start_idx`/`end_idx ÷ 100`
  only when `view === 'advanced'`; passed to the chart; "Dashed lines = detected stroke cycles.
  Segmentation is experimental." caption + `chartCaption` style.
- Index-space correctness confirmed against the file's existing CSV-export reuse of the same indices
  plus `time = i/100`.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `swimnetics-mobile/src/components/VelocityChart.js` | Modified | `cycleBoundaries` prop + `cycle` color + dashed zoom-aware boundary lines under the trace |
| `swimnetics-mobile/src/screens/ReportCardScreen.js` | Modified | Advanced-only boundary computation + chart prop + experimental caption + style |

## Verification Results

- `npx expo export --platform ios` → exit 0 (1056 modules, 3.2 MB bundle).
- Self-review: Simple view + no-cycle sessions render no overlay/caption (AC-2); zoom filter present (AC-3).

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Dashed lines, not shaded regions | Least clutter against trace+cursor+marker; "see what the segmenter sees" | Shading remains an easy future swap |
| ReportCard Advanced only (not RecordScreen) | RecordScreen is the fragile ~950-line BLE/camera file; same component → trivial later opt-in | Logged as parity follow-up |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 0 | — |
| Deferred | 0 | Followed plan as written |

**Total impact:** None — plan executed exactly as specified.

## Issues Encountered

None.

## Next Phase Readiness

**Ready:**
- Overlay rides the single end-of-phase EAS build; device checks appended to 39-TEST-PLAN.md.
- Same `cycleBoundaries` prop is reusable for RecordScreen parity if/when wanted.

**Concerns:**
- Segmentation is placeholder quality (`segmentation_reliable=False` always) — the caption sets that
  expectation honestly; boundary accuracy improves with the future 16-06 wavelet tuning.

**Blockers:**
- None. Phase 39 remaining = 39-06 only (DU4 flag abnormal + ignore) — needs the abnormal-definition
  + ignore-persistence decision before planning.

---
*Phase: 39-redesign-fixes, Plan: 05*
*Completed: 2026-06-20*
