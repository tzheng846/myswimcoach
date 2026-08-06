---
phase: 16-freestyle-support
plan: 01
status: complete
---

# Summary: Matrix-profile motif-matching spike

## Verdict

Naive single-template matrix-profile motif-matching (`stumpy`: self-join → consensus
template → `match`) **does not produce usable stroke-cycle segmentation** on real
swim data. Two iterations surfaced two distinct, structural failure modes — neither
fixable by parameter tuning. See Recommendations for what viable machinery might
look like, and for an alternative direction that may sidestep the whole family of
problems.

## What was built

- `segment_motif_spike.py` — standalone diagnostic (matches `inspect_cycles.py`
  conventions) overlaying `segment_cycles_trough`'s trough-based cycles against
  `stumpy` motif-match anchors, plus the matrix-profile distance curve, across
  multiple sessions in one Plotly HTML page
- `stumpy` added to `requirements.txt` — installs and imports cleanly in the
  `mySwimCoach` env (Python 3.14.4, numpy 2.4.4, scipy 1.17.1; pulled in `numba`
  0.65.1 + `llvmlite` 0.47.0)

No production file was modified (`metrics.py`, `vel_acc_extraction.py`, `api.py`,
`CLAUDE.md` all untouched, per the plan's boundaries).

## Round 1 — baseline/tail hijacking (found, then fixed mid-spike)

First run (unmasked — full signal fed to `stumpy.stump`/`match`): anchors clustered
on the pre-swim baseline — "the red dots are concentrated on the baseline part where
there's noise but no real data" (user's read).

**Root cause:** z-normalized matrix-profile distance is degenerate on near-constant
subsequences. Subtracting the mean and dividing by std turns any near-flat window
into "trivially identical" to any other near-flat window, at distance ≈ 0 — *lower*
than the natural distance between genuine, varying stroke cycles — so `argmin` locks
onto the flattest region in the whole recording. Empirical proof: in `leo_br_1` and
`carlos_fr_1` the chosen "consensus template" window measured **std = 0.00000**
(literally zero variance) and sat inside the pre-swim baseline; `carlos_fl_1`'s sat
right at the baseline→swim transition (std = 0.196). This is a named, documented
pathology in matrix-profile literature (the "constant/flat-subsequence problem").

**Fix applied:** mask the pre-swim baseline and post-swim tail with `NaN` before
`stump`/`match`, using the *same* `baseline_end`/`swim_end` boundaries the production
pipeline already computes via `metrics.detect_phases` — no new threshold logic
introduced. `stumpy` has documented NaN handling: any window touching NaN is assigned
`inf` distance, so both template selection (`argmin` naturally ignores `inf`) and
matching stay confined to the active-swim region, with every index still expressed in
the original array's coordinates (no slicing/offset bookkeeping needed). Confirmed
mechanically working on re-run — every session's `template_idx` now lands inside
`[baseline_end, swim_end)`:

| session | masked baseline → tail | template_idx | in active region? |
|---|---|---|---|
| leo_br_1 | [0:1094] → [3270:3376] | 2391 | yes |
| carlos_fr_1 | [0:361] → [2028:2134] | 1714 | yes |
| carlos_fl_1 | [0:228] → [1093:1093] (no tail) | 444 | yes |
| swim_lucas_fl_1 | [0:899] → [1977:2063] | 1875 | yes |

## Round 2 — single-template "regime-locking" (the deeper finding)

With the baseline fixed, anchors moved into the active-swim region — but landed on
only a *subset* of genuine strokes, consistently in one contiguous stretch rather
than spread across the whole swim. Visual judgment per session (user's read):

- **leo_br_1** (breaststroke, cleanest data): "detected segmentation of all the fast
  paced stroke. The slower paced ones were undetected." (11 motif anchors vs. 22
  trough cycles)
- **carlos_fl_1** (butterfly): "detected first 4 strokes, but a change in
  speed/amplitude caused it to fail." (6 motif anchors vs. 3 trough cycles — more
  anchors than trough cycles, but concentrated in the first half only)
- **swim_lucas_fl_1** (butterfly): same pattern — anchors clustered tightly around one
  high-amplitude burst rather than spread across the active region the way the trough
  markers are (6 vs. 11 trough cycles)
