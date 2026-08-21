---
phase: 77-fly-breakout-detection
plan: 01
subsystem: signal-processing
tags: [butterfly, breakout, cwt, band-power, morlet, metrics, refuse-to-answer]

requires:
  - phase: 76-breakout-detection
    provides: the free/back kick-band detector, the `_breakout_leaves_swim` collapse guard, the
              `compute_session_metrics` per-stroke override seam, and `tools/breakout_band_probe.py`
  - phase: 75-report-card-phase-model
    provides: `detect_underwater_start` (75-02) — the `uw_start_idx` this detector searches from
provides:
  - metrics.detect_breakout_fly — butterfly Underwater→Swim boundary by arm-cycle APPEARANCE
  - a butterfly-only `ip_end` override in compute_session_metrics
  - the fly section of tools/breakout_band_probe.py (scorer, fingerprint, jitter grid, contrast sweep,
    seam check, --plot)
affects: [75-03 underwater kick metrics, backfill of stored butterfly sessions, annotate seed]

tech-stack:
  added: []
  patterns:
    - "Refuse-to-answer: return None and let the caller keep the incumbent boundary, rather than ship a
       confident wrong answer"
    - "Score the SHIPPED function in the probe, never a probe-local reimplementation"
    - "Band-edge jitter grid as the standard test for physical-vs-knife-edge"

key-files:
  created: []
  modified: [metrics.py, tests/test_metrics.py, tools/breakout_band_probe.py, .paul/ROADMAP.md]

key-decisions:
  - "D5 per-session f0 band refinement MEASURED AND REJECTED (2.33 s vs 0.38 s) — left in code, off"
  - "_FLY_MIN_CONTRAST added unplanned at 1.5 — without it the detector cannot refuse for lack of signal"
  - "_FLY_SCALO_HZ = (0.5, 5.0), not the plan's (0.5, 3.0) — the measurement was made on that grid"
  - "e50eb628's +4.12 s confident miss accepted as the price of contrast 1.5 over 2.0"

patterns-established:
  - "Cycle regularity / physical plausibility is a separate gate from median error"
  - "A checkpoint tool must not surface a rejected detector's output alongside the shipped one"

duration: ~5h (plan → apply → checkpoint → unify, across a session break)
started: 2026-08-20
completed: 2026-08-20
---

# Phase 77 Plan 01: Fly Breakout Detection — Summary

**Shipped `metrics.detect_breakout_fly` — the band-power ratio `P(0.8–1.1 Hz) / P(1.1–1.5 Hz)` detected
as a rise after a sustained low — taking butterfly's Underwater→Swim boundary from a median |err| of
2.67 s to 0.38 s on 16 annotated sessions, with free/back/breaststroke byte-identical.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~5h including a session break and one review cycle |
| Started | 2026-08-20 (PLAN written 17:09) |
| Completed | 2026-08-20 |
| Tasks | 5 of 5 (4 auto + 1 `checkpoint:human-verify`) |
| Files modified | 4 (`metrics.py`, `tests/test_metrics.py`, `tools/breakout_band_probe.py`, `.paul/ROADMAP.md`) |
| Tests added | 20 (`TestBreakoutFly` + `TestBreakoutFlyIntegration`) |
| Suite | **403 passed** (baseline 388) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Finds the fly breakout, refuses when unsure | **Pass, with a correction** | Detection and the never-raise contract hold. ⚠ AC-1's premise that the sustained-low-run gate supplies the refusal was **refuted** — see Deviation 5. The refusal is real, but `_FLY_MIN_CONTRAST` is what delivers it. |
| AC-2: Measured accuracy holds on DB ground truth | **Pass** | median 0.38 s (target ≤0.6 s), **12/16 ≤1.0 s** (required ≥11/16), 9/16 ≤0.5 s, 1 refusal scored at the incumbent. Jitter grid worst cell **0.94 s < 2.67 s incumbent** on all 16 cells. Auto `detect_underwater_start` seam gives an **identical 0.38 s**. |
| AC-3: Per-stroke; free/back/breast byte-identical | **Pass** | Branch at `metrics.py:1393`, immediately after the 76 free/back branch and **before** the manual override at `:1401`. Byte-identity verified by rebuilding the pre-77 module and diffing every returned key. |
| AC-4: Detections look right on real DB traces | **Pass** | User approved after review. ⚠ Approval took a second pass because the checkpoint tool showed the wrong plots first — see Deviation 6. |
| AC-5: Suite green, contract files untouched | **Pass** | **403 passed**, 1 pre-existing warning (baseline 388 → this plan added 15 net collected). `git diff api.py annotations.py` **empty**. `metrics.py` diff is **479 insertions, 0 deletions** — so no 76 symbol could have been modified. |

