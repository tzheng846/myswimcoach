---
phase: 87-stroke-level-asymmetry
plan: 01
subsystem: metrics
tags: [segmentation, freestyle, backstroke, asymmetry, wavelet, backfill, supabase]

requires:
  - phase: 59-stroke-specific-segmentation
    provides: _pair_boundaries + SEGMENTER_BY_STROKE, the leading-pad drop rule, MARKS_PER_CYCLE
  - phase: 75-report-card
    provides: metrics_json.phases.boundaries (resolved manual > detected > auto) — the backfill's swim window
  - phase: 83-per-cycle-trace-coloring
    provides: the additive-backfill precedent (one key only, user-run, print the zeros)
provides:
  - metrics.segment_strokes — single-arm segmentation for freestyle/backstroke
  - metrics._derive_item_metrics — the per-cycle derivation loop, now shared by cycles and strokes
  - metrics._arm_asymmetry — 3 signed asymmetry percentages + 4 per-side CVs
  - metrics_json.strokes — stored per-arm-stroke array, beside cycles
  - annotations.annotation_to_overrides -> stroke_bounds (k > 1 only)
  - tools/backfill_strokes.py
affects: [87-02-frontend-toggle, ratings, phase_metrics]

tech-stack:
  added: []
  patterns:
    - "Segmentation products of compute_session_metrics live at metrics_json TOP LEVEL beside cycles, not inside phases"
    - "Physiology gates (which strokes alternate arms) are separate from detector gates (the segmenter's k)"

key-files:
  created: [tools/backfill_strokes.py]
  modified: [metrics.py, annotations.py, api.py, tests/test_metrics.py, tests/test_annotations.py, tests/test_api.py]

key-decisions:
  - "D1: strokes at metrics_json top level beside cycles — same producer, same two write sites, no SCHEMA_VERSION bump"
  - "D2: asymmetry ships on AUTO sessions despite r = -0.06 vs coach-mark truth (user call, made after seeing the measurement)"
  - "D3: sides are A/B, never left/right — a 1-D axial encoder cannot observe which arm is which"
  - "DEV-1: segment_strokes gates on stroke_type, NOT on the segmenter's .k — fly/breast carry k=2"

patterns-established:
  - "One shared _segmenter_bounds helper carries the 59-05 pad-drop rule, so cycles and strokes cannot diverge on it"
  - "Drift guard by inert-path comparison: monkeypatch the new path off and assert the old output is byte-identical"

duration: ~75min
started: 2026-08-31
completed: 2026-08-31
---

# Phase 87 Plan 01: Stroke-level segmentation + arm asymmetry (BACKEND) Summary

**The individual arm stroke is now a stored unit — `metrics_json.strokes` beside `cycles` for
freestyle/backstroke, with seven signed asymmetry / per-side-consistency keys in
`metrics_json.session`, backfilled across 47 of the 101 stored sessions.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~75 min |
| Started | 2026-08-31 |
| Completed | 2026-08-31 |
| Tasks | 4 of 4 (3 auto + 1 blocking human-action checkpoint) |
| Files modified | 6 modified, 1 created |
| Test suite | 520 → **563 green** (43 new; no pre-existing test modified) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: strokes for alternating-arm strokes only | **Pass** | `TestSegmentStrokes`: full cycle field set + `stroke_num`; `None` for butterfly, breaststroke, `im`, `udk`, an unknown string, and `None`. Gate is stroke_type, not `.k` — see DEV-1 |
| AC-2: cycle output byte-identical | **Pass** | `TestStrokeDriftGuard` across all 5 stroke types: `cycles` equal and every pre-existing `session` key equal, with the strokes path monkeypatched inert. Suite green with no pre-existing test touched |
| AC-3: coach marks drive strokes | **Pass** | 7 marks → 6 `stroke_bounds` + 3 `cycle_bounds`; `cycle_bounds` pinned against the pre-change expectation; absent at `marks_per_cycle == 1` for all 7 legacy stroke values; `finish_s` never appended |
| AC-4: signed, documented, sample-size gated | **Pass** | All seven `None` below 3 usable strokes per side; a known ±33% imbalance recovers to +33.3 ±3.0 and flips sign when the sides swap |
| AC-5: both write sites persist strokes | **Pass** | POST /process: response body + captured insert payload. PUT /annotations: strokes replaced from marks while `phases`, `go_signal_s` and the once-only `metrics_json_auto` backup survive |
| AC-6: backfill additive, zeros visible | **Pass** | Dry-run changed nothing (verified by re-read); `--apply` wrote only `strokes` + the 7 session keys; all six counters printed including the zero |
| AC-7: measured limits live in the code | **Pass** | `r = -0.06`, the parity-flip cause, and the left/right impossibility are in `segment_strokes`' docstring, `_arm_asymmetry`'s docstring, and `tools/backfill_strokes.py`'s module docstring |

## Accomplishments

- **`metrics.segment_strokes`** — runs the UNPAIRED base segmenter (reachable via the new
  `paired.base` / `paired.k` attributes) on the same slice and takes every boundary instead of
  every k-th. Calling the segmenter a second time rather than deriving strokes from surviving
  cycles is deliberate: `paired` drops degenerate spans *after* pairing, so the two drop sets
  are not nested.
- **The 59-05 leading-pad drop is now shared code** (`_segmenter_bounds`), used by both
  `_pair_boundaries` and `segment_strokes`. That rule was worth boundary F1 0.000 → 0.458 and
  is invisible to `stroke_rate_spm`; it can no longer be reimplemented differently in two places.