- **carlos_fr_1** (freestyle): "was bad, but I don't blame it since the data looks
  terrible, even I can't tell by human eye" — a data-quality issue, not an algorithm
  failure; the user explicitly separated this from the method's performance
- **swim_lucas_fr_1_20260515_192607**: excluded from this round per user direction
  ("don't use swim_lucas_fr_1 — the other three are fine")

**Root cause:** the self-join's single global-minimum template captures *one* local
regime — a specific pace/amplitude/shape — and `stumpy.match` then only finds
recurrences of *that exact shape*. Real swim sessions aren't stationary: pacing,
fatigue, and effort drift stroke shape over the course of a swim, so "one consensus
template represents every stroke in a session" is a false premise. Compounding this:
the match window length `m_len` is **fixed** — derived once from a single global
`T_est`. Z-normalization corrects for amplitude and offset, but *not* for the shape
distortion that occurs when stroke *rate* drifts enough that a fixed-length window
captures a different fraction of a cycle at different points in the swim — exactly
the kind of drift "speed/amplitude changes" produce. Neither factor is a tuning knob;
both are structural to the single-template/fixed-window design.

**Mechanistic link between the red anchors and the purple matrix-profile curve**
(established when the user asked how to read the relationship): every match is
*guaranteed* to sit at a relatively low point in the MP curve, since matching the
template caps the self-join distance from above (`mp[j] <= distance(window_j, Q)`).
The converse doesn't hold — a low MP value does *not* guarantee a match, because that
window's true nearest neighbor may be some *other* recurring shape entirely.
`leo_br_1`'s MP curve shows roughly-periodic dips reaching back to ~t=14s — well
before the red anchors start around t=20s — which is likely the signature of exactly
that: the slower early strokes resembling *each other*, a second shape-family the
single-template approach is structurally blind to.

## Recommendations for Plan 16-02 (ranked)

1. **Wavelet/CWT stroke-rate ridge (recommended).** `CLAUDE.md`'s existing "Wavelet
   notes" already document that a Morlet CWT (`cmor1.5-1.0`) on detrended velocity
   produces "a clean stroke-rate ridge" (exploratory code already exists in
   `vel_acc_extraction_testing3.py`). This reframes segmentation from "does this
   window's *shape* resemble that window" (which broke twice here) to "what's the
   dominant oscillation frequency *right now*" — a question that doesn't degenerate
   on flat regions, doesn't care about velocity dead-spots, and *naturally* tracks
   rate drift (a ridge is defined as time-varying — pacing/fatigue shifts are exactly
   what it follows). Mechanism to get from ridge to boundaries: integrate
   instantaneous rate into cumulative phase `Φ(t) = ∫rate(t')dt'`, place a boundary
   at each integer crossing (the same idea used to derive heartbeat boundaries from a
   time-varying heart-rate signal). Real work remains — a ridge gives rate, not exact
   phase alignment, so a peak-picking step near each crossing is still needed — but
   it sidesteps both structural problems found in this spike.

2. **`stumpy.motifs()` (multi-template).** The documented next tool in the same
   library: finds *K* motif groups instead of one, directly targeting "one template,
   one regime." Ranked lower because it's a new spike's worth of open questions (how
   many motifs? how do overlapping matches from different templates reconcile into
   one coherent cycle list?), and because real pacing/fatigue drift is likely
   *continuous* rather than a clean switch between discrete regimes — multi-motif may
   just shrink the blind spot rather than close it.

3. **Orthogonal — relax the precision bar for a freestyle V1.** Several
   session-level metrics (`stroke_rate_spm`, `mean_vel_ms`, `max_vel_ms`,
   `fatigue_index_pct`) could plausibly come from a periodicity/frequency estimate
   *without ever detecting a cycle boundary* — only the genuinely per-cycle metrics
   (`cv_arm_peak_vel`, `mean_isi_s`, `mean_dps_m`, `mean_coast_fraction`, etc.)
   strictly require segmentation. Shipping the frequency-derivable subset for
   freestyle first, while exact per-cycle segmentation stays an open thread, could
   close the "missing freestyle" commercial gap sooner than waiting on a fully
   general breakthrough.

Pose/IMU sub-phase work and HMM labeling remain correctly parked — both blocked on
data that doesn't yet exist (the pose pipeline), not "from here" options.
