---
phase: 75-report-card-phase-model
plan: 04
subsystem: metrics
tags: [phase-metrics, start-phase, glide, reaction-time, fastapi, jsonb]

requires:
  - phase: 75-02
    provides: detect_underwater_start (end-of-glide boundary) + _window/_span_distance helpers
  - phase: 79
    provides: detect_dive_start (foot-of-surge) — opens the Start window
provides:
  - 10 implemented Start-phase metrics in phase_metrics.REGISTRY
  - PUT /sessions/{id}/go-signal endpoint (GO time in metrics_json, jsonb)
  - _rebuild_phases shared recompute helper (reads stored go_signal_s)
affects: [75-step3-ui, ios-report-card]

tech-stack:
  added: []
  patterns:
    - "Start metrics = reductions over [dive_start,underwater_start] + glide sub-slice [peak,underwater_start]"
    - "GO signal input persisted in metrics_json (jsonb, no migration); endpoint mutates then recomputes"

key-files:
  created: []
  modified: [phase_metrics.py, api.py, tests/test_phase_metrics.py, tests/test_recompute.py, PIPELINE.md]

key-decisions:
  - "Waived D12 one-at-a-time gate for the Start batch (user, 2026-08-21) — 10 share 3 helpers"
  - "reaction_time first-movement = detect_phases motion onset (the jump), NOT dive_start (skips the jump)"
  - "go_signal_s in metrics_json jsonb, not a new column — no migration"
  - "glide window = velocity-peak → underwater_start, no min-duration floor"
  - "streamline_drag stays planned (nonlinear fit + tether confound)"

patterns-established:
  - "Registry tiers are frozen-at-taxonomy metadata; a metric can be implemented while still tagged 'high'"

duration: ~40min
started: 2026-08-21
completed: 2026-08-21
---

# Phase 75 Plan 04: Start-Phase Metrics Summary

**10 of 11 Start metrics implemented in one pass (peak/time-to-peak/max-accel, dive duration, four glide metrics, break-into-kick velocity, reaction time) + a `PUT /sessions/{id}/go-signal` endpoint that stores the GO time in `metrics_json` and recomputes so `reaction_time` derives. `streamline_drag` deferred.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~40 min |
| Completed | 2026-08-21 |
| Tasks | 3 completed |
| Files modified | 5 |
| Suite | 443 passed (was 426; +17 new) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: ten Start metrics compute over a known trace; streamline_drag stays planned | Pass | `TestStartMetrics.test_values_are_window_and_glide_arithmetic` checks each against hand-computed values; `test_ten_specs_report_implemented_streamline_planned` |
| AC-2: reaction_time derives only from a stored GO time (set/clear via endpoint, jsonb) | Pass | `TestReactionTime` (unit) + `TestSetGoSignal` (endpoint set/clear/persist); reaction_time = onset − go, `None` without a GO |
| AC-3: no regression; every fn degrades to None, never raises | Pass | Full suite green; degradation cases (missing dive_start, empty accel, window<floor, boundary past trace, degenerate ctx) all covered |

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `phase_metrics.py` | Modified | 3 helpers (`_start_window`, `_start_peak`, `_glide_window`) + 10 `_compute_*` fns; flipped 10 Start specs to `implemented` |
| `api.py` | Modified | Refactored `recompute_phases` → shared `_rebuild_phases` (reads stored `go_signal_s`); added `PUT /sessions/{id}/go-signal` |
| `tests/test_phase_metrics.py` | Modified | `TestStartMetrics` + `TestReactionTime`; fixed the stale `reaction_time` planned-status test |
| `tests/test_recompute.py` | Modified | `TestSetGoSignal` — set/clear/persist/validation (422 negative, non-numeric, missing field) |
| `PIPELINE.md` | Modified | §6 registry table (Start 10 implemented / 1 planned) + Start-metric & reaction_time notes |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Waived D12 one-at-a-time gate for this batch | The 10 share 3 window helpers; splitting would be ceremony | Whole Start phase computes at once |
| reaction anchor = motion onset, not dive_start | Phase 79's dive_start deliberately skips the jump-and-sink; using it would undercount reaction time | `reaction_time` uses `detect_phases` baseline_end |
| `go_signal_s` in `metrics_json` jsonb | No migration (D15 doctrine); `compute_phases` already echoes it | No schema change; survives recompute |
| glide window = peak → underwater_start, no floor | User definition; short glides are real signal | glide_* compute even for brief glides |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Essential — a pre-existing test asserted the old `reaction_time` status |
| Scope additions | 0 | — |
| Deferred | 0 | — |

**Total impact:** None beyond plan. The one auto-fix was updating `test_reaction_time_entry_value_none_status_planned` → `_implemented_but_none_without_go`, since 75-04 flips the spec from planned to implemented (the test would otherwise fail correctly).

## Key finding — the registry tiers are stale

The taxonomy tiered `glide_*` and `break_into_kick_vel` as **high** on 2026-08-19, when there was "no reliable entry→first-kick window." Phases 75-02 (`underwater_start` = end of glide) and 79 (`dive_start` = start of window) shipped that window afterward, so these are now cheap reductions. Left the `tier` field unchanged (it is frozen-at-taxonomy metadata, not implementation effort); flagged here and in PIPELINE.

## Issues Encountered

None.

## Next Phase Readiness

**Ready:**
- Start section now has data for the Step-3 report-card UI (9 metrics on process/recompute; reaction_time once a GO time is set).
- `_rebuild_phases` is the shared seam for the remaining Swim (9) + Whole (4) metric batches.

**Concerns / owed:**
- ⚠ **User-run backfill owed:** `python tools/backfill_phases.py --apply` to populate the 9 non-reaction Start metrics across the stored library (standing pattern 57/59-03/61-01/65/79). Not in this diff.
- Display-only: no absolute-value ground truth for glide/start metrics (D7 — within-athlete contrast only).
- `reaction_time` end-to-end UAT needs a real session with a GO time (deferred to the GO-button UI, Step 3).
- `streamline_drag` still planned.

**Blockers:** None.

---
*Phase: 75-report-card-phase-model, Plan: 04*
*Completed: 2026-08-21*