## Accomplishments

- **The incumbent is beaten by ~7×** on butterfly: median |err| 2.67 s → 0.38 s, sessions within 1 s
  2/16 → 12/16, six sessions inside 0.12 s.
- **Robustness measured rather than asserted.** All 16 band-edge jitter cells beat the incumbent
  (worst 0.94 s), so the win is physical. The production seam was checked by re-scoring with the auto
  `detect_underwater_start` instead of the coach's mark — identical 0.38 s.
- **Two ideas were measured and rejected instead of shipped on faith** — the D5 per-session f0 band
  refinement (2.33 s vs 0.38 s) and `_FLY_MIN_CONTRAST ≥ 2.0` (0.63 s, 4 refusals).
- **The physical fingerprint reproduced** at the coach's marks: arm band 2.53× (appears, 14/16),
  fundamental 0.45× (drops), 2-beat harmonic 2.09× (appears, 15/16).

## Full Measured Result (live DB, 16 annotated butterfly sessions)

| session | coach mark | detected | err | incumbent err |
|---|---|---|---|---|
| bc064b9d | 4.76 | 4.77 | +0.01 | +4.11 |
| 22b4711b | 6.42 | 6.34 | −0.08 | +2.43 |
| f28712f3 | 6.34 | 6.23 | −0.11 | +3.46 |
| 3f3bf63f | 6.31 | 6.20 | −0.11 | +4.40 |
| 6db0859d | 8.40 | 8.29 | −0.11 | +2.92 |
| 2ecabf17 | 7.25 | 7.13 | −0.12 | +2.95 |
| c0cdfc25 | 5.20 | 5.49 | +0.29 | +2.02 |
| e166b8fe | 4.58 | 4.93 | +0.35 | +1.58 |
| 24274495 | 5.91 | 5.51 | −0.40 | +0.82 |
| 1cb736af | 11.35 | 11.89 | +0.54 | −3.25 |
| 86a83f92 | 7.73 | 8.46 | +0.73 | +2.05 |
| 85b18b3f | 10.75 | 11.62 | +0.87 | −3.75 |
| 6b206400 | 6.27 | 5.12 | −1.15 | +1.25 |
| 30d73d65 | 9.41 | 11.45 | +2.04 | +0.95 |
| 0d3e7820 | 6.76 | REFUSE | (+3.05 fallback) | +3.05 |
| e50eb628 | 4.87 | 8.99 | +4.12 | +2.42 |