- **`_derive_item_metrics`** — the per-cycle derivation loop extracted verbatim, so a stroke and
  a cycle carry an identical field set computed by identical code.
- **Backfill applied**: 47 of 101 sessions written, **24 from coach marks**, 20 from the auto
  segmenter, 3 with a resolvable window but no strokes, 11 left `None` for <3 strokes per side;
  54 skipped as non-free/back; 0 failed. Post-write live read confirms 42/45 freestyle rows carry
  `strokes` with `phases`/`cycles`/`initial_phase`/`data_quality` intact, and that breaststroke
  rows have no `strokes` key at all.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `metrics.py` | Modified (+278/−61) | `_segmenter_bounds`, `_spans_from_bounds`, `segment_strokes`, `_arm_asymmetry`, `_derive_item_metrics`; `strokes` key on the return |
| `annotations.py` | Modified (+21) | `stroke_bounds` from all marks, emitted only at `k > 1` |
| `api.py` | Modified (+6/−2) | `strokes` in the POST /process insert + response and in the PUT /annotations merge |
| `tools/backfill_strokes.py` | **Created** (260 lines) | Additive-only backfill, dry-run by default |
| `tests/test_metrics.py` | Modified (+149) | 22 tests: segmentation, asymmetry, drift guard |
| `tests/test_annotations.py` | Modified (+120) | 15 tests: `stroke_bounds` contract + PUT persistence |
| `tests/test_api.py` | Modified (+68) | 6 tests: POST /process response + insert payload |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| **DEV-1** — `segment_strokes` gates on `stroke_type ∈ (freestyle, backstroke)`, not on the segmenter's `.k == 1` as the plan's Task 1 step 3 specified | Butterfly and breaststroke carry `k=2` in `SEGMENTER_BY_STROKE` — a property of *their detector*, per that table's own ⚠ comment — so a `.k` gate would have emitted a strokes array for them and contradicted the plan's own AC-1 | New module constant `_ALTERNATING_ARM_STROKES`, commented to name the two-quantities distinction. A future stroke that alternates arms must be added there, not inferred from `k` |
| Backfill's v95 window starts at `dive_start_s` where the stored boundaries carry one | `compute_session_metrics` windows v95 over `b_end → swim_end`, and v95 sets the dead-spot threshold; using the stroke start instead would silently shift `dead_spot_s` between the live path and the backfilled one | Backfilled `dead_spot_s` matches what /process would have produced |
| Everything else followed the plan | — | — |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Plan-internal contradiction, resolved in favour of the AC |
| Scope additions | 0 | — |
| Deferred | 1 | Observation only, logged below |

**Total impact:** one necessary correction to a plan step that contradicted its own acceptance
criterion. No scope creep; nothing a coach can currently see changed.

### Auto-fixed Issues

**1. [Contract] Task 1 step 3's `.k` gate would have broken AC-1**
- **Found during:** Task 1, reading `SEGMENTER_BY_STROKE` before writing `segment_strokes`
- **Issue:** the plan said return `None` when the resolved segmenter has `.k == 1`; butterfly
  and breaststroke are registered as `_pair_boundaries(_learned_boundaries, 2)`, so `.k == 2`
  for them and they would have received a duplicate-of-cycles strokes array
- **Fix:** gate on the physiology set `_ALTERNATING_ARM_STROKES`, with a comment naming why the
  detector's `k` and the stroke's arms-per-cycle are different quantities
- **Verification:** `TestSegmentStrokes::test_non_alternating_strokes_get_none`, parametrised
  over butterfly, breaststroke, `im`, `udk`, an unknown string, and `None`
- **Note:** the plan's stated 505-test baseline was also stale; the real baseline was 520

### Deferred Items

- **3 freestyle sessions have a resolvable swim window but produce zero strokes**
  (`6f1c8510`, `a7a9e3ad`, `5ddef202`, plus `925fffa1` at a single stroke). Not introduced by
  this plan — those sessions already produced no cycles — but the backfill made the count
  visible for the first time. Worth a look before 87-02 renders an empty stroke view for them.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| PUT /annotations calls `compute_session_metrics` without `stroke_type` | No change needed — `manual["stroke_bounds"]` (derived from stroke_type upstream in `annotation_to_overrides`) drives the manual branch, which never consults `stroke_type` |
| `TestSchemaContract` risk flagged in Task 2 step 3 | Confirmed by running it, not assumed: `strokes` lives inside the existing `metrics_json` jsonb, so no new column and no SQL patch. Green |

## Next Phase Readiness

**Ready:**
- `metrics.strokes` is present in the payload for every free/back session with a resolvable
  window — 87-02's toggle has data to switch to on both the live path and the stored library.
- `cycleBands.js` / `cycleTraces.js` already take a `durationKey`; the `numberKey` option 87-02
  needs is the same shape-agnostic seam, and stroke dicts carry `stroke_num` where cycles carry
  `cycle_num`.
- The seven session keys are in `metrics_json.session`, so the A/B readout needs no new endpoint.

**Concerns:**
- **D2's risk is now live in the library.** 20 of the 47 backfilled sessions carry auto-derived
  asymmetry that measured `r = -0.06` against coach-mark truth. 87-02 shows it under the existing
  `auto` chip only, per the user's call — the number will look authoritative in the UI regardless.
- Backstroke (2 sessions, 0 annotated) rides freestyle's code path untested against ground truth.
  Confirms STATE item 10; do not report backstroke asymmetry as validated.
- The 3 zero-stroke sessions above will render an empty stroke view in 87-02.

**Blockers:** None.

---
*Phase: 87-stroke-level-asymmetry, Plan: 01*
*Completed: 2026-08-31*
