---
phase: 16-freestyle-support
plan: 04
status: complete
completed: 2026-06-12
verdict: GO (invest further — user eyeball call at checkpoint)
---

# Summary: Wavelet/CWT stroke-rate ridge spike

## Verdict — GO

After three closed shape-matching spikes (16-01/02/03), the Morlet CWT ridge is
the standing path forward for stroke-agnostic segmentation. User reviewed the
11-session scalogram/ridge/rate comparison and called it **"good enough" — GO**:
the ridge is promising enough on the scalograms to invest in turning it into a
real implementation. This is the first non-"close" verdict in Phase 16.

**Important caveat recorded with the GO:** the *quantitative* breaststroke
calibration (the step meant to turn "the ridge looks smooth" into "the mechanism
reproduces a known-good answer" before trusting freestyle/fly) was **weak** — see
the table below. The GO is the user's eyeball judgment on the scalogram ridges
(row 2: whether the red ridge sits on a clean bright band), not a clean pass of
the numeric cross-check. The follow-up implementation plan must treat the
rate-accuracy and ceiling-railing problems below as open work, not solved.

## Breaststroke cross-check (step 3 — ground truth = segment_cycles troughs)

Ridge mean rate vs. production `stroke_rate_spm`, 8 breaststroke sessions:

| Session | trough cyc | prod SPM | ridge SPM | diff | ridge bounds |
|---|---|---|---|---|---|
| leo_br_1 | 22 | 41.4 | 36.8 | −4.6 ✓ | 14 vs 22 |
| sid_br_1 | 10 | 50.2 | 20.3 | −29.9 | 3 vs 10 |
| sid_br_2 | 10 | 54.0 | 65.2 | +11.2 | 12 vs 10 |
| jimmy_br_1 | 5 | 19.0 | 21.3 | +2.3 ✓ | 3 vs 5 |
| connor_br_1 | 8 | 26.0 | 42.1 | +16.1 | 8 vs 8 |
| connor_br_2† | 16 | 93.0 | 38.8 | −54.2 | 6 vs 16 |
| connor_br_3 | 10 | 33.9 | 35.8 | +2.0 ✓ | 7 vs 10 |
| connor_br_4 | 11 | 60.8 | 34.9 | −25.9 | 8 vs 11 |

† connor_br_2 = flagged sensor-dropout outlier (per `_track_ridge` code comment).

- **3 of 8 within ±5 SPM** (leo_br_1, jimmy_br_1, connor_br_3); the rest miss by
  11–54 SPM in **both** directions — not a fixable constant offset.
- **4 sessions rail into the 120-SPM search ceiling** (sid_br_2, connor_br_2,
  carlos_fr_1, lucas_fl_1) — the ridge locking onto a harmonic/noise band rather
  than a clean fundamental. The two `_PERIOD_*` bounds and the DP penalties
  (`_RIDGE_JUMP_PENALTY`, `_RIDGE_LOW_BAND_BIAS`) are the obvious tuning knobs.
- Ridge boundary counts diverge from trough counts almost everywhere (only
  connor_br_1 matches on count, and its rate is +16 SPM off).

## Freestyle/fly (step 4 — interpretable only in light of step 3)

| Session | trough cyc | prod SPM | ridge SPM | diff |
|---|---|---|---|---|
| carlos_fr_1 | 8 | 13.8 | 40.3 | +26.4 (railed ceiling) |
| carlos_fl_1 | 3 | 23.8 | 48.1 | +24.4 |
| swim_lucas_fl_1_…192933 | 11 | 43.0 | 36.7 | −6.3 |

These have no trough ground truth; the numbers are recorded but not trusted
given the breaststroke miss. The GO rests on the *qualitative* scalogram read,
which the user judged promising.

## What was built / run

- `wavelet_spike.py` — already code-complete entering this plan (Morlet
  `cmor1.5-1.0`, 3s rolling-mean detrend per CLAUDE.md "Wavelet notes";
  baseline/tail masking via `detect_phases`; DP ridge tracker with continuity +
  low-band-bias penalties replacing per-instant argmax; integer-phase-crossing
  boundaries via Φ(t)=∫rate dt'; Plotly 3-row × N-col comparison). **No code
  changes this plan** — this APPLY was the validation run + checkpoint.
- Ran on the 11-session set (8 breaststroke + carlos_fr_1, carlos_fl_1,
  swim_lucas_fl_1). All 11 rendered without errors → `wavelet_spike.html`.
- Env: `mySwimCoach` conda env (pywt 1.8.0, plotly 6.6.0). Standalone — no
  production file touched (`metrics.py`/`vel_acc_extraction.py` imported read-only).

## Acceptance criteria (plan Verification block)

| Criterion | Status |
|---|---|
| Scalogram + ridge render for all 11 sessions without errors | Pass |
| Breaststroke cross-check run + presented (boundaries + rate vs prod) | Pass (weak agreement, documented) |
| Freestyle/fly scalograms run + presented (3 sessions) | Pass |
| User checkpoint reached with clear go/no-go | Pass — **GO** |
| 16-04-SUMMARY.md written documenting verdict | Pass (this file) |

## Next phase readiness

**Ready:** Wavelet ridge is the chosen direction for freestyle/fly segmentation.
Mechanism (detrend → CWT → DP ridge → phase-crossing boundaries) is implemented
and produces output on all stroke types.

**Open work for the follow-up implementation plan (16-05, contingent on this GO):**
1. **Rate accuracy** — close the breaststroke gap to the trusted trough rate
   before trusting freestyle (tune scale range / DP penalties; investigate the
   ceiling-railing sessions; confirm whether part of the miss is a
   `stroke_rate_spm`-definition mismatch vs. a true ridge error).
2. **Boundary placement** — ridge-derived counts vs. trough counts.
3. Edge effects, merge with existing breaststroke trough logic, wiring into
   `metrics.py` — all explicitly out of scope for this spike.

**Blockers:** None. (Kick/pull sub-motion resolution, dive/pulldown re-masking,
pose/IMU/HMM work remain parked per 16-01/02/03.)

---
*Phase: 16-freestyle-support, Plan: 04 — Completed 2026-06-12*