**median 0.38 s · mean 0.88 s · ≤0.5 s 9/16 · ≤1.0 s 12/16 · refused 1**

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `metrics.py` | Modified (+additive block at `:994–1300`, branch at `:1393`) | `_fly_scalogram`, `_fly_band`, `_fly_bands`, `_fly_band_ratio`, `detect_breakout_fly`, 14 constants, and the butterfly `ip_end` override |
| `tests/test_metrics.py` | Modified (+20 tests) | `TestBreakoutFly` (detector contract, refusals, degenerate input) + `TestBreakoutFlyIntegration` (per-stroke dispatch, manual precedence, collapse veto, byte-identity) |
| `tools/breakout_band_probe.py` | Modified (fly section, ~250 lines) | Scores the **shipped** detector; fingerprint, jitter grid, contrast sweep, refinement comparison, seam check, `--plot` |
| `.paul/ROADMAP.md` | Modified (+1 row) | Phase 77 row in the v0.5 table |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| `_FLY_MIN_CONTRAST = 1.5` | Top of a measured flat 1.0–1.5 plateau; ≥2.0 costs 0.38→0.63 s and 3 good detections | Accepts one confident miss (`e50eb628`) to gain three correct detections |
| `_FLY_REFINE_BANDS = False` (D5) | Measured 2.33 s vs 0.38 s. It peak-picks whatever dominates just after `uw_start`, which on a short/weak underwater is already the arm cycle — it derives its "fundamental" from the thing it should measure against | Left in code, off. It is the swimmer-invariant idea and one swimmer's corpus cannot refute it |
| No learned model (D2) | 16 sessions from ONE swimmer — where 59-05's no-overfit reasoning bites hardest | Fixed physical bands only |
| Reuse `_breakout_leaves_swim` rather than a fly copy | 76-01's `stroke_count → 0` failure came from exactly this seam | One guard, one place to fix |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Scope additions | 1 | `_FLY_MIN_CONTRAST` — essential, not creep |
| Constant/tolerance corrections | 3 | Reproduce the measurement rather than approximate it |
| Premise refuted | 1 | AC-1's refusal mechanism was wrong |
| Tooling defect found at checkpoint | 1 | Cost one review cycle; not shipped code |

**Total impact:** No scope creep. One plan premise refuted, one unplanned gate that the plan needed and
did not specify, and one checkpoint-tooling defect that should be fixed before the next breakout phase.

### 1. `_FLY_MIN_CONTRAST` added — a gate the plan did not specify
- **Found during:** Task 1, writing the refusal tests.
- **Issue:** The low/rise thresholds are drawn from the ratio's **own** 20–80 percentile range, so a
  threshold always sits inside the observed spread. A merely *rippling* ratio therefore always
  eventually supplies a low run and a "rise" — the detector could refuse only for running out of
  window, never for **lack of signal**.
- **Fix:** A contrast floor — the ratio's 80th percentile must be ≥1.5× its 20th.
- **Verification:** `_fly_contrast_sweep` in the probe; value chosen off the measured plateau, not taste.

### 2. `_FLY_SCALO_HZ = (0.5, 5.0)`, not the plan's `(0.5, 3.0)`
The 0.35 s scratch result was measured on the 0.5–5.0 geomspace grid with 96 scales. Changing the grid
changes which frequencies land in each band, so the plan's value would not have reproduced its own
cited measurement.

### 3. Synthetic test tolerance 1.5 s, not 1.0 s
The CWT smears a *hard synthetic step* over ~1 s at these frequencies, so ~1.1 s of lag is the wavelet,
not the detector. The accuracy claim that matters is the DB score (0.38 s), not the fixture.

### 4. One refusal test asserts with the floor deliberately raised
On a synthetic stationary tone the contrast lands at 1.35–1.49 — the no-low-run case would pass at the
shipped 1.5 floor by only 0.7%, which tests numpy's rounding rather than the detector. Documented in
the test.

### 5. ⚠ AC-1's refusal premise was REFUTED
The sustained-low-run requirement does **not** by itself refuse a stationary stroking trace — the arm
cycle's own amplitude modulation satisfies it. **Only the contrast gate stops that case.** AC-1 assumed
the low-run gate would. Carried forward as a real finding: any future band-ratio detector that draws its
thresholds from its own signal's percentile range inherits this hole.

### 6. ⚠ The checkpoint tool surfaces a REJECTED detector's butterfly output ahead of the shipped one
- **Found during:** Task 5, the human-verify checkpoint itself. It caused a rejected review
  ("most are not even close") that cost a full cycle to diagnose.
