---
phase: 59-segmenter-evaluation
plan: 03
subsystem: api
tags: [segmentation, swim-window, cwt, ridge, stroke-rate, pairing, metrics]

requires:
  - phase: 59-segmenter-evaluation (59-01)
    provides: the scoring harness, the ground-truth corpus, and the measurements that
              established the 1.75x defect and the +7.8 s window error
  - phase: 59-segmenter-evaluation (59-02)
    provides: SEGMENTER_BY_STROKE — the seam the pairing wrapper is registered through
provides:
  - "metrics.detect_swim_window — rhythm-based swim window, with a self-distrust fallback"
  - "metrics._pair_boundaries — cycle pairing for alternating-arm strokes"
  - "metrics._cwt_ridge — shared ridge extraction (segmenter + window detector)"
  - "tools/window_candidates.py — the 4-candidate research record"
  - "tools/backfill_preview.py — read-only quantification of the stored-row gap"
affects: [59-04 exploration, 59-05 ship, a future backfill plan, 53-attention-allocation]

tech-stack:
  added: []
  patterns:
    - "A detector that returns None rather than a confident wrong answer"
    - "Plausibility fallback asymmetry: false positive costs only the improvement"
    - "Validate on the FULL corpus, not just the tuned subset"

key-files:
  created: [tools/window_candidates.py, tools/backfill_preview.py]
  modified: [metrics.py, tests/test_metrics.py, CLAUDE.md]

key-decisions:
  - "Ship D_settle — frequency settling, the only candidate of 4 to clear the gate"
  - "Add _WINDOW_MIN_CYCLES plausibility fallback after finding 13/36 collapses"
  - "Backfill preview only; no DB write authorised"

patterns-established:
  - "A gate measured on the tuning subset proves nothing about generalisation"
  - "Prefer disbelieving a detector over emitting an implausible window"

duration: ~2h
started: 2026-08-09
completed: 2026-08-09
---

# Phase 59 Plan 03: Swim Window + Cycle Pairing — Summary

**Freestyle stroke rate now reads 0.973× the human-derived value instead of 1.647×, by fixing two coupled errors together — and the window detector was given the ability to refuse to answer, after the full corpus showed it collapsing on 13 of 36 sessions.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~2 h |
| Tasks | 4 auto + 1 checkpoint:decision, all completed |
| Files | 2 created, 3 modified |
| Suite | 268 → **269** |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Window matches the annotator | **Pass** | `ip_end` 3.93 → **1.99 s**, `finish` 3.82 → **0.82 s** (median \|error\|). Per-stroke at the checkpoint: freestyle 3.95→2.28 / 3.50→1.78, butterfly 3.56→2.02 / 4.72→0.71, breaststroke 4.02→1.95 / 2.96→1.42. |
| AC-2: Rate lands on the human scale | **Pass** | Median ratio **0.973** (was 1.647); median \|log ratio\| **0.069** (was 0.50). Gate required 0.85–1.15 and <0.50. |
| AC-3: Annotation path still wins | **Pass** | Verified empirically across 23 `cycle_bounds` recomputes: `cycles` identical 23/23, `session` identical 22/23. The one exception is explained below and is correct. |
| AC-4: Non-paired strokes unpaired | **Pass** | Butterfly/breaststroke take the bare wavelet. Their numbers still moved — via the window alone — median ratio **1.316**, fly as high as 1.92. Reported, not compensated. |
| AC-5: Corpus quantified, not modified | **Pass** | 37 rows; **16 ANNOTATED → a backfill must skip them**; 14 auto rows would move, median stored/new 1.65, range 0.73–4.88. Read-only confirmed by grep. |
| AC-6: Pins re-baselined, never weakened | **Pass** | 3 of 59-02's `TestSegmenterDispatch` tests inverted, +1 added. 59-01's 7 pins did not move — see Findings. |

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `metrics.py` | Modified | `_cwt_ridge` (shared), `detect_swim_window` + `_longest_active_run` + 5 constants, `_pair_boundaries`, registry populated, `compute_session_metrics` wiring |
| `tools/window_candidates.py` | Created | The 4-candidate research record — A_envelope, B_env+band, C_ridgepow, D_settle |
| `tools/backfill_preview.py` | Created | Read-only preview of what stored rows would become |
| `tests/test_metrics.py` | Modified | `TestSegmenterDispatch` re-baselined + AC-3 override test |
| `CLAUDE.md` | Modified | New "swim window is rhythm-based" section; the 1.75× defect marked fixed |

## Findings

### The research mattered — three of four candidates failed, and instructively
A_envelope and B_env+band missed `ip_end` by 4–8 s, **always early**, because underwater dolphin
kicking is rhythmic and an amplitude test accepts it. B's band filter could not reject it either:
its reference frequency was computed over a mask that already contained the kicking, so the band
centred on the wrong value. C_ridgepow nailed `finish` (1.20 s) but was the **worst** on `ip_end`
(6.31 s). Only D_settle — which uses the frequency **transition**, taking steady-state stroke
frequency from the back 60% of the swim and finding where the ridge first settles near it —
beat the incumbent on both.

### A gate measured on the tuning subset proves nothing about generalisation
The AC-2 gate uses the 12 fully-labeled sessions. Those are exactly what the detector was tuned
against. Run across all 36 freestyle/backstroke sessions, **13 produced a window yielding ≤3
cycles** — implausible for a 25 m swim, and a failure mode the OLD detector never had (it erred by
including too much, never too little). This is CONTEXT R1 (one swimmer, overfitting) arriving as a
measured fact rather than a caveat.

