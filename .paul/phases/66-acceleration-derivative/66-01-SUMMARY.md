---
phase: 66-acceleration-derivative
plan: 01
subsystem: signal-processing
tags: [savitzky-golay, scipy, acceleration, backfill, per-stroke, fastapi]
requires:
  - phase: 64-video-velocity-overlay (plan 02)
    provides: sessions.acceleration_profile + acceleration_from_velocity + the backfill tool
provides:
  - Savitzky-Golay acceleration derivative at full rate (smooth + accurate, no facets)
  - stroke-dependent smoothing window (free/back wider than fly/breast)
  - backfill --recompute overwrite mode
affects: [65-underwater-phase-detection, any future segmentation that leans on acceleration]
tech-stack:
  added: []
  patterns: ["per-stroke dispatch for the accel window, mirroring SEGMENTER_BY_STROKE"]
key-files:
  created: []
  modified: [vel_acc_extraction.py, tests/test_metrics.py, tools/backfill_acceleration.py, api.py]
key-decisions:
  - "SG deriv=1 replaces decimate->grad->linear-interp; full rate, one pass"
  - "Window is stroke-dependent: free/back 0.50s, fly/breast 0.25s (user call at checkpoint)"
  - "Display-only: metrics.py never consumes acceleration; velocity untouched"
patterns-established:
  - "acceleration_from_velocity(vel, fs, stroke_type) — stroke picks the smoothing window"
duration: ~1 session, with a checkpoint-driven refinement
started: 2026-08-16
completed: 2026-08-16
---

# Phase 66 Plan 01: Savitzky–Golay Acceleration Derivative Summary

**Replaced the choppy ~5 Hz decimate→gradient→linear-interp acceleration with a full-rate
Savitzky–Golay first derivative, then made its smoothing window stroke-dependent (free/back 0.50 s,
fly/breast 0.25 s) so alternating-arm strokes stop looking noisy — all display-only, re-backfilled
across 70 rows.**

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: SG, smooth + full-rate | Pass* | *Metric reframed — see Deviations. SG tracks a clean sinusoid to **0.3% RMS** (old 118%) and preserves peaks; old crushed them 29% (synthetic) / **61%** (a real session) |
| AC-2: Exact on low-order signals | Pass | A linear velocity ramp → constant accel, `atol=1e-6` |
| AC-3: Pipeline + API inherit it; api test green | Pass | `run_pipeline`/`/process` route through the shared fn; `test_insert_carries_acceleration_profile` still passes |
| AC-4: Re-backfill overwrites existing | Pass | `--recompute` selects all 70 velocity-bearing rows; dry-run writes 0 |
| AC-5: Deployed + re-backfilled, verified | Pass | Railway deployed; 70/70 re-backfilled; stored == `acceleration_from_velocity(stored vel, fs, stroke)` exactly |

## Verification

- Suite **276 → 277** (rewrote the pinning test; +1 stroke-dependency test).
- Spot-check (real rows): stored accel == the SG derivation exactly. Freestyle stored TV **268** vs
  **740** at the 0.25 s window (~2.8× smoother); butterfly kept sharp at 0.25 s (TV 1003).
- Deploy: `120908f` then `ee1852c` pushed → Railway; re-backfill applied twice (uniform SG, then
  stroke-dependent) — 70 updated, 0 failed each time.

## Deviations from Plan

| Type | Item | Rationale |
|------|------|-----------|
| Metric correction | AC-1's "markedly lower total variation" was **wrong** | The old 5 Hz path is over-smoothed in frequency → *lower* TV yet visibly faceted. Replaced with accuracy-vs-analytic + peak-amplitude assertions, which is what "definition too low" actually means |
| Scope addition (checkpoint) | **Stroke-dependent window** (free/back 0.50 s, fly/breast 0.25 s) | User saw free was noisier than fly and asked for per-stroke resolution. Threaded `stroke_type` through `acceleration_from_velocity` + `run_pipeline` |
| Scope addition (file) | Edited **`api.py`** (not in `files_modified`) | `/process` must pass `stroke_type` to `run_pipeline` so new sessions get the right window — one-arg change |
| Process | Re-backfill ran **twice** | Once for uniform SG, once after the stroke-dependent window landed |

## Files Modified

| File | Change | Purpose |
|------|--------|---------|
| `vel_acc_extraction.py` | Modified | SG derivative + `_ACCEL_WINDOW_S` per-stroke map; `run_pipeline` gains `stroke_type` |
| `api.py` | Modified | `/process` passes `stroke_type` to `run_pipeline` |
| `tools/backfill_acceleration.py` | Modified | `--recompute` overwrite mode; selects + passes `stroke_type` |
| `tests/test_metrics.py` | Modified | Pinning test → accuracy/ramp/peak; +stroke-dependency test |

## Commits

| Commit | What |
|--------|------|
| `120908f` | SG derivative + rewritten test + `--recompute` |
| `ee1852c` | Stroke-dependent window + `stroke_type` plumbing + test |

## Next Phase Readiness

**Ready:** acceleration is smooth, accurate and stroke-appropriate on the web overlay + chart.
**Concern (recorded, not blocking):** the windows are hand-tuned on one swimmer. The honest version
sets each stroke's window from its measured velocity spectrum once a broader corpus exists.
**Note for Phase 65 / future segmentation:** acceleration is now a clean signal and is tempting to
segment on (`_learned_boundaries` already uses `dv`/`d²v`). ⚠ These windows are tuned for DISPLAY —
if segmentation starts depending on acceleration, the window becomes a segmentation hyperparameter
and "display-only" no longer holds.

---
*Phase: 66-acceleration-derivative, Plan: 01 — Completed 2026-08-16*