- **Issue, two surfaces of the same defect:**
  1. `--plot` runs the Phase-76 `_plot()` for **every** session including butterfly, writing 17
     `{sid}_butterfly.png` whose blue "candidate" line is the kick-band rule Phase 77 exists *because*
     it fails on fly. Those sort **before** the 16 `fly_{sid}.png` in any directory listing. Same
     session, both files: `1cb736af` reads −6.1 s in one and +0.54 s in the other; `22b4711b` reads
     +9.3 s and −0.08 s.
  2. The console per-stroke summary prints `[butterfly] SHIPPED median |err| 3.00s` — that row is
     `detect_breakout_kickband` scored on butterfly, **not what production runs for fly**. The real fly
     number appears ~40 lines further down.
  3. ⚠ **Found while closing this loop, and it is the worst of the three:** `_plot` never renders a
     shipped detector *at all*. Line 244 computes `ship_idx` from `metrics.detect_breakout_kickband`
     and scores it, but line 270 passes **`cand_idx`** — the probe's own exploratory
     `_detect_breakout` — to `_plot`. So every `{sid}_{stroke}.png`, **freestyle included**, draws a
     detector that 76-01's Correction 2 measured as materially different from production (0.86 s vs
     0.42 s). Only `_fly_plot` (added by this plan) renders what actually ships.
     **Consequence: Phase 76's still-owed AC-4 human-verify checkpoint cannot be satisfied by the
     current tool** — the freestyle plots do not show the freestyle detector that shipped.
- **Status: NOT FIXED — deferred.** It is checkpoint tooling, not shipped code, and fixing it was not
  in this plan's scope. Logged below.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| STATE.md asserted "THE SUITE IS RED — one failure caused by 76-01" | **Stale.** Suite was already green at baseline (388) before this plan. Corrected in STATE.md. |
| Checkpoint rejected on first review | Root-caused to Deviation 6 (wrong plot set), not to detector behaviour. Re-verified against the shipped `fly_*` plots and the re-run scorer; approved. |

## Deferred Items

- **DEFER-77-A — Fix `breakout_band_probe.py`'s reporting. Three defects, one root cause: the tool
  shows exploratory/rejected detectors where it should show the shipped one.**
  (a) pass `ship_idx` to `_plot` instead of `cand_idx`, so the free/back plots render the detector that
  actually ships — **this one blocks Phase 76's owed AC-4**;
  (b) write the Phase-76 butterfly PNGs to a `rejected/` subfolder, or skip them for butterfly;
  (c) label the per-stroke butterfly `SHIPPED` row `76-kickband, N/A for fly`.
  Origin: Task 5 (a found at UNIFY). **Do (a) before Phase 76's checkpoint, and all three before the
  next breakout phase runs a human-verify checkpoint.**
- **D6 — Comparability break + backfill for stored butterfly sessions.** Every stored butterfly session's
  `ip_end`-derived metrics are now out of scale with newly-processed ones. The DB write is a **separate
  post-approval step the user runs** — Claude is blocked from unattended production writes.
- **D7 — 75-03 flag.** Butterfly kick metrics now inherit a correct `stroke_start`; raise this at 75-03
  apply time, since the kick window is `[uw_start, stroke_start]`.
- **Ground-truth question (raised, unresolved).** On several fly traces the coach mark sits well after
  where velocity visibly starts oscillating (`1cb736af` oscillates from ~4.5 s, marked 11.4 s;
  `85b18b3f` from ~3.5 s, marked 10.8 s). That gap is underwater dolphin kicking, which looks like
  stroking on a velocity trace. Not a code issue — a question about the marks, if fly accuracy is ever
  revisited.

## Next Phase Readiness

**Ready:**
- All four strokes now have a breakout path: free/back on 76's kick-band disappearance, butterfly on
  77's arm-cycle appearance, breaststroke unchanged (pulldown, not a kick train).
- 75-03's underwater kick window has a trustworthy end boundary on fly.

**Concerns:**
- **Two unclosed loops sit under this one.** 76-01 and 75-03 are applied in the working tree with no
  SUMMARY and no commit. Phase 77's diff is not the only uncommitted change.
- `e50eb628` is a known +4.12 s confident miss — the one case where the refuse-rather-than-guess
  convention loses. Deliberate.
- 16 sessions, one swimmer. Every constant here is fitted to that corpus, and the jitter grid is the
  only evidence that it generalises.

**Blockers:** None.

---
*Phase: 77-fly-breakout-detection, Plan: 01*
*Completed: 2026-08-20*
