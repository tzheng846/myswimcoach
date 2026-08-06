---
phase: 02-metric-explanations
plan: 01
subsystem: ui
tags: [streamlit, metrics, coaching, thresholds]

requires: []
provides:
  - _METRIC_RANGES dict with breaststroke thresholds for all 6 session metrics
  - _rate_metric() function returning Good/OK/Needs work rating with hex color
  - Colored rating badges (● Good/OK/Needs work) under each metric card
  - Enhanced help tooltips with numeric range text

affects: [any future metric additions, coach chat context]

tech-stack:
  added: []
  patterns:
    - "_METRIC_RANGES as single source of truth for all metric thresholds"
    - "_rate_metric(key, value) → (label, color) for any session metric"
    - "st.markdown with unsafe_allow_html for colored inline badges"

key-files:
  modified: [app.py]

key-decisions:
  - "Thresholds consolidated in _METRIC_RANGES — not duplicated in help strings or _compute_verdicts"
  - "Rating shown as colored ● dot + text below st.metric, not as delta parameter"
  - "mean_coast_fraction stored as 0–1 fraction; lambda operates on that scale"

patterns-established:
  - "To add a new ratable metric: add entry to _METRIC_RANGES with good/ok/ranges keys"

duration: ~15min
started: 2026-05-17T00:00:00Z
completed: 2026-05-17T00:00:00Z
---

# Phase 2 Plan 01: Metric Explanations Summary

**Colored Good/OK/Needs work rating badges added under all 6 metric cards, backed by a consolidated _METRIC_RANGES threshold table with breaststroke-specific ranges.**

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Ratings visible on all 6 cards | Pass | ● badge renders in both Simple (3 cards) and Advanced (6 cards) |
| AC-2: Single source of truth | Pass | _METRIC_RANGES is the only place thresholds live |
| AC-3: Help tooltip includes numeric ranges | Pass | ranges text appended automatically from _METRIC_RANGES |

## Accomplishments

- `_METRIC_RANGES` dict defines good/ok lambdas + ranges text for all 6 session metrics
- `_rate_metric(key, value)` returns `(label, hex_color)` — 9/9 unit tests pass
- `_build_stats_table` rewritten to use session key + format_fn pattern; ratings rendered as colored `st.markdown` below each `st.metric`

## Files Modified

| File | Change |
|------|--------|
| `app.py` | Added _METRIC_RANGES, _rate_metric(); rewrote _build_stats_table |

## Deviations from Plan

None — executed exactly as written.

## Next Phase Readiness

**Ready:**
- Any new metric can be rated by adding an entry to `_METRIC_RANGES`
- `_rate_metric` is importable and unit-testable independently

**Concerns:**
- Thresholds are fixed for recreational/intermediate breaststroke — may need swimmer-level calibration later
- `_compute_verdicts` still has its own fatigue/pacing thresholds (not yet unified with _METRIC_RANGES)

**Blockers:** None