**Root cause, diagnosed rather than guessed:** the amplitude run latches onto the **dive
transient**. It starts at t=0 and ends early, because the dive's broadband energy inflates the
95th-percentile reference until actual swimming falls below 25% of it.

**Four alternative references were swept and all rejected** — none beat the shipped one, two were
dramatically worse:

| reference | collapse | ip MAE | fin MAE |
|---|---|---|---|
| p95 / 0.25 (shipped) | 13/36 | 2.52 | 2.20 |
| median / 1.5 | 28/36 | 5.94 | 10.67 |
| median / 2.5 | 32/36 | 5.54 | 12.16 |
| post-baseline p75 / 0.6 | 18/36 | 2.82 | 2.74 |
| post-baseline p75 / 0.9 | 27/36 | 6.17 | 8.78 |

### 59-01's pins did not move — and that is a finding, not a relief
They measure the **raw segmenter** and **stored `metrics_json_auto`**, neither of which this plan
touched. ⚠ **Consequence: `tools/score_segmenter.py`'s "production window" column is now STALE.**
Its `_windows()` still calls `detect_phases` / `detect_initial_phase`, so the harness no longer
measures what production slices. Left unchanged deliberately (the plan boundaries the harness), but
**59-04 must fix it before trusting that column.**

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Ship `D_settle` (checkpoint) | Only candidate of 4 to clear the gate: ratio 0.991, \|log\| 0.035 | Tasks 2–4 proceeded |
| Add `_WINDOW_MIN_CYCLES = 4.0` | 13/36 collapse found at Task 4; threshold sweeps all failed | Collapse 13/36 → **1/36**; errors on kept windows *improved* (ip 2.16→1.99, fin 1.20→0.82) |
| Divisor NOT from `annotations.MARKS_PER_CYCLE` | That table is exact physiology for HUMAN marks; k=2 works on the auto path only as an empirical property of *this* segmenter | 59-05 must re-measure k if it swaps the base segmenter |
| Backfill preview only | CONTEXT D20 | 37 rows quantified; DB write is a separate plan and decision |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Caught my own ordering bug before it shipped |
| Scope additions | 2 | One essential (fallback), one DRY (shared ridge) |
| Deferred | 1 | Stale harness column → 59-04 |

**1. [Scope addition — user-authorised] The plausibility fallback.**
Not in the plan. Found at Task 4, exceeded what the checkpoint had approved, so execution stopped
and the user was asked rather than shipping it or patching around it. `_WINDOW_MIN_CYCLES` flags
13/13 collapsed windows while also disbelieving 7/23 sound ones — **the asymmetry is deliberate**: a
false positive costs only the *improvement* (that session reverts to today's behavior), while a
false negative ships a confident wrong answer.

**2. [Scope addition — DRY] `_cwt_ridge` extracted.**
Two callers now need the same ridge; duplicating six lines would let them drift apart if `_WAVELET`
or the scale grid changed. **Proven inert by the 59-01 fixture hash** (`4609a7b0…` before and
after) — exactly the guardrail 59-02 built.

**3. [Auto-fixed] My own reordering broke the annotation path.**
Moving `detect_initial_phase` above the manual `baseline_end_idx` override changed which
`baseline_end` it received, silently altering dive/pulldown on annotated sessions. Caught by reading
the diff, not by a test. Restored to the pre-59-03 order, which is now documented in-place as
load-bearing.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| First threshold sweep timed out at 10 min (CWT recomputed per mode × session) | Cached the ridge once per session to a pickle; sweep then ran in seconds |
| The plan's read-only grep matched `sys.path.insert` | Tightened to a DB-builder-specific pattern; re-verified empty |
| AC-3 initially reported 23/23 differing | Narrowed to `initial_phase.initial_phase_end_idx` (the intended supersession) plus one genuine `session` difference, explained below |

**The one `session` difference:** `08-05T20:57` butterfly has `finish_s = null` in its annotation, so
there was no human finish to override with. The detector legitimately supplies one and `mean_vel_ms`
rose 1.18 → 1.43 by no longer averaging over ~24 s of dead tail. That session is already in the
exclusion list for exactly that reason.

## Next Phase Readiness

**Ready**
- The most visibly wrong number in the product is corrected, ground-truth-judged.
- `detect_swim_window` returning `None` gives 59-04 a clean extension point: improve the detector
  and the fallback rate falls.

**Concerns**
- ⚠ **`tools/score_segmenter.py`'s production-window column is stale.** 59-04 must fix it first.
- ⚠ **17 of 36 sessions currently fall back** to the old boundaries — the improvement reaches
  roughly half the corpus. That is the honest ceiling of what shipped.
- ⚠ **Butterfly and breaststroke got worse** (median 1.316, up to 1.92). The window fix removed an
  error that had been cancelling for them too. Owed to 59-04/05.
- ⚠ **37 stored sessions are now out of scale** with newly-processed ones, on top of the 16 already
  on the human scale. Comparability break recorded in `CLAUDE.md`.
- ⚠ **`ratings.py` is affected but untouched** — halving freestyle stroke rate moves it against the
  breaststroke-derived bands, changing pillar scores and the needs-attention list. Phase 53 owns it.
- ⚠ `_WINDOW_*` constants are tuned on one swimmer.

**Blockers**
- None.

**⚠ Phase 59 is 3 of 5 plans, NOT complete.** The plan-count heuristic would fire a transition here —
it must not. 59-04 (explore stroke-cycle segmentation) and 59-05 (ship the winner) are unwritten.
**59-04 is the user's originally-expected work** and is the immediate next plan.

---
*Phase: 59-segmenter-evaluation, Plan: 03*
*Completed: 2026-08-09*
