---
phase: 65-underwater-phase-detection
plan: 02
subsystem: signal-processing
tags: [segmentation, cwt-ridge, detect_swim_window, low-band-bias, breakout, ip_end]

requires:
  - phase: 65-underwater-phase-detection
    provides: 65-01-FINDINGS (Mode C = low-railed f_ref; Option A decision) + the probe
  - phase: 59-segmenter-evaluation
    provides: detect_swim_window, _cwt_ridge, _track_ridge, the fixture regression harness
provides:
  - detect_swim_window low-rail de-bias guard (the "indigo ray" fix)
  - _cwt_ridge / _track_ridge low_band_bias parameter (default-preserving)
  - _window_from_ridge helper (extracted, byte-identical settle body)
  - _WINDOW_FMIN_HZ = 0.45 (plausible-stroke floor, measured)
affects: [65-03, 69-freestyle-breakout-placement]

tech-stack:
  added: []
  patterns:
    - "Fix a shared primitive via a default-preserving PARAMETER, not a global change, when only one of its callers is broken"
    - "Gate a stroke-agnostic detector's new behaviour on stroke_type to honour a per-stroke exemption"
key-files:
  created: [.paul/phases/65-underwater-phase-detection/65-02-PLAN.md, .paul/phases/65-underwater-phase-detection/65-02-SUMMARY.md]
  modified: [metrics.py, tests/test_metrics.py, tools/underwater_probe.py]
key-decisions:
  - "_WINDOW_FMIN_HZ = 0.45 — set from data (rail 0.33 < 0.45 < lowest legit fired f_ref 0.72)"
  - "Breaststroke EXEMPT via a threaded stroke_type (one-line change at compute_session_metrics:774) — honours phase D2"
  - "No fixture re-baseline — all 4 fixtures had plausible f_ref, so the guard fires on none"
patterns-established:
  - "The guard fires ONLY below the floor, so non-railed sessions are byte-identical by construction"
duration: ~1 session
started: 2026-08-17
completed: 2026-08-17
---

# Phase 65 Plan 02: Underwater Breakout Fix — detect_swim_window low-rail guard

**Repaired the reported "dive + underwater kicks segmented as stroke cycles" bug ("indigo ray") by
giving `detect_swim_window` a de-bias guard: when its CWT-ridge `f_ref` rails below `_WINDOW_FMIN_HZ`
(0.45 Hz) it recomputes the ridge with `_track_ridge`'s low-band bias removed and re-derives the
window — so `ip_end` stops collapsing onto `b_end`. Indigo ray: `ip_end` 2.7→7.1 s, 15→10 cycles.
The shared ridge is untouched (a default-preserving `low_band_bias` param), breaststroke is exempt,
and the 12-session corpus is byte-identical.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~1 session |
| Completed | 2026-08-17 |
| Tasks | 3 (2 auto + 1 human-verify) |
| Files modified | 3 code/tools + 2 plan docs |
| Suite | 282 passed |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Mode-C window excludes the underwater kicks | Pass | indigo ray `ip_end` 2.7→**7.1 s**, cycles 15→**10**, `source` stays `swim_window` (not the 16.6 s trough fallback). A **2nd butterfly rail** was also found + fixed in the cross-stroke sweep. |
| AC-2: Mode-A sessions byte-identical | Pass | 12-session corpus: every `final_ip`/`cyc`/`source` matches the 65-01 baseline. `d25c578f` tried the recompute and correctly declined (0.26→0.28, still railed) → unchanged. |
| AC-3: Shared ridge untouched | Pass | `_cwt_ridge(vel, fs)` elementwise-identical (test); fixture regression `test_scores_are_unchanged` GREEN with **zero re-baseline**; full suite 282. |

## Accomplishments

- **The reported bug is fixed at its mechanism.** `_track_ridge`'s `_RIDGE_LOW_BAND_BIAS` tipped a
  weak stroke fundamental to the CWT floor (indigo ray f_ref 0.33 Hz vs a real ~0.9); the guard
  recomputes de-biased (f_ref 0.88) and the window lands after the kicks.
- **Surgical by construction.** The guard fires ONLY when f_ref < 0.45, and de-biasing is a near-no-op
  on non-railed ridges (Δf_ref ≤ 0.09 across all 10 plausible corpus sessions), so nothing that
  already worked moved. Cross-stroke sweep: 2/16 sessions changed, both butterfly rails.
- **Zero collateral.** The shared `_cwt_ridge` is byte-identical on its bare call, so
  `segment_cycles_wavelet`, the dispatch/regularity gates, and all four fixture "production" rows are
  unchanged — no re-baseline was needed.

## Task Commits

