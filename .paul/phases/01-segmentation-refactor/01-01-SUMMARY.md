---
phase: 01-segmentation-refactor
plan: 01
subsystem: pipeline
tags: [segmentation, trough-detection, metrics, streamlit]

requires: []
provides:
  - Trough-only stroke segmentation trimmed to swim window
  - Auto-detected baseline_end and swim_end in detect_phases
  - Clean segmentation / metrics split in metrics.py
  - Color-coded stroke visualization with hover labels in app.py

affects: [metrics, app, any future pipeline changes]

tech-stack:
  added: []
  patterns:
    - "detect_phases returns both baseline_end and swim_end"
    - "segment_cycles_trough operates on trimmed [baseline_end:swim_end] slice; indices offset back to full array"
    - "SPM derived from mean steady-cycle duration, not FFT"
    - "Stroke vrects colored by _STROKE_PALETTE cycling; hover shows absolute stroke number"

key-files:
  modified: [metrics.py, app.py]

key-decisions:
  - "Trough-only segmentation: peak-anchored and template methods deleted entirely"
  - "swim_end uses last-sample-above-threshold + 0.5s grace (not sustained window) to include final glide"
  - "Stroke boundaries: prepend 0 AND append len(vel) to trough list — captures first and last strokes"
  - "SPM from mean cycle duration; FFT and freq_info removed"
  - "Triangles removed; stroke regions shown as colored vrects with invisible hover scatter"

patterns-established:
  - "segment_cycles_trough always receives trimmed vel_swim; all returned indices offset by b_end before use"

duration: ~60min
started: 2026-05-17T00:00:00Z
completed: 2026-05-17T00:00:00Z
---

# Phase 1 Plan 01: Segmentation Refactor Summary

**Trough-only stroke segmentation with auto-trimmed swim window, dead code removed, and color-coded stroke visualization replacing triangle markers.**

## Performance

| Metric | Value |
|--------|-------|
| Tasks | 3 planned + 4 post-apply fixes |
| Files modified | 2 (metrics.py, app.py) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: No baseline false detections | Pass | segmentation now starts at baseline_end |
| AC-2: No post-swim false detections | Pass | swim_end trims post-swim; last-sample+grace fix ensures final stroke included |
| AC-3: SPM from cycle durations | Pass | 60 / mean(duration) replaces FFT |
| AC-4: Dead code removed | Pass | estimate_cycle_frequency, segment_cycles, _rolling_rms, segment_cycles_template all deleted |
| AC-5: seg_method removed from app.py | Pass | No occurrences remain; Segmentation settings expander deleted |

## Accomplishments

- `detect_phases` now returns `swim_end` (last above-threshold sample + 0.5s grace) in addition to `baseline_end`
- `compute_session_metrics` trims to `[baseline_end:swim_end]` before segmenting; all indices offset back to full-array coordinates
- Four dead functions (~200 lines) deleted; `scipy.fft` import removed
- `app.py` fully decoupled from `seg_method`; segmentation settings expander gone
- Stroke visualization replaced: triangle markers → color-coded vrects with invisible hover scatter showing absolute stroke number

## Deviations from Plan

### Scope additions (post-APPLY, user-requested)

**1. First stroke was missing**
- Issue: `segment_cycles_trough` only iterated `range(len(troughs)-1)`, so no left boundary for the first stroke
- Fix: prepend `0` to bounds array
- Files: `metrics.py` — `segment_cycles_trough`

**2. Last stroke was missing**
- Issue: no right boundary after the final trough — last stroke never created
- Fix: append `len(vel)` to bounds array
- Files: `metrics.py` — `segment_cycles_trough`

**3. swim_end cut off last stroke**
- Issue: sustained-window scan (required 0.5s above threshold) failed at the final glide
- Fix: scan for last individual sample above threshold + 0.5s grace
- Files: `metrics.py` — `detect_phases`

**4. Triangle markers replaced with color-coded stroke regions**
- User requested: remove triangles; add alternating palette vrects; hover shows stroke number
- Added `_STROKE_PALETTE`, vrect rendering, invisible hover scatter in `_build_vel_chart`
- Added `t_start_s`/`t_end_s` to cycle dicts in `load_and_compute`
- Removed `show_labels` parameter from `_build_vel_chart` and all call sites
- Removed `_cycle_color` helper function (unused after change)
- Files: `app.py`

## Files Modified

| File | Change |
|------|--------|
| `metrics.py` | detect_phases extended; 4 functions deleted; compute_session_metrics refactored; segment_cycles_trough boundary fix |
| `app.py` | seg_method removed; expander deleted; vrect coloring + hover added; show_labels removed |

## Next Phase Readiness

**Ready:**
- Segmentation is clean, well-bounded, and correct for all tested sessions
- metrics.py has clear SEGMENTATION / METRICS section headers
- app.py has no dead seg_method state

**Concerns:**
- Kick detection metrics (pct_cycles_with_kick, mean_arm_kick_ratio) remain unreliable due to the 2.5 Hz LP filter merging arm+kick peaks — documented in CLAUDE.md, deferred
- swim_end grace period (0.5s) is a fixed heuristic; may need tuning for very slow swimmers

**Blockers:** None
