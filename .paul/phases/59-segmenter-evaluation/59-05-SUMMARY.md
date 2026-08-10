---
phase: 59-segmenter-evaluation
plan: 05
subsystem: api
tags: [segmentation, learned-model, dispatch, butterfly, breaststroke, regularity]

requires:
  - phase: 59-segmenter-evaluation (59-02)
    provides: SEGMENTER_BY_STROKE, the seam the new entries register through
  - phase: 59-segmenter-evaluation (59-04)
    provides: the scored candidate table and the regularity finding that chose the winner
provides:
  - "metrics._learned_boundaries — logistic-regression boundary detector, no new dependency"
  - "Butterfly and breaststroke routed off the wavelet"
  - "TestCycleRegularityGate — a standing guard against phase-drifting cycles"
  - "A fix for a phase bug in 59-03's freestyle pairing"
affects: [53-attention-allocation, a future backfill plan, ratings thresholds]

tech-stack:
  added: []
  patterns:
    - "Ship a fitted model as a constant block, not a loaded artifact"
    - "Cycle regularity is a gate separate from boundary F1"

key-files:
  created: []
  modified: [metrics.py, tests/test_metrics.py, CLAUDE.md]

key-decisions:
  - "Reimplement the learned model in numpy — no sklearn on the Railway path"
  - "peakpick rejected for butterfly despite a better F1"
  - "Freestyle stays on the wavelet"

patterns-established:
  - "A segmenter can place boundaries well and still emit meaningless cycles"
  - "stroke_rate_spm is blind to phase errors; cv and alternation are not"

duration: ~1h
started: 2026-08-09
completed: 2026-08-09
---

# Phase 59 Plan 05: Ship the Per-Stroke Segmenters — Summary

**Butterfly and breaststroke moved off the wavelet onto a 5-parameter learned detector, improving boundary placement, cycle regularity and stroke rate simultaneously — with no new production dependency — and the verification uncovered a phase bug that had made every shipped freestyle cycle half a cycle out of alignment.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~1 h |
| Tasks | 3 auto, 0 checkpoints |
| Files | 3 modified, 0 created |
| Suite | 269 → **273** |

## Results

| stroke | F1 before | F1 after | cv before | cv after | human cv | rate before | rate after |
|---|---|---|---|---|---|---|---|
| butterfly | 0.317 | **0.526** | 0.218 | **0.104** | 0.055 | 1.31 | **1.02** |
| breaststroke | 0.232 | **0.444** | 0.217 | **0.071** | 0.083 | 1.66 | **1.00** |
| freestyle | 0.000* | **0.458** | — | 0.094 | 0.062 | 1.00 | 1.03 |

\* freestyle's 0.000 was the phase bug described below — not a property of the wavelet.

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: fly/breast improve on all three axes | **Pass** | No axis regressed for either. |
| AC-2: freestyle untouched | **Pass, with a caveat** | Routing unchanged, and the fixture pins did not move. But freestyle *metrics* moved because of the phase fix — see deviations. |
| AC-3: no new production dependency | **Pass** | `grep sklearn metrics.py` returns only comment lines. Inference verified to reproduce sklearn to 1.1e-16. |
| AC-4: regularity is a standing gate | **Pass** | `TestCycleRegularityGate`, parametrised per stroke. |

## Findings

### The phase bug — the most consequential thing this plan found
`_anchors_from_marks` pads the boundary list with index 0, so `segment_cycles_wavelet` returns
`[0, m0, m1, …]`. `_pair_boundaries` then took indices 0, 2, 4… of *that*, selecting
`[0, m1, m3, …]` — **every freestyle cycle landing half a cycle out of phase with the arm entries.**

Measured on 12 freestyle sessions:

| pairing | median F1 |
|---|---|
| shipped (with the pad) | **0.000** |
| pad dropped | **0.458** |
| opposite phase | 0.000 |

**It survived 59-03's gate because `stroke_rate_spm` is blind to it** — the mean interval is
identical either way, so the rate ratio read 1.00 and nothing looked wrong. Only comparing boundary
*positions* to human marks exposed it. Fixed in `_pair_boundaries`.

### `peakpick` rejected for butterfly despite a better F1
0.524 vs the wavelet's 0.317 — it would have shipped on F1 alone. Its alternation of 0.276 against a
human 0.056 means its cycles drift through phases, because it emits an *unstable* ~2.5 events per
cycle. The learned detector emits ~2.02 *consistently*, so pairing lands one boundary per cycle at a
stable phase. **This is why AC-4 exists.**

### No sklearn in production
The model is logistic regression on 5 features; inference is a dot product and a sigmoid. The numpy
form reproduces `predict_proba` to 1.1e-16 across all 20 sessions. Weights ship as a constant block —
no artifact to version, store or lose. Retraining = re-run `tools/segmenter_candidates.py` and
replace two constants.

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Caught my own bug before it shipped |
| Scope additions | 1 | Fixed a pre-existing defect outside the stated boundary |

**1. [Auto-fixed] I shipped the detector using `_anchors_from_marks` and it scored 0.000.**
The tested candidate built cycles *between consecutive peaks*; `_anchors_from_marks` pads with 0 and
`len(vel)`. The plan warned about exactly this class of divergence for the *features* — it happened
at the boundary construction instead. Caught by the verification run, fixed, re-measured.

**2. [Scope addition, outside the stated boundary] The freestyle phase fix.**
59-05's boundaries said "do not change freestyle routing". The routing was not changed — but
`_pair_boundaries` was, which affects freestyle. Justification: it is a genuine defect that made the
shipped behaviour differ from the measured and intended behaviour, and leaving it would have meant
knowingly shipping misaligned freestyle cycles. ⚠ **Consequence: freestyle per-cycle metrics moved
again** — a second comparability break on top of 59-03's. Recorded in `CLAUDE.md`.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| First verification script compared *paired* boundaries against *all* arm entries | Wrong comparison for freestyle; corrected to compare against human cycle boundaries |
| `tests/test_segmenter_eval.py` listed in `files_modified` but never needed | Its pins measure the raw segmenter and never exercise the paired path, so nothing moved |

## Next Phase Readiness

**Ready**
- All four strokes route to a measured choice. Swapping any is a one-line registry edit, now guarded
  by the regularity gate.

**Concerns**
- ⚠ **Breaststroke rests on n=2 sessions.** Reverting is deleting one registry line.
- ⚠ **Freestyle metrics moved twice** (59-03 pairing, 59-05 phase fix). Stored sessions are further
  out of scale; `tools/backfill_preview.py` quantifies it.
- ⚠ Carried and untouched: the butterfly/breaststroke *window* regression from 59-03, the 17/36
  window fallback rate, and the trace-vs-video question.
- ⚠ The corpus mixes chart-timed and video-timed labels; nothing has been re-scored under the
  "trace is truth" rule adopted in 59-04.

**Blockers**
- None.

---
*Phase: 59-segmenter-evaluation, Plan: 05*
*Completed: 2026-08-09*
