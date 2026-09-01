---
phase: 88-splits-picker-and-units
plan: 01
subsystem: metrics
tags: [phase-metrics, splits, registry, backfill, react, supabase]

requires:
  - phase: 75-06
    provides: the per-distance scalar split specs (splits_5m…splits_25m) and the DISPLAY row model
  - phase: 83-02
    provides: tools/backfill_phases.py as the established recompute seam
provides:
  - splits_remainder — mean velocity from 20 m past dive_start to finish_s, on the chord convention
  - _dive_relative() — the single shared "where is 0 m" block for dive-relative distance metrics
  - RETIRED_KEYS — a client-side skip so a retired registry key stops rendering off its stored label
  - two split fill counters in tools/backfill_phases.py
affects: [88-03, 88-04, any future registry retirement]

tech-stack:
  added: []
  patterns:
    - "Retiring a registry key needs a client-side skip set, not just a DISPLAY deletion"
    - "A distance/threshold floor is measured on the real library at a --dry-run checkpoint before --apply"

key-files:
  created: []
  modified:
    - phase_metrics.py
    - tests/test_phase_metrics.py
    - tools/backfill_phases.py
    - web/lib/phaseValence.js
    - web/components/portal/phases/PhaseReportCard.js

key-decisions:
  - "D3 REVISED: _MIN_REMAINDER_M is 0.5 m, not the planned 1.0 m — measured, not reasoned"
  - "D2 held: no SCHEMA_VERSION bump; registry membership is not phases-object shape"
  - "D5 held: the anchor block is extracted, not duplicated; the four surviving bins did not move"

patterns-established:
  - "Measure a threshold's fire rate on the real library before writing it anywhere (83-03's lesson, applied and it fired)"

duration: ~2h (across two sessions)
started: 2026-08-31
completed: 2026-08-31
---

# Phase 88 Plan 01: Splits Registry Summary

**`splits_25m` retired from the registry, the valence map and the report card; replaced by
`splits_remainder` (20 m → `finish_s`, chord velocity) and backfilled across all 99 stored
sessions — with the plan's 1.0 m distance floor caught wrong at its own checkpoint and re-picked
at 0.5 m against the measured library.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~2h across two sessions (mid-apply handoff) |
| Completed | 2026-08-31 |
| Tasks | 5 of 5 (4 auto + 1 blocking human-action checkpoint) |
| Files modified | 5 |
| Test suite | 563 → **566 green** |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: The closing stretch has a row | **Pass** | `test_remainder_covers_twenty_metres_to_the_finish` matches `_remainder_by_hand` to `rel=1e-9`; `splits_25m` absent from the computed object |
| AC-2: The four surviving bins did not move | **Pass** | `test_reached_splits_are_segment_mean_velocities` and `test_split_tracks_the_segment_it_covers` pass **unedited** — the `_dive_relative` extraction is behaviour-free |
| AC-3: A too-short stretch reports nothing | **Pass** | Both None-cases pinned; the floor test imports `pm._MIN_REMAINDER_M` rather than hardcoding, so the 1.0 → 0.5 change needed no test edit (0.4 m tail < 0.5 m still holds) |
| AC-4: The dead row disappears on old sessions | **Pass** | `RETIRED_KEYS` skip in the `model` memo; `splits_25m` appears nowhere in web source except that set |
| AC-5: The floor is measured before it is trusted | **Pass — and it failed the first time** | See Deviations |

## Verification Results

| Check | Result |
|---|---|
| `pytest tests/` | **566 passed** (563 baseline + 4 new − 1 replaced) |
| `python tools/backfill_phases.py --dry-run --limit 5` | both new counter lines print |
| `cd web && npm run build` | clean, 20 routes |
| `node scratch/stroke_toggle_check.mjs` | 63/63 |
| `node scratch/overlay_render_check.mjs` | 40/40 |
| `node scratch/marketing_render_check.mjs` | 45/45 |
| Live DB after `--apply` | 99/99 carry `splits_remainder`; **0** still carry `splits_25m`; `splits_20m` 56 non-null, `splits_remainder` **42** non-null |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `phase_metrics.py` | Modified | `_MIN_REMAINDER_M = 0.5`, `_dive_relative()` extracted, `_remainder_velocity()`, registry swap |
| `tests/test_phase_metrics.py` | Modified | `_remainder_by_hand` helper + 4 tests; 1 replaced; registry key-set updated |
| `tools/backfill_phases.py` | Modified | `with_split_20` / `with_split_rem` counters + two summary lines |
| `web/lib/phaseValence.js` | Modified | `splits_25m: "up"` → `splits_remainder: "up"` |
| `web/components/portal/phases/PhaseReportCard.js` | Modified | `RETIRED_KEYS` set, `DISPLAY` entry swap, skip in the row loop |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Decision revised at checkpoint | 1 | **Load-bearing** — the plan's stated premise was factually wrong |
| Scope additions | 0 | — |
| Deferred | 1 | 88-03 entanglement, see below |