Committed as a single plan commit (not per-task): **`feat(65-02): swim-window low-rail de-bias guard`**
covering `metrics.py` + `tests/test_metrics.py` + `tools/underwater_probe.py` + the plan/summary +
STATE/ROADMAP.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `metrics.py` | Modified | `low_band_bias` param on `_track_ridge` + `_cwt_ridge` (default `_RIDGE_LOW_BAND_BIAS`); new `_WINDOW_FMIN_HZ = 0.45`; extracted `_window_from_ridge` (byte-identical settle body, returns `(window, f_ref)`); de-bias guard + `stroke_type` param in `detect_swim_window`; one-line `stroke_type` pass at `compute_session_metrics:774` |
| `tests/test_metrics.py` | Modified | `TestSwimWindowLowRail` — default-bias identity, de-bias-raises-ridge (real data), guard no-op on plausible/back-compat, and a deterministic guard-fires + breaststroke-exempt test (stubbed ridge) |
| `tools/underwater_probe.py` | Modified | De-bias diagnostic: `_fref_ip` (via the new `_window_from_ridge`) + the biased-vs-de-biased lever table |
| `.paul/phases/65-underwater-phase-detection/65-02-PLAN.md` | Created | The plan |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| `_WINDOW_FMIN_HZ = 0.45` | Task-1 measured the rail at 0.33 Hz and the lowest legit *fired* f_ref at 0.72 Hz; 0.45 separates them with wide margin both sides | The 65-01 note's "0.51" was a looser-window artifact; the faithful floor is comfortably below 0.72 |
| Breaststroke exempt via threaded `stroke_type` | `detect_swim_window` is stroke-agnostic; a slow legitimate breaststroke can sit near the floor, and D2 requires breaststroke byte-identical | Guard never evaluates breaststroke; the 5-session breaststroke sweep confirmed 0 moved |
| Fix via a `low_band_bias` PARAMETER, not a global bias change | `_cwt_ridge` is shared with `segment_cycles_wavelet` (cycle counting, tuned in 59); only `detect_swim_window` is broken | Segmenter + fixture untouched; blast radius bounded to the swim window |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Scope additions | 1 | Threaded `stroke_type` (+1-line at :774) — justified, honours D2 |
| Plan-doc fixes | 2 | Corrected a fabricated placeholder uuid; probe `_fref_ip` rewritten |
| Deferred | 1 | TODO #69 (freestyle-early residual) logged to ROADMAP |
| Positive (avoided work) | 1 | No fixture re-baseline needed |

**Total impact:** Essential, no scope creep. The one behavioural addition (breaststroke exemption)
strengthens the fix.

### Auto-fixed / Scope additions

**1. Threaded `stroke_type` into `detect_swim_window`**
- **Found during:** Task 1 measurement — `69f33669` in the fixture is breaststroke, and the guard is
  stroke-agnostic, so a legitimately slow breaststroke (~0.4–0.6 Hz) could rail below the floor and
  wrongly trigger the recompute, violating phase D2 (breaststroke byte-identical).
- **Fix:** `detect_swim_window(t, vel, stroke_type=None)`; the guard is gated on
  `stroke_type != "breaststroke"`; `compute_session_metrics` passes `stroke_type` (one line at :774,
  inside the range the plan's boundary named "do not touch"). Default `None` → eligible, so the probe
  and the fixture scorer (bare 2-arg calls) behave exactly as measured.
- **Verification:** `test_guard_is_noop_on_a_plausible_session` (breaststroke==default==butterfly) +
  the 5-session breaststroke sweep (0 moved).

**2. Probe `_fref_ip` rewritten**
- **Issue:** Task 1's first cut toggled the module global `metrics._RIDGE_LOW_BAND_BIAS`; once Task 2
  made it a default arg (bound at def-time), that monkeypatch would silently use 0.5 for both calls.
- **Fix:** `_fref_ip` now passes `low_band_bias` explicitly to `_cwt_ridge` and runs the real
  `_window_from_ridge` — faithful and monkeypatch-free.

**3. Fabricated placeholder uuid corrected**
- The plan's Task-1/Task-3 verify steps carried an invented `6ececa0f-95a4-…` placeholder; recovered
  the real `6ececa0f-ac9e-4a20-95e9-6de0962dca1a` from the transcript and corrected the doc.

### Deferred Items

- **ROADMAP #69** — free/back breakout lands ~1–2 s EARLY on NON-railed sessions (Mode-A settle
  residual, NOT this fix). Raised at the human-verify. **Acceleration was evaluated as a lever and
  REJECTED** (it is `dv/dt` — no information independent of velocity; just as large during the
  kicks; differentiation is a high-pass that amplifies the kicks). Gate any future fix on ground
  truth (annotation + Phase 67 camera) first; promising code lever is a frequency step-down rule.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Windows console `cp1252` crash on a `→` in the probe print | Replaced with ASCII `->` |
| Could not synthesize a reliable "railed" signal for a unit test | Tested the guard's control flow deterministically with a stubbed `_cwt_ridge`; end-to-end rail correction is the real-data human-verify (probe on indigo ray) |
| Scratchpad viz script blanked by `open(f,"w").write(open(f).read())` (write truncates before read) | Rewrote with the path inlined; noted the trap |

## Next Phase Readiness

**Ready:** Phase 65-03 (underwater metrics + web reporting) can build on a correct `ip_end`. The fix
is display-affecting only for newly-processed/recomputed sessions.

**Concerns:**
- ⚠ **Stored sessions still show pre-fix numbers.** No DB write/backfill here (by scope); the web
  portal serves the old `metrics_json` until 65-03 recomputes/backfills — a comparability decision
  65-03 must make explicitly (the 6th such break lineage: 57 / 59-03 / 59-05 / 61-01 / … ).
- n is still tiny (1 swimmer, 4 annotated freestyle, **0 backstroke**, breaststroke exempt). The fix
  is validated on butterfly rails; backstroke has 1 session total in the DB and is unproven.
- The Mode-A late/early residual (#69) is untouched and is what a coach's eye will notice next on
  freestyle.

**Blockers:** None.

---
*Phase: 65-underwater-phase-detection, Plan: 02*
*Completed: 2026-08-17*
