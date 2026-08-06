---
phase: 16-freestyle-support
plan: 05
subsystem: api
tags: [wavelet, cwt, pywt, segmentation, metrics, freestyle]
completed: 2026-06-12
status: complete
provides:
  - segment_cycles_wavelet — production cycle segmentation for all 4 strokes
  - segmentation_reliable flag (session + /process data_quality)
affects: [freestyle metrics tuning (future 16-06), iOS Coming-Soon gate, web portal]
key-decisions:
  - "Wavelet ridge is the SOLE segmenter for all strokes; trough kept, never called (user: no fallback)"
  - "Shipped at placeholder quality (segmentation_reliable=False); NO algo tuning this plan"
  - "Breaststroke test assertions kept strict — they pass under wavelet (12 strokes @ 50.0 SPM)"
duration: ~35min
---

# Phase 16 Plan 05: Wavelet ridge → production segmenter (placeholder ship)

**`segment_cycles_wavelet` (ported Morlet-CWT ridge) replaces the trough segmenter as the
sole cycle-segmentation engine for all four strokes in `compute_session_metrics`, shipped
deliberately at placeholder quality behind `segmentation_reliable=False`.**

## Acceptance Criteria Results

| AC | Status | Evidence |
|----|--------|----------|
| AC-1 wavelet is production segmenter, all strokes | Pass | Only `segment_cycles_wavelet` called (metrics.py:441); `segment_cycles_trough` present but uncalled; downstream metric code unchanged; 31 tests pass |
| AC-2 provisional flag exposed | Pass | `session["segmentation_reliable"]` is `False` (bool); `/process` `data_quality` carries it + a "segmentation is experimental — provisional" warning |
| AC-3 robustness + deps + tests | Pass | flat→None / short guards (no pywt crash); `python metrics.py processed/` exit 0, 0 crashes across 30 files; `PyWavelets` in requirements.txt; `pytest tests/` 31 passed |

## What Was Built / Modified

| File | Change | Purpose |
|------|--------|---------|
| `metrics.py` | `segment_cycles_wavelet()` + `_detrend_for_cwt`/`_track_ridge`/`_anchors_from_marks` + constants; swapped call at :441; `segmentation_reliable=False` in session; dead `T_est` line removed | Production wavelet segmentation engine |
| `api.py` | `segmentation_reliable` in `data_quality` + provisional warning | Surface placeholder status to clients |
| `requirements.txt` | `PyWavelets` added | Railway server-side `import pywt` |
| `tests/test_metrics.py` | `segmentation_reliable` in EXPECTED_SESSION_KEYS + `test_segmentation_reliable_always_false` | Re-baseline to wavelet engine |
| `CLAUDE.md` | metrics.py section: wavelet = production segmenter, trough = never-called backup | Doc accuracy |

## Verification Results

```
pytest tests/                  → 31 passed
python metrics.py processed/   → exit 0, 0 crashes / 30 files
breaststroke_sample (wavelet)  → 12 strokes @ 50.0 SPM  (within strict 10–60 bound)
freestyle/fly now segment      → carlos_fr_1=17, carlos_fl_1=8, swim_lucas_fl_1=3 cycles
flat/short edge cases          → segment_cycles_wavelet → None (no CWT crash)
```

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Wavelet sole segmenter, trough never called | User: "replace all 4 strokes; trough = invisible backup; no fallback" | One unified engine; trough is reference-only |
| Ship placeholder, no tuning | User: "not enough data; ship as placeholder" | Known breaststroke regression accepted; `segmentation_reliable=False` |
| Kept breaststroke test assertions strict | Wavelet did NOT break the 10–60 SPM bound (50.0) | Better coverage than the plan's fallback-to-loosen |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Scope additions | 0 | — |
| Plan-anticipated, not needed | 1 | Test loosening (plan allowed it; unneeded — kept strict) |
| Env hygiene | 1 | Installed pytest+httpx+stripe into mySwimCoach (all already in requirements*.txt — env was missing them; NOT a code/requirements change) |

`T_est` dead-line removal was executed exactly as the plan specified (grep confirmed
`_estimate_period` still has readers in pipeline_view.py + the spikes, so the function
stays defined; only the now-unused local assignment was dropped).

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| `No module named pytest/stripe` in mySwimCoach env | Installed the already-declared deps; suite then green |

## Next Phase Readiness

**Ready:** Wavelet ridge is live in the production pipeline for all strokes; freestyle/fly
now produce cycle-level metrics (were silently running the wrong trough engine).

**Concerns (deferred tuning — a future 16-06):**
- Breaststroke regression shipped knowingly: 16-04 cross-check was 3/8 within ±5 SPM.
- Ceiling-railing on some sessions (ridge locks onto a harmonic at 120 SPM); freestyle
  rates look high (carlos_fr_1 ≈ 75 SPM) — all provisional, flagged.
- Tuning knobs: scale range (`_PERIOD_MIN/MAX_S`), `_RIDGE_JUMP_PENALTY`,
  `_RIDGE_LOW_BAND_BIAS`; and confirm how much of the breaststroke miss is a
  `stroke_rate_spm`-definition mismatch vs. true ridge error.

**Blockers:** None.

**Deploy note:** real backend code changed (metrics.py, api.py, requirements.txt). Railway
auto-deploys on push to main — so this reaches production the moment it's pushed. pywt
(PyWavelets) is a new Railway build dependency; confirm the build picks it up.

---
*Phase: 16-freestyle-support, Plan: 05 — Completed 2026-06-12*
