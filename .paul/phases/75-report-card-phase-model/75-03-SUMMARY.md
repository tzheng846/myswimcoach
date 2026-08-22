---
phase: 75-report-card-phase-model
plan: 03
type: execute
status: complete
date: 2026-08-21
files_modified:
  - metrics.py                     # detect_underwater_kicks (75-03) + NEW detect_swim_boundaries (boundary fix)
  - phase_metrics.py               # 7 kick compute fns + registry flip; resolve_boundaries: stroke_start/finish "detected"
  - tests/test_phase_metrics.py    # kick-metric tests; boundary-contract updates + drift-guard test
  - tools/plot_kicks.py            # NEW eyeball harness (+ --annotated-only / --max-boundary-err modes)
  - PIPELINE.md                    # §3 stroke_start/finish now detector-resolved
  - .paul/STATE.md                 # 75-03 closed; owed-item 6 corrected; boundary fix recorded
hypothesis: 1                # find_peaks + prominence — APPROVED at eyeball, no hypothesis 2 needed
tests_green: true            # pytest tests/ = 426 passed
db_writes: false             # backfill is USER-run
---

# 75-03 SUMMARY — underwater dolphin-kick segmentation + the boundary fix it surfaced

## Headline
The dolphin-kick counter (`detect_underwater_kicks`, hypothesis 1 = `find_peaks` with a
prominence floor) is **validated and closed**. The eyeball checkpoint (AC-4) also exposed a
separate, higher-impact defect — the stored `stroke_start`/`finish` boundaries the kick window
rides on were **stale on the whole library, and the owed backfill would not have fixed them** —
which is now also fixed at the shared `resolve_boundaries` seam.

## Part A — the kick detector (the planned work)
- **`metrics.detect_underwater_kicks(t, vel, uw_start_idx, uw_end_idx)`** — each downkick is one
  axial velocity surge, so kicks are the prominent peaks of the window slice:
  `prominence = _UW_KICK_PROM_FRAC (0.15) · window-v95`, `distance = fs / _UW_KICK_MAX_HZ (4 Hz)`.
  Interior magnet-dropout NaNs are linearly filled first (a multi-peak prominence search would
  otherwise be poisoned by one gap). Returns a full-trace peak-index array, possibly empty; `None`
  on a degenerate window. Pure, never raises. This is exactly the "peaks + valleys with prominence
  so it doesn't stick at a local minimum" the phase set out to build.
- **Seven kick metrics** compute + registered `implemented` (`kick_count`, `kick_tempo`,
  `kick_consistency`, `dist_per_kick`, `per_kick_decay`, `first_kick_impulse`, `uw_ivv`).
  `uw_ivv` is window-only (no peaks) so it survives a peakless window; the others degrade to `None`
  by peak count. Breaststroke and every 75-02 output stay byte-identical (AC-3 guard held).

### AC-4 eyeball verdict (human-reviewed on live DB traces) — **APPROVED**
Reviewed all 33 annotated non-breaststroke sessions on their **ground-truth (annotation) windows**
(`tools/plot_kicks.py --annotated-only`), because the raw contact sheet was dominated by boundary
failures, not kick errors (see Part B). On correct windows the marked peaks are the downkicks a
coach would count — clean across butterfly and freestyle. Two known-limitation cases logged, **not
blockers** (hypothesis 1 accepted without a hypothesis 2):
- `8a51ece7` (free) — shallow ~1.2–1.5 m/s oscillations, possible ripple counted as kicks.
- `b8cb1e36` (`udk`) — alternating tall/short peaks; the short intermediate bumps may be up-kicks,
  so count can inflate ~2× on pure UDK sets.

## Part B — the boundary fix (surfaced by AC-4, not in the original plan)
The eyeball first showed impossible counts (e.g. 23 "kicks" underwater). Root cause was NOT the kick
detector but the window's right edge: **`stroke_start_s` was stale on every stored session — median
3.56 s off annotation** — because it flowed from the stored `initial_phase_end_idx`, which only the
raw-CSV `compute_session_metrics` path writes. `resolve_boundaries` had a `detected` branch for
`dive_start` (79) and `underwater_start` (75-02) but **not** for `stroke_start`/`finish`, and
`build_seed` read the legacy `initial_phase_end_idx`. So `backfill_phases.py --apply` /
`POST /recompute` (which only re-run `compute_phases`) **could not refresh it** — contradicting the
then-current STATE owed-item 6.

**Fix:**
- **`metrics.detect_swim_boundaries(t, vel, stroke_type) -> (stroke_start_idx, finish_idx)`** — a
  pure standalone mirroring the rhythm-window + Phase 76/77 breakout block of
  `compute_session_metrics` (the hot path is left untouched — surgical). Degenerate traces →
  `(None, None)`; `finish` clamped to the last sample so it maps in-range.
- **`resolve_boundaries`** now has a `detected` branch calling it for **both** `stroke_start_s` and
  `finish_s` (manual annotation still wins; seed is the fallback only when detection returns None).
  So the backfill and `/recompute` now refresh **all four** boundaries from live detectors with no
  raw-CSV read.
- **Result:** auto-path `stroke_start` error **3.56 s → 0.40 s** vs annotation (n=33) — the live
  breakout quality (free 0.42 s / fly 0.38 s) now actually reaches stored sessions.
- **Drift guard:** `tests/test_phase_metrics.py::test_detect_swim_boundaries_matches_pipeline` pins
  the standalone to `compute_session_metrics` ip_end on the 4 ground-truth fixtures, so the
  duplicated logic can't silently diverge.

## Tests
`pytest tests/` = **426 passed**. 5 boundary-metric tests updated to the new contract (stroke_start/
finish are now detector-resolved, not seed-or-null); their None-window coverage preserved via
monkeypatch. Drift-guard test added.

## Owed
- ✅ **Backfill applied 2026-08-21** (user-run `python tools/backfill_phases.py --apply`): all four
  boundaries re-resolved from live detectors across the stored library — corrected `stroke_start`/
  `finish` + the 75-03 kick metrics landed. Comparability break closed, standing pattern.
- The two Part-A over-detection cases (`udk`, shallow-freestyle) if they ever bite a real report.