### 1. D3's premise was wrong; `_MIN_REMAINDER_M` is 0.5 m, not 1.0 m

- **Found during:** Task 5, the blocking backfill checkpoint — exactly where AC-5 was designed to catch it.
- **Issue:** D3 justified a 1.0 m floor on the claim that a 25-yard lap leaves ~1.9 m past the
  20 m mark. It does not. `finish_s` clamps before the wall touch and `dist_m` already runs short
  of the wall (waist tether), so the tail is much shorter than the plan assumed. Measured across
  the 56 stored sessions that reach 20 m:

  ```
  median tail past 20 m: 0.872 m   (p25 0.486, p75 1.839, min 0.019, max 5.206)
  floor 0.0 → 56/56   0.3 → 49/56   0.5 → 42/56   0.75 → 34/56   1.0 → 23/56
  ```

  At 1.0 m the new metric filled **23 of 56 (41%)** — under the plan's own stated stop condition
  of two thirds. The floor sat *above the median tail*.
- **Fix:** Floor lowered to **0.5 m** (user decision at the checkpoint) → **42 of 56 (75%)**.
  0.5 m is ~0.3 s / ~26 samples at race speed and roughly half a torso; below it the chord is
  measuring the touch itself rather than a stretch of swimming. The code comment now carries the
  measured distribution and explicitly marks the original premise as corrected.
- **Verification:** `tools/backfill_phases.py --dry-run` on the full library reported
  `splits_remainder 42 of 99`, matching `scratch/_remainder_floor_probe.py` exactly; confirmed
  again by direct DB read after `--apply`.
- **Assessment:** AC-5 did its job. This is the second time (after 83-03) that a threshold
  reasoned-about rather than measured turned out wrong — the pattern is now twice-validated.

### Deferred

- **88-03's diff is entangled in `PhaseReportCard.js`.** The unit-conversion work (wave 2) was
  partially applied into this same file during the interrupted session, alongside
  `web/lib/unitConvert.js` and `scratch/unit_check.mjs` (63/63 passing). 88-01's boundary required
  the two diffs stay separable; they are not. Left in place rather than discarded — it is correct
  and green — but it means wave 1 cannot be committed without carrying wave 2 work along.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Session interrupted mid-apply; applied state untrusted | Full re-verification from scratch — every AC re-checked, whole test suite and all four render harnesses re-run rather than assumed |
| `_first_at` is duplicated between `_split_velocity` and `_remainder_velocity` | Accepted — the plan's Task 1 specified this shape, and hoisting the closure would have widened the AC-2 refactor surface for no behavioural gain |

## Next Phase Readiness

**Ready:**
- `splits_remainder` is stored, filled on 42 sessions, and displayed with band / label / empty note.
- `_dive_relative()` is the one dive-relative anchor block — **88-04's picker must call it** so its
  chord arithmetic reproduces a grid bin exactly (that plan's AC-2).
- `RETIRED_KEYS` is the established instrument for the next registry retirement.

**Concerns:**
- ⚠ **The new row's span varies ~10× across sessions** (0.5 m to 5.2 m), median 0.87 m. On a
  typical 25-yard lap it reads closer to *closing speed over ~0.9 m* than to a 5 m split, under a
  label that sits directly beneath four true 5 m splits. The `DISPLAY` desc warns to read it
  against the athlete's own same-distance swims, but the row is structurally not comparable to the
  four above it. Worth watching in 88-04's verification, where the picker makes the contrast visible.
- ⚠ **`RETIRED_KEYS` now matches nothing.** Zero sessions escaped the backfill (there are no
  `velocity_profile`-null rows), so no stored object carries `splits_25m` any more. The guard was
  still correct — the web deploy and the backfill are separate events and it covered that window —
  but it is defensive-only from here.
- ⚠ Old stored `splits_25m` values are gone, not migrated (CONTEXT D3, as planned).

**Blockers:** None.

---
*Phase: 88-splits-picker-and-units, Plan: 01*
*Completed: 2026-08-31*
