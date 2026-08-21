"""
metrics.py — Breaststroke feature extraction from processed tether-wheel data.

Inputs:  t (s), vel (m/s), dist (m) as numpy arrays at a uniform sample rate.
Outputs: dicts from compute_session_metrics() and segment_cycles().

All functions are pure (no I/O, no plots).
"""

import argparse
import numpy as np
import pandas as pd
import pywt
from pathlib import Path
from scipy.signal import find_peaks
from scipy.integrate import trapezoid
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

SESSION_STEM = "leo_br_1"

# ── tuning constants ────────────────────────────────────────────────────────
_BASELINE_THRESH     = 0.05   # rolling-mean |vel| below this → baseline (m/s)
_BASELINE_WIN_S      = 1.0    # window length for baseline detection (s)
_PEAK_HEIGHT_FRAC    = 0.30   # arm-pull peak must exceed this × v95
_PEAK_DIST_FRAC      = 0.75   # minimum gap between consecutive peaks (× T_cycle)
_PEAK_MIN_PROM_FRAC  = 0.10   # min prominence for any peak (pull or kick) × v95
_DEAD_SPOT_THRESH    = 0.10   # |vel| below this × v95 → dead spot
_COAST_FRAC_THRESH   = 0.50   # |vel| below this × arm_peak_vel → coasting (per cycle)


def _window_v95(vel, start, end):
    """95th percentile of |vel| over the half-open window [start, end) — Phase 57.

    v95 is the scale every velocity threshold in this module is expressed in. It used
    to be taken over the FULL trace, but a recording keeps running after the swimmer
    touches, so a long near-zero tail dragged the percentile down and with it every
    threshold scaled by it. Windowing removes that bias.

    An empty window falls back to the full trace: a pure metric function must degrade
    rather than raise on a degenerate annotation.
    """
    seg = vel[start:end]
    if len(seg) == 0:
        return float(np.percentile(np.abs(vel), 95))
    return float(np.percentile(np.abs(seg), 95))


# ── SEGMENTATION ─────────────────────────────────────────────────────────────

def detect_phases(t, vel):
    """
    Identify baseline and swimming regions.

    Returns dict with integer indices into t/vel:
        baseline_end   – last index of the near-zero baseline
        steady_start   – same as baseline_end (kept for callers; no per-cycle split
                         exists since Phase 61-01 removed the steady/ramp_up tagging)
    """
    fs  = _compute_fs(t)
    win = max(1, int(_BASELINE_WIN_S * fs))
    rm  = pd.Series(np.abs(vel)).rolling(win, min_periods=1).mean().values

    # Find first sustained crossing above threshold (held for 0.5 s)
    hold   = max(1, int(0.5 * fs))
    b_end  = 0
    for i in range(len(t) - hold):
        if np.all(rm[i : i + hold] > _BASELINE_THRESH):
            b_end = i
            break

    # swim_end: last sample where rolling mean is above threshold + 0.5 s grace
    # to include the final glide. Using single-sample check avoids cutting off
    # the last stroke because the sustained-window check misses its glide phase.
    swim_end = len(t)
    for i in range(len(t) - 1, b_end, -1):
        if rm[i] > _BASELINE_THRESH:
            swim_end = min(i + hold + 1, len(t))
            break

    return {"baseline_end": b_end, "steady_start": b_end, "swim_end": swim_end}



def segment_cycles_trough(t, vel, T_est=None):
    """
    Segment at deep velocity troughs (glide phase) — literature-recommended
    approach for breaststroke.

    The tethered-wheel velocity drops near zero during each glide; those deep
    minima are unambiguous cycle boundaries and are immune to the arm+kick
    double-peak problem.  The dominant peak within each trough-bounded segment
    becomes the stroke anchor.

    T_est: autocorrelation-estimated stroke period (s). When provided, the
    minimum trough separation becomes 0.5 × T_est (adaptive to the swimmer's
    own tempo). Falls back to 0.5 s (120 SPM hard cap) if T_est is None.

    Returns same format as segment_cycles, or None if fewer than 2 qualifying
    troughs are found.
    """
    fs  = _compute_fs(t)
    n   = len(vel)
    v95 = float(np.percentile(np.abs(vel), 95))

    # Minimum trough separation: adaptive when T_est is available, otherwise
    # use 0.5 s (120 SPM — faster than any realistic breaststroke).
    min_sep_s = max(0.3, 0.5 * T_est) if T_est is not None else 0.5

    troughs, _ = find_peaks(
        -vel,
        height   = -0.20 * v95,                    # vel must be < 0.20 × v95
        distance = max(1, int(min_sep_s * fs)),
    )

    if len(troughs) < 1:
        return None

    # Prepend start + append end as virtual boundaries so both the first stroke
    # (swim-start → first trough) and last stroke (last trough → swim-end)
    # are captured, not skipped.
    bounds = np.concatenate([[0], troughs, [len(vel)]])

    cycles = []
    for i in range(len(bounds) - 1):
        a, b = int(bounds[i]), int(bounds[i + 1])
        seg  = vel[a:b]
        if len(seg) < 2:
            continue
        pk = a + int(np.argmax(seg))
        cycles.append({"cycle_num": len(cycles), "peak_idx": pk, "start_idx": a, "end_idx": b})

    return cycles if len(cycles) >= 1 else None


# ── WAVELET SEGMENTATION (production engine, all strokes — Phase 16-05) ────────
# Ported from wavelet_spike.py (16-04 GO). Morlet CWT ridge → instantaneous
# stroke rate → integer-phase-crossing cycle boundaries. Shipped at PLACEHOLDER
# quality (session["segmentation_reliable"] = False): the 16-04 breaststroke
# cross-check was weak (3/8 within ±5 SPM). Still the default for every stroke,
# but no longer hardcoded — Phase 59-02 made routing table-driven; see
# SEGMENTER_BY_STROKE below. segment_cycles_trough above is not called from the
# pipeline; it is a scored candidate for Phase 59-04.

_WAVELET          = "cmor1.5-1.0"
_DETREND_WINDOW_S = 3.0
_PERIOD_MIN_S     = 0.5
_PERIOD_MAX_S     = 4.0
_N_SCALES         = 80

# DP ridge-tracker penalties (empirical derivation documented in wavelet_spike.py):
# jump penalty stops a single harmonic-spike frame from winning a jump-and-back;
# low-band bias tips a close two-band call toward the slower (outer stroke) cycle.
_RIDGE_JUMP_PENALTY  = 4.0
_RIDGE_LOW_BAND_BIAS = 0.5


def _detrend_for_cwt(vel, fs):
    """Subtract a centered 3-second rolling mean — the documented fix for the
    near-zero dark-node artifact a raw-velocity CWT produces (velocity genuinely
    touches near-zero between strokes; detrending removes that so the transform
    sees oscillation shape, not absolute level)."""
    window = max(3, int(round(_DETREND_WINDOW_S * fs)))
    rolling_mean = pd.Series(vel).rolling(window, center=True, min_periods=1).mean().values
    return vel - rolling_mean


def _track_ridge(power, freqs_hz, low_band_bias=_RIDGE_LOW_BAND_BIAS):
    """
    Continuity- and low-band-biased ridge extraction via dynamic programming —
    replaces a per-instant argmax(power) that can snap onto a harmonic for a few
    frames and has no way to prefer one of two simultaneously-loud bands.

    node_cost[f,t] = -log(col-normalized power) + low_band_bias*log_freq[f]
    cost[f,t]      = min_f'{ cost[f',t-1] + LAMBDA*(logfreq[f]-logfreq[f'])^2 } + node_cost[f,t]

    Frequencies compared in log-space (pywt scales are geometric). Returns the
    optimal scale-index path — same shape/role as argmax(power, axis=0).

    low_band_bias defaults to _RIDGE_LOW_BAND_BIAS (0.5) — passing anything else is a
    Phase 65-02 seam: detect_swim_window recomputes the ridge with bias=0 when the
    production ridge rails to the low-frequency floor. Every other caller omits it, so
    their ridge is byte-identical to before the seam existed.
    """
    n_scales, n_times = power.shape
    log_freqs = np.log(freqs_hz)
    jump_cost = _RIDGE_JUMP_PENALTY * (log_freqs[:, None] - log_freqs[None, :]) ** 2  # [from, to]

    col_max   = np.maximum(power.max(axis=0, keepdims=True), 1e-12)  # floor guards all-zero columns
    log_pow   = np.log(power / col_max + 1e-12)
    node_cost = -log_pow + (low_band_bias * log_freqs)[:, None]

    cost    = np.empty((n_scales, n_times))
    backptr = np.empty((n_scales, n_times), dtype=np.int64)
    cost[:, 0] = node_cost[:, 0]

    for ti in range(1, n_times):
        totals = cost[:, ti - 1][:, None] + jump_cost
        backptr[:, ti] = np.argmin(totals, axis=0)
        cost[:, ti] = totals[backptr[:, ti], np.arange(n_scales)] + node_cost[:, ti]

    path = np.empty(n_times, dtype=np.int64)
    path[-1] = np.argmin(cost[:, -1])
    for ti in range(n_times - 1, 0, -1):
        path[ti - 1] = backptr[path[ti], ti]
    return path


def _cwt_ridge(vel, fs, low_band_bias=_RIDGE_LOW_BAND_BIAS):
    """Detrended velocity → (ridge_freq_hz, ridge_power) along the DP-tracked ridge.

    Extracted in Phase 59-03 because TWO callers now need the same ridge and must not
    drift apart if _WAVELET or the scale grid ever changes:
      * segment_cycles_wavelet integrates the frequency to count cycle boundaries
        ("how many strokes have gone by") — needs precision.
      * detect_swim_window asks whether the frequency is STEADY ("is this rhythm
        stroking, kicking, or nothing") — needs only coarse discrimination.
    Same signal, two different questions, very different precision requirements.

    low_band_bias passes straight through to _track_ridge; it defaults to the production
    value so segment_cycles_wavelet's bare call is byte-identical. detect_swim_window
    passes 0.0 only when its production ridge rails low (Phase 65-02).

    Returns (None, None) on short or flat input — the caller decides what that means.
    """
    if len(vel) < max(50, int(_PERIOD_MAX_S * fs)):
        return None, None
    active = _detrend_for_cwt(vel, fs)
    if not np.any(np.isfinite(active)) or float(np.max(np.abs(active))) < 1e-6:
        return None, None

    dt = 1.0 / fs
    target_freqs = np.geomspace(1.0 / _PERIOD_MAX_S, 1.0 / _PERIOD_MIN_S, _N_SCALES)
    scales       = pywt.central_frequency(_WAVELET) / (target_freqs * dt)

    coeffs, freqs_hz = pywt.cwt(active, scales, _WAVELET, sampling_period=dt)
    power = np.abs(coeffs) ** 2

    ridge_idx = _track_ridge(power, freqs_hz, low_band_bias)
    return freqs_hz[ridge_idx], power[ridge_idx, np.arange(power.shape[1])]


def _anchors_from_marks(vel, marks):
    """Boundary-mark indices → {cycle_num, peak_idx, start_idx, end_idx} anchors
    (dominant peak per span) — the same cycle shape segment_cycles_trough returns,
    so extract_cycle_peaks and the downstream metrics run unchanged."""
    bounds  = np.concatenate([[0], marks, [len(vel)]])
    anchors = []
    for i in range(len(bounds) - 1):
        a, b = int(bounds[i]), int(bounds[i + 1])
        seg  = vel[a:b]
        if len(seg) < 2:
            continue
        pk = a + int(np.argmax(seg))
        anchors.append({"cycle_num": len(anchors), "peak_idx": pk, "start_idx": a, "end_idx": b})
    return anchors


def segment_cycles_wavelet(t, vel):
    """
    PRODUCTION cycle segmentation for ALL strokes (Phase 16-05).

    Morlet CWT on the 3-second-detrended velocity → per-instant dominant
    frequency (instantaneous stroke rate) via a DP-tracked ridge → cumulative
    phase Φ(t)=∫rate dt' → a cycle boundary at each integer crossing.

    Operates on the already-masked slice the caller passes (NO internal
    detect_phases re-masking — compute_session_metrics hands in
    vel[ip_end:swim_end]). Returns slice-relative indices in the same format as
    segment_cycles_trough — list[{cycle_num, peak_idx, start_idx, end_idx}] — or
    None when the input is too short or has no oscillation (mirrors the trough
    None-path so the caller's `if cycles is None: cycles = []` still applies).
    """
    n = len(vel)
    if n < 50:
        return None
    fs = _compute_fs(t)

    # Guard (inside _cwt_ridge): need at least one longest-period window, and an actual
    # oscillation. A flat signal detrends to ~0 → the CWT has no ridge and _track_ridge
    # would divide by an all-zero column. That is the flat/short path.
    ridge_freq, _ = _cwt_ridge(vel, fs)   # Hz = instantaneous stroke rate
    if ridge_freq is None:
        return None

    # Cumulative phase; a boundary at each integer crossing (slice-relative index).
    phase    = np.concatenate(([0.0], np.cumsum(ridge_freq[:-1] * np.diff(t))))
    marks    = []
    n_target = 1
    for i in range(1, len(phase)):
        if phase[i - 1] < n_target <= phase[i]:
            marks.append(i)
            n_target += 1
    marks = np.array(marks, dtype=np.int64)

    anchors = _anchors_from_marks(vel, marks)
    return anchors if len(anchors) >= 1 else None


# ── LEARNED BOUNDARY DETECTOR (Phase 59-05) ──────────────────────────────────
#
# Logistic regression over a 5-feature window stack, predicting "is this sample an arm
# entry". Fitted in tools/segmenter_candidates.py on all 20 scorable annotated sessions —
# the same protocol 59-04's leave-one-session-out numbers came from.
#
# ⚠ NO sklearn IN PRODUCTION, DELIBERATELY. Inference is a dot product and a sigmoid; the
# numpy form below was verified to reproduce sklearn's predict_proba to 1.1e-16 across all
# 20 sessions. sklearn stays in tools/ for FITTING only. The weights are a CONSTANT BLOCK
# rather than a loaded artifact, so there is no model file to version, ship, or lose.
# To retrain: re-run tools/segmenter_candidates.py and replace these two constants.
#
# ⚠ 59-04 measured this LOSO vs in-sample at 0.591/0.600 (butterfly) — it does NOT overfit,
# because 5 features cannot memorise 236 marks. That is a property of THIS model's tiny
# capacity and is NOT a license to fit a bigger one on the same corpus.
_LEARNED_COEF      = np.array([0.6976347336, 1.5399329061, 0.2073524188,
                               -0.1574910741, 1.1872824453])
_LEARNED_INTERCEPT = -1.0419426935241078
_LEARNED_FEAT_WIN_S = 0.15
_LEARNED_MIN_PROB   = 0.5


def _learned_features(vel, fs):
    """[v, dv, d2v, v-local_mean, local_std] per sample.

    ⚠ MUST match tools/segmenter_candidates.py::_features exactly. A silent divergence here
    does not raise — it just feeds the fitted weights inputs they were not trained on.
    """
    v  = np.nan_to_num(vel)
    d1 = np.gradient(v)
    d2 = np.gradient(d1)
    w  = max(3, int(_LEARNED_FEAT_WIN_S * fs))
    roll     = pd.Series(v).rolling(w, center=True, min_periods=1)
    loc_mean = roll.mean().values
    loc_std  = roll.std().fillna(0).values
    return np.column_stack([v, d1, d2, v - loc_mean, loc_std])


def _learned_boundaries(t, vel):
    """Cycle boundaries from the learned per-sample arm-entry probability.

    Same contract as every other segmenter: takes the already-sliced window, returns
    slice-relative cycle dicts, or None when it finds too little to work with.
    """
    if len(vel) < 50:
        return None
    fs = _compute_fs(t)
    p  = 1.0 / (1.0 + np.exp(-(_learned_features(vel, fs) @ _LEARNED_COEF
                               + _LEARNED_INTERCEPT)))
    period = _estimate_period(t, vel) or 1.0
    marks, _ = find_peaks(p, height=_LEARNED_MIN_PROB,
                          distance=max(1, int(0.6 * period * fs)))
    if len(marks) < 2:
        return None

    # ⚠ Cycles are built BETWEEN consecutive peaks — deliberately NOT via
    # _anchors_from_marks, which pads with 0 and len(vel). That padding is correct for
    # segment_cycles_wavelet (whose marks are interior phase crossings) but wrong here: the
    # peaks ARE the boundaries. Padding shifts every boundary one position and invents a
    # cycle starting at t=0, which drops boundary F1 to 0.000 while leaving the stroke RATE
    # looking fine — measured, not hypothetical.
    cycles = []
    for a, b in zip(marks[:-1], marks[1:]):
        if b - a < 2:
            continue
        cycles.append({"cycle_num": len(cycles), "start_idx": int(a), "end_idx": int(b),
                       "peak_idx": int(a) + int(np.argmax(vel[a:b]))})
    return cycles or None


def _pair_boundaries(base_segmenter, k):
    """Wrap a segmenter so every k-th boundary starts a cycle (Phase 59-03).

    Freestyle and backstroke ALTERNATE ARMS, so one cycle spans two arm entries. The
    wavelet emits a boundary at roughly each arm entry, and counting every one of them
    as a cycle is what made auto stroke_rate_spm read 1.48–2.08x (median ~1.75x) the
    human-derived value. Mirrors annotations.annotation_to_overrides' marks[0::k].

    ⚠ THE DIVISOR IS NOT annotations.MARKS_PER_CYCLE, AND MUST NOT BE IMPORTED FROM IT.
    That table is EXACT PHYSIOLOGY for HUMAN marks. Here, k=2 works only because THIS
    segmenter happens to emit boundaries at roughly arm-entry rate — an empirical
    property measured in 59-01 (1.15–1.5x the arm-entry count), not a physiological
    law. Swap the base segmenter in 59-05 and k must be re-measured, not assumed.
    """
    def paired(t, vel):
        cycles = base_segmenter(t, vel)
        if not cycles:
            return cycles
        bounds = [c["start_idx"] for c in cycles] + [cycles[-1]["end_idx"]]
        # ⚠ DROP _anchors_from_marks' LEADING PAD BEFORE PAIRING (fixed in 59-05).
        # segment_cycles_wavelet returns anchors padded with index 0, so the boundary list
        # is [0, m0, m1, ...]. Pairing indices 0,2,4 of THAT selects [0, m1, m3, ...] —
        # every cycle landing HALF A CYCLE out of phase with the arm entries. Measured on
        # 12 freestyle sessions: boundary F1 0.000 with the pad, 0.458 without it.
        # It went unnoticed because stroke_rate_spm is blind to it — the mean interval is
        # unchanged either way, which is why 59-03's rate gate passed at 1.00.
        if len(bounds) > 2 and bounds[0] == 0:
            bounds = bounds[1:]
        bounds = bounds[0::k]
        out = []
        for i in range(len(bounds) - 1):
            a, b = bounds[i], bounds[i + 1]
            if b - a < 2:
                continue          # degenerate span cannot carry per-cycle metrics
            out.append({"cycle_num": len(out), "start_idx": a, "end_idx": b,
                        "peak_idx": a + int(np.argmax(vel[a:b]))})
        return out or None
    return paired


# ── PER-STROKE SEGMENTER DISPATCH (Phase 59-02, populated 59-03) ──────────────
#
# An OVERRIDE table, not an exhaustive map. Anything absent resolves to the default.
#
# 59-02 shipped it EMPTY (proving the seam inert); 59-03 registered the two
# alternating-arm strokes. The BASE segmenter is unchanged for every stroke —
# freestyle and backstroke differ only in that their boundaries are paired into
# cycles. Choosing a different base per stroke is Phase 59-05's job.
#
# ⚠ Butterfly and breaststroke get NO pairing: they are 1 arm entry per cycle. 59-01
# measured butterfly over-counting at an UNSTABLE 1.18–2.18x the cycle count (the
# ridge sometimes locks onto the two-dolphin-kick harmonic), which no constant
# divisor can fix — that is 59-04/05's problem, not this one's.
#
# WHY THE SEAM EXISTS. Phase 59-01 scored the shipping segmenter against 23
# hand-annotated sessions for the first time and found that no two strokes want
# the same method — a 20-line peak-pick baseline beat the wavelet 2x on butterfly
# (recall 0.84 vs 0.41 at ±0.15 s) while the wavelet won on freestyle.
#
# WHY THE TABLE LIVES HERE AND NOT IN annotations.py. `annotations.MARKS_PER_CYCLE`
# is the LABELING convention (one mark = one arm entry; free/back = 2 per cycle).
# The number of BOUNDARIES a segmenter emits per cycle is a DIFFERENT quantity —
# 59-01 measured 1.15–1.5x the arm-entry count for freestyle and an unstable
# 1.18–2.18x the cycle count for butterfly. Sharing one table would conflate a
# human convention with an algorithm's behavior.
#
# REGISTRY CONTRACT — a value is a callable:
#     f(t, vel) -> list[cycle dict] | None
# It receives the ALREADY-SLICED vel[ip_end:swim_end] and returns slice-relative
# indices in segment_cycles_wavelet's dict shape; the caller offsets them to
# full-trace. None means "found nothing" and is handled by the caller.
# ⚠ segment_cycles_trough(t, vel, T_est=None) does NOT satisfy this signature.
# Wrap it (T_est from _estimate_period) rather than widening the contract.
SEGMENTER_BY_STROKE = {
    # Alternating arms: the wavelet emits ~1 boundary per ARM ENTRY, and 2 entries make a
    # cycle. 59-04 measured both challengers WORSE here on cycle regularity (L1 cv 0.121,
    # peakpick 0.246, vs the wavelet's 0.069 against a human 0.063) — so freestyle keeps it.
    "freestyle":  _pair_boundaries(segment_cycles_wavelet, 2),
    "backstroke": _pair_boundaries(segment_cycles_wavelet, 2),

    # ⚠ k=2 ON STROKES THAT ARE PHYSIOLOGICALLY *ONE* ARM ENTRY PER CYCLE. NOT A BUG.
    # It contradicts annotations.MARKS_PER_CYCLE (which says 1) and that is correct: `k` is
    # a property of the DETECTOR, not the stroke. This detector emits ~2.02 events per
    # butterfly cycle CONSISTENTLY, so every 2nd event lands one boundary per cycle at a
    # stable phase — measured cv 0.104 / alternation 0.090 against a human 0.055 / 0.056.
    # ⚠ `peakpick` was REJECTED here despite a better F1 (0.524 vs the wavelet's 0.317):
    # it emits an UNSTABLE ~2.5 events per cycle, so pairing drifts through phases
    # (alternation 0.276). Good boundary placement, meaningless cycles. See the regularity
    # gate in tests/test_metrics.py before swapping either of these.
    # ⚠ breaststroke rests on n=2 annotated sessions. Reverting is deleting this one line.
    "butterfly":    _pair_boundaries(_learned_boundaries, 2),
    "breaststroke": _pair_boundaries(_learned_boundaries, 2),
}
_DEFAULT_SEGMENTER = segment_cycles_wavelet


def resolve_segmenter(stroke_type):
    """Return the segmenter for a stroke_type. Unknown/None → the default.

    Every value `sessions.stroke_type` can hold — the four strokes, the mobile
    picker's "im" and "udk", an unrecognised string, or None — falls through to
    the default while SEGMENTER_BY_STROKE is empty.
    """
    return SEGMENTER_BY_STROKE.get(stroke_type, _DEFAULT_SEGMENTER)


# ── SWIM WINDOW BY RHYTHM (Phase 59-03) ───────────────────────────────────────
#
# ⚠ Tuned against ONE swimmer's 23 annotated sessions. Change-detector values, not
# universal constants. Measured effect vs the old detectors (median |error|):
#     ip_end  3.93 s → 2.16 s        finish  3.82 s → 1.20 s
_WINDOW_POWER_FRAC   = 0.25   # ridge amplitude vs its own 95th pct → "rhythm present"
_WINDOW_FREQ_TOL     = 0.30   # ±30% of steady-state stroke frequency counts as settled
_WINDOW_HOLD_CYCLES  = 1.0    # settled frequency must persist this many cycles
_WINDOW_GAP_S        = 1.0    # bridge rhythm dropouts shorter than this
# Plausibility floor. A window spanning fewer than this many cycles at its OWN detected
# stroke frequency is not a swim, and the detector is disbelieved (returns None → the
# caller keeps the old motion-based boundaries). Measured on 36 freestyle/backstroke
# sessions: `duration x f_ref < 4` flags 13/13 of the windows that collapse to ≤3 cycles,
# at the cost of also disbelieving 7/23 sound ones. That asymmetry is deliberate — a
# false positive costs only the IMPROVEMENT on that session (it reverts to today's
# behavior), while a false negative ships an implausibly narrow window and a
# wrong-in-a-new-way stroke rate.
_WINDOW_MIN_CYCLES   = 4.0
# Plausible-stroke frequency floor (Phase 65-02). A steady f_ref BELOW this is not a stroke rate —
# it is the CWT ridge railed to its low-frequency floor (grid low end 1/_PERIOD_MAX_S = 0.25 Hz)
# because _track_ridge's low-band bias tipped a weak stroke fundamental down. Measured 2026-08-17
# on 12 sessions + "indigo ray": the rail sits ~0.33 Hz; the lowest LEGITIMATE fired f_ref is
# 0.72 Hz, so 0.45 separates them with wide margin. Only free/back/fly rail this way; breaststroke's
# slow legitimate rhythm can sit near the floor, so it is exempt from the guard (see detect_swim_window).
_WINDOW_FMIN_HZ      = 0.45


def _longest_active_run(mask, fs, min_gap_s=_WINDOW_GAP_S):
    """Longest contiguous True run, after bridging gaps shorter than min_gap_s.

    Bridging is load-bearing: one slow stroke or a breath dips the ridge amplitude
    below threshold mid-swim, and without it the window would truncate at that dip.
    """
    if not mask.any():
        return None
    m = mask.copy()
    gap = max(1, int(min_gap_s * fs))
    idx = np.flatnonzero(m)
    for a, b in zip(idx[:-1], idx[1:]):
        if 1 < b - a <= gap:
            m[a:b] = True
    idx    = np.flatnonzero(m)
    splits = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[splits + 1]]
    ends   = np.r_[idx[splits], idx[-1]]
    best   = int(np.argmax(ends - starts))
    return int(starts[best]), int(ends[best]) + 1


def _window_from_ridge(fs, ridge_freq, ridge_power):
    """The amplitude-run → steady f_ref → plausibility-gate → frequency-settle body of
    detect_swim_window, factored out (Phase 65-02) so it can run on either the production
    (biased) ridge or a de-biased one.

    Returns (window, f_ref):
      * window = (ip_end, swim_end) or None — exactly what detect_swim_window used to
        return inline, in the same branch order;
      * f_ref  = the steady stroke frequency it measured, or np.nan when it could not.
        The caller reads f_ref to tell a low-RAILED ridge (a small positive f_ref, even
        when the plausibility gate then returns window=None) from a genuine no-window.

    ⚠ BYTE-IDENTICAL to the old inline body on the production ridge. Do not "improve"
    it here — TestCycleRegularityGate and the segmenter fixture do not exercise it, but
    the whole point of the 65-02 seam is that the biased path is unchanged.
    """
    amp = np.sqrt(np.maximum(ridge_power, 0.0))
    ref = float(np.percentile(amp, 95))
    if ref < 1e-9:
        return None, float("nan")
    run = _longest_active_run(amp > _WINDOW_POWER_FRAC * ref, fs)
    if run is None:
        return None, float("nan")
    i0, i1 = run

    back = ridge_freq[i0 + int(0.4 * (i1 - i0)):i1]
    if back.size < 3:
        return (i0, i1), float("nan")
    f_ref = float(np.median(back))
    if not np.isfinite(f_ref) or f_ref <= 0:
        return (i0, i1), float("nan")

    # Plausibility: does this window even span a swim's worth of cycles at its own
    # detected frequency? On roughly a third of real sessions the amplitude run latches
    # onto the DIVE transient instead of the swim — it starts at t=0 and ends early —
    # and the result is an implausibly narrow window. Disbelieve those outright rather
    # than emit a confident wrong answer. (f_ref is still returned so the caller can see
    # a low RAIL even here.)
    if ((i1 - i0) / fs) * f_ref < _WINDOW_MIN_CYCLES:
        return None, f_ref

    near = np.abs(ridge_freq - f_ref) <= _WINDOW_FREQ_TOL * f_ref
    hold = max(1, int(_WINDOW_HOLD_CYCLES / f_ref * fs))
    held = 0
    for i in range(i0, i1):
        held = held + 1 if near[i] else 0
        if held >= hold:
            return (int(i - hold + 1), i1), f_ref
    return (i0, i1), f_ref


def detect_swim_window(t, vel, stroke_type=None):
    """Start and end of CYCLIC STROKING → (ip_end, swim_end), or None.

    Phase 59-03. Replaces two detectors that were asking the wrong question:
    `detect_phases` asked "where does MOTION start and stop" and
    `detect_initial_phase` asked "where is the first deep TROUGH". The coach marks
    where STROKING starts and stops, which is neither.

    Both old rules were measured wrong, and both hypotheses for WHY were refuted:
      * finish is not a threshold problem — mean |vel| in the over-run region is
        0.403 m/s, EIGHT times _BASELINE_THRESH. The swimmer really is still moving
        after the touch. It is fast but APERIODIC, so rhythm separates it and
        amplitude cannot.
      * ip_end is not a trough-selection problem — in 12 of 23 sessions the first
        qualifying trough was already the nearest one to the human mark and was still
        0.6–6.1 s early. Underwater dolphin kicking IS rhythmic, just at roughly
        twice the stroke frequency, so amplitude accepts it and only FREQUENCY
        rejects it.

    Hence: ridge amplitude finds the active region; the frequency SETTLING inside it
    finds where stroking actually begins. Steady-state stroke frequency is taken from
    the back 60% of the active region, which is past any breakout by construction.

    Phase 65-02 — the low-rail guard. On some free/back/fly sessions ("indigo ray") the
    production ridge rails to the CWT low-frequency floor: _track_ridge's low-band bias
    tips a weak stroke fundamental down, so f_ref reads ~0.33 Hz (a real fly rate is
    ~0.8–1.2 Hz), the settle test finds "settled" from the very first sample, and ip_end
    collapses onto b_end — the dive + underwater kicks then segment as cycles. When f_ref
    rails below _WINDOW_FMIN_HZ we recompute the ridge with the low-band bias REMOVED and
    take the window from that instead. Breaststroke is exempt: its slow legitimate rhythm
    can sit near the floor, and its segmentation is validated and must stay byte-identical
    (phase D2). If the de-biased ridge does not recover a plausible f_ref, the biased
    result stands — never worse than before, and never the trough fallback (which was
    16.6 s on indigo ray).

    Returns full-trace indices, swim_end exclusive. None when the trace is too short
    or flat to carry a ridge — the caller keeps its existing fallbacks.
    """
    fs = _compute_fs(t)
    ridge_freq, ridge_power = _cwt_ridge(vel, fs)
    if ridge_freq is None:
        return None

    window, f_ref = _window_from_ridge(fs, ridge_freq, ridge_power)

    # De-bias guard: ONLY a low RAILED f_ref triggers the recompute, so any session whose
    # ridge already tracks a plausible stroke rate returns `window` unchanged — byte-identical
    # to pre-65-02. Breaststroke never enters the branch.
    if (stroke_type != "breaststroke"
            and np.isfinite(f_ref) and 0.0 < f_ref < _WINDOW_FMIN_HZ):
        rf0, rp0 = _cwt_ridge(vel, fs, low_band_bias=0.0)
        if rf0 is not None:
            window0, f_ref0 = _window_from_ridge(fs, rf0, rp0)
            if np.isfinite(f_ref0) and f_ref0 >= _WINDOW_FMIN_HZ:
                return window0

    return window


def detect_initial_phase(t, vel, baseline_end_idx):
    """
    Identify dive surge and underwater pulldown before cyclic breaststroke begins.

    Looks for the first deep velocity trough after baseline_end — that trough
    marks the end of the initial phase.  Prominent peaks before that trough
    are classified as dive surge (first peak) and pulldown (last peak).

    Returns dict:
        initial_phase_end_idx  – index where cyclic stroke segmentation starts
        dive_detected          – True if a dive surge peak was found
        dive_duration_s        – time from baseline_end to dive peak, or None
        pulldown_detected      – True if an underwater pulldown peak was found
        pulldown_peak_vel_ms   – velocity at pulldown peak, or None
        pulldown_duration_s    – time from pulldown peak to initial_phase_end, or None
    """
    _default = {
        "initial_phase_end_idx": baseline_end_idx,
        "dive_detected":         False,
        "dive_duration_s":       None,
        "pulldown_detected":     False,
        "pulldown_peak_vel_ms":  None,
        "pulldown_duration_s":   None,
    }
    try:
        fs = _compute_fs(t)
        search_samples = min(len(vel) - baseline_end_idx, int(15 * fs))
        if search_samples < 5:
            return _default

        vel_search = vel[baseline_end_idx : baseline_end_idx + search_samples]
        v95 = float(np.percentile(np.abs(vel_search), 95))
        if v95 < 0.01:
            return _default

        # First deep trough = end of initial phase
        min_dist = max(1, int(0.5 * fs))
        troughs, _ = find_peaks(-vel_search, height=-0.20 * v95, distance=min_dist)
        if len(troughs) == 0:
            return _default

        ip_end_off = int(troughs[0])
        ip_end_idx = baseline_end_idx + ip_end_off

        # Prominent peaks in the initial window
        win = vel[baseline_end_idx:ip_end_idx]
        if len(win) < 2:
            return {**_default, "initial_phase_end_idx": ip_end_idx}

        peaks, _ = find_peaks(win, prominence=0.15 * v95)
        out = {**_default, "initial_phase_end_idx": ip_end_idx}

        if len(peaks) == 0:
            pass  # no detectable peaks in initial window
        elif len(peaks) == 1:
            pk_off = int(peaks[0])
            out["pulldown_detected"]    = True
            out["pulldown_peak_vel_ms"] = float(win[pk_off])
            out["pulldown_duration_s"]  = float(t[ip_end_idx] - t[baseline_end_idx + pk_off])
        else:
            # First peak = dive surge, last peak = pulldown
            dive_off = int(peaks[0])
            pull_off = int(peaks[-1])
            out["dive_detected"]        = True
            out["dive_duration_s"]      = float(t[baseline_end_idx + dive_off] - t[baseline_end_idx])
            out["pulldown_detected"]    = True
            out["pulldown_peak_vel_ms"] = float(win[pull_off])
            out["pulldown_duration_s"]  = float(t[ip_end_idx] - t[baseline_end_idx + pull_off])

        return out

    except Exception:
        return _default


# ── DIVE START (Phase 79) ─────────────────────────────────────────────────────
#
# `dive_start_s` opens the race-Start phase. It USED to key on baseline_end — the first
# point the rolling mean of |vel| holds above a low floor for 0.5 s, i.e. motion onset.
# That fires early: at the start the swimmer jumps off the block and sinks, tugging the
# tether line below true dive speed, and the low floor trips on that artifact.
#
# The coach's rule (2026-08-20, refined 2026-08-21): the launch is the first surge that
# clears a real speed X — the jump-and-sink tug never reaches it, a dive/push-off does.
# Anchor the marker at the FOOT of that surge (the local minimum immediately left of the
# first upward crossing of X), not its crest: that low point is the true launch start,
# after the block artifact. Fall back to baseline_end when nothing crosses X (e.g. a weak
# wall push-off) — never worse than the old rule. X swept in tools/score_dive_start.py.
_DIVE_CROSS_MS = 2.0        # X: the launch surge must clear this speed (m/s). Tunable — swept.
_DIVE_FOOT_PROM_FRAC = 0.15 # foot-trough min prominence as a fraction of X (0.3 m/s at X=2).
                            # A shallow ripple on the surge's noisy rising edge is a local min
                            # too; without this it would be taken as the foot instead of the
                            # real valley below it. Scaled to X (not v95) so the cutoff is
                            # stable — independent of the post-touch tail that drags v95 down.


def detect_dive_start(t, vel, threshold=_DIVE_CROSS_MS, prom_frac=_DIVE_FOOT_PROM_FRAC):
    """Foot of the first launch surge that clears `threshold` m/s — the race Start.

    Returns a FULL-TRACE index: the last PROMINENT local minimum left of the first upward
    crossing of `threshold` (the low foot of the launch surge, AFTER the jump-and-sink
    block artifact). The trough must be at least `prom_frac * threshold` deep, so a shallow
    ripple on the surge's rising edge is skipped in favour of the true valley below it.
    Returns None when no sample reaches `threshold`, or when no prominent trough precedes
    the crossing — the caller then falls back to baseline_end. Pure; never raises.

    ⚠ NaN-safe like detect_underwater_start: reached from POST /recompute over a STORED
    velocity_profile that can carry magnet-dropout nulls. Uses finite-aware comparisons
    and does NOT route through _window_v95 (which returns NaN on a single null).
    """
    try:
        v = np.asarray(vel, dtype=float)
        if v.size < 3:
            return None

        # First upward crossing of X: the earliest finite sample at or above threshold.
        # The tug never reaches X, so the first crossing is the real dive/push-off surge.
        above = np.isfinite(v) & (v >= float(threshold))
        crossings = np.flatnonzero(above)
        if crossings.size == 0:
            return None
        c = int(crossings[0])
        head = v[:c]
        if head.size < 3:
            return None

        # The surge foot: the LAST *prominent* local minimum left of the crossing (the real
        # valley nearest c). find_peaks(-head) with a prominence floor rejects rising-edge
        # ripples; the last survivor is the foot. None when none is prominent enough (or the
        # rise into the crossing is monotonic) → caller falls back to baseline_end.
        troughs, _ = find_peaks(-head, prominence=prom_frac * float(threshold))
        if troughs.size == 0:
            return None
        return int(troughs[-1])

    except Exception:
        return None


# ── UNDERWATER START (Phase 75-02) ────────────────────────────────────────────
#
# The coach's own rule, verbatim: "for every session i've seen, the underwater phase
# begins at the first big velocity dip."  Physically that dip is where the free glide
# ENDS and propulsion resumes — the start / push-off drives velocity to the race peak,
# the swimmer then coasts in streamline while velocity decays, and dolphin kicking (or
# the breaststroke pulldown) begins at the bottom of that decay.
#
# Measured 2026-08-19 against the 38 hand-marked `underwater_start_s` annotations:
#     prom frac   0.25    0.30    0.35    0.40    0.50    0.60
#     mean |err|  0.43s   0.24s   0.18s   0.13s   0.24s   0.74s
#     within .5s  29/38   33/38   35/38   35/38   33/38   24/38
# 0.40 is the minimum of a broad, flat 0.30–0.40 plateau — not a knife-edge fit — and it
# is uniform across strokes (freestyle 0.15 s, butterfly 0.10 s, breaststroke 0.03 s).
# The rule it replaces (`baseline_end_s + dive_duration_s`, i.e. the first prominent PEAK
# — the top of the dive) scored 1.23 s on only 10 of those 38 and is null on 84 of 108
# live sessions, because detect_initial_phase needs TWO peaks to set dive_detected.
#
# ⚠ Caveat to carry forward: those marks were placed by a coach looking at the velocity
# trace, so the rule may partly describe how the mark is clicked rather than independent
# physiology. It is nonetheless the annotation contract's own definition of the boundary,
# which makes it the right target for an auto seed.
_UW_SURGE_WINDOW_S  = 4.0   # the start surge peaks within this long of first motion
_UW_START_PROM_FRAC = 0.40  # dip prominence, as a fraction of v95 — see table above


def detect_underwater_start(t, vel, baseline_end_idx):
    """First prominent velocity dip after the start surge — where kicking begins.

    Returns a FULL-TRACE index, or None when the trace carries no qualifying dip (same
    refuse-to-answer convention as detect_swim_window). Pure; never raises.

    ⚠ Uses np.nanpercentile / np.nanargmax rather than the module's _window_v95 helper,
    which calls np.percentile and therefore returns NaN if a single sample is NaN. This
    detector is also reached from the API's recompute path, whose input is a STORED
    velocity_profile that can contain nulls. Do not "consolidate" it onto _window_v95.
    """
    try:
        fs = _compute_fs(t)
        start = max(0, int(baseline_end_idx))
        seg = vel[start:]
        if len(seg) < int(fs):          # under one second of signal — no answer
            return None

        v95 = float(np.nanpercentile(np.abs(seg), 95))
        if not np.isfinite(v95) or v95 <= 0:
            return None

        # The start surge: the fastest the swimmer goes in the first few seconds.
        lim = int(_UW_SURGE_WINDOW_S * fs)
        head = seg[:lim] if len(seg) > lim else seg
        if not np.any(np.isfinite(head)):
            return None
        pk = int(np.nanargmax(head))

        tail = seg[pk:]
        if len(tail) < 3:
            return None

        troughs, _ = find_peaks(-tail, prominence=_UW_START_PROM_FRAC * v95)
        if len(troughs) == 0:
            return None

        return start + pk + int(troughs[0])

    except Exception:
        return None


_UW_KICK_PROM_FRAC = 0.15   # min downkick-peak prominence, as a fraction of the window v95
_UW_KICK_MAX_HZ    = 4.0    # kick-rate ceiling → min peak spacing = fs / this (reject ripples)


def detect_underwater_kicks(t, vel, uw_start_idx, uw_end_idx):
    """Propulsive dolphin-downkick peaks inside the underwater window [uw_start, uw_end).

    Each downkick is one axial velocity surge, so the kicks are the prominent peaks of the
    window slice. Returns a FULL-TRACE int array of peak indices — possibly EMPTY when the
    window carries no clear surge (a glide-only underwater) — or None when the window is
    itself degenerate (empty, reversed, or no finite signal). Pure; never raises.

    ⚠ Reached from POST /recompute over a STORED velocity_profile that can carry magnet-
    dropout nulls (→ NaN). Unlike detect_underwater_start (which hunts a single early trough
    and tolerates sparse NaN by luck), a prominence-based MULTI-peak search scans widely for
    each peak's base, so one interior NaN would poison every kick's prominence. Interior
    dropouts are therefore linearly filled first — peaks are about oscillation shape, not
    exact values, so the fill is safe.
    """
    try:
        i0 = max(0, int(uw_start_idx))
        i1 = min(len(vel), int(uw_end_idx))
        seg = np.asarray(vel[i0:i1], dtype=float)
        good = np.isfinite(seg)
        if len(seg) < 3 or not np.any(good):
            return None
        if not np.all(good):
            idx = np.arange(len(seg))
            seg = np.interp(idx, idx[good], seg[good])

        v95 = float(np.percentile(np.abs(seg), 95))
        if not np.isfinite(v95) or v95 <= 0:
            return None

        fs = _compute_fs(t)
        min_dist = max(1, int(round(fs / _UW_KICK_MAX_HZ)))

        peaks, _ = find_peaks(seg, prominence=_UW_KICK_PROM_FRAC * v95, distance=min_dist)
        return i0 + np.asarray(peaks, dtype=int)

    except Exception:
        return None


# ── BREAKOUT BY KICK-BAND DISAPPEARANCE (Phase 76) ────────────────────────────
#
# The Underwater→Swim breakout for the flutter strokes (freestyle, backstroke). Six
# prior levers failed to place it — amplitude, mean-vel step, accel surge, 2x harmonic,
# rhythm step-down, first-deep-trough (65-01 / 75-02). The signal that works: dolphin
# kicking is cyclic, so a KICK BAND (~1.8-3.2 Hz) carries sustained power through the
# whole underwater phase and then goes quiet when arm stroking takes over. That band
# sits ABOVE production's 0.25-2.0 Hz ridge window, which is exactly why every ridge
# detector was structurally blind to it.
#
# ⚠ FREE/BACK ONLY — the caller (compute_session_metrics) enforces it. Butterfly RETAINS
# the band on the surface: its stroke IS two dolphin kicks per arm cycle (~2 Hz), so the
# band never disappears and this rule scores WORSE than the incumbent there — measured,
# not assumed (tools/breakout_band_probe.py: butterfly median |err| 4.46 s vs a 2.43 s
# incumbent, Pk_uw/sf ≈ 1). It must never be called for butterfly or breaststroke.
#
# ⚠ Constants are physically motivated (dolphin-kick rate), NOT fit to the corpus (D3).
_KICK_BAND_HZ    = (1.8, 3.2)   # dolphin-kick band — ABOVE the 0.25-2.0 Hz stroke ridge
_KICK_SCALO_HZ   = (0.5, 5.0)   # wider scalogram so the kick band is actually visible
_KICK_SCALO_N    = 96           # geometric scales spanning _KICK_SCALO_HZ
_KICK_SMOOTH_S   = 0.4          # rolling-mean smoothing of the band-power trace (s)
_KICK_DROP_FRAC  = 0.35         # band is "quiet" below this × the active-run 95th-pct power
_KICK_HOLD_S     = 0.6          # quiet must persist this long to count as the breakout
_KICK_MIN_RUN_S  = 0.5          # a sustained kick run shorter than this → refuse (D2).
                                # 1.0 originally; corrected 2026-08-20, when the probe was first
                                # pointed at the SHIPPED detector (76-01 Task 3) and showed the
                                # gate vetoing 4 of 16 freestyle sessions this detector had
                                # already placed to within 0.5 s — short but real underwaters.
                                # Those 4 fell back to the incumbent (+1.85 to +3.25 s) and pulled
                                # median |err| to 0.81 s, outside 76-01 AC-2. Measured plateau:
                                # 0.0-0.6 all give 0.42 s, so 0.5 is mid-plateau rather than a
                                # knife-edge fit, and still keeps a real floor. _breakout_leaves_swim
                                # below now covers the late-wrong-answer case this half-proxied.


def _kick_band_power(vel, fs):
    """Smoothed mean |CWT|² in _KICK_BAND_HZ at each sample, or None if unreadable.

    A DEDICATED wider CWT (_KICK_SCALO_HZ), NOT _cwt_ridge — the production ridge's
    0.25-2.0 Hz grid cannot see the kick band, which is the whole point. Same wavelet and
    detrend as production; np.nan_to_num because stored velocity_profiles carry nulls.
    """
    active = _detrend_for_cwt(np.nan_to_num(np.asarray(vel, dtype=float)), fs)
    if not np.any(np.isfinite(active)) or float(np.max(np.abs(active))) < 1e-9:
        return None
    dt = 1.0 / fs
    target = np.geomspace(_KICK_SCALO_HZ[0], _KICK_SCALO_HZ[1], _KICK_SCALO_N)
    scales = pywt.central_frequency(_WAVELET) / (target * dt)
    coeffs, freqs = pywt.cwt(active, scales, _WAVELET, sampling_period=dt)
    power = np.abs(coeffs) ** 2
    sel = (freqs >= _KICK_BAND_HZ[0]) & (freqs <= _KICK_BAND_HZ[1])
    if not sel.any():
        return None
    p = power[sel].mean(axis=0)
    w = max(1, int(_KICK_SMOOTH_S * fs))
    return np.convolve(p, np.ones(w) / w, mode="same")


def detect_breakout_kickband(t, vel, uw_start_idx, swim_end_idx=None):
    """Underwater→Swim breakout via kick-band disappearance (free/back).

    Returns the full-trace index where the sustained ~2 Hz dolphin-kick band goes quiet,
    or None when the band carries no trustworthy answer — the refuse-to-answer convention
    (see detect_swim_window). Refuses when:
      * uw_start is degenerate or the signal is too short/flat to carry a scalogram;
      * no kick-band run is active after uw_start;
      * the active kick run before the drop is shorter than _KICK_MIN_RUN_S (weak/short
        underwater — the swimmer barely kicked);
      * the band never cleanly goes quiet INSIDE the swim window. This last one is the
        "kept dolphin-kicking past the breakout" / weak-contrast session (Pk_uw/sf ≈ 1):
        the only quiet is the dead tail after swim_end, so bounding the search to
        swim_end turns those +4 s confident misses into a refusal → the caller keeps the
        incumbent boundary. Measured to matter on ~4 of 16 annotated freestyle sessions.

    Pure; never raises. FREE/BACK only — do not call for butterfly/breaststroke (the band
    does not disappear on the surface for undulatory strokes).
    """
    try:
        fs = _compute_fs(t)
        n  = len(vel)
        s  = max(0, int(uw_start_idx))
        end = min(int(swim_end_idx), n) if swim_end_idx is not None else n
        if s >= end - 1 or (end - s) < int(2 * fs):
            return None

        pk = _kick_band_power(vel, fs)
        if pk is None:
            return None

        ref = float(np.percentile(pk[s:end], 95))
        if not np.isfinite(ref) or ref < 1e-12:
            return None

        active = pk > _KICK_DROP_FRAC * ref
        rel = np.flatnonzero(active[s:end])
        if rel.size == 0:
            return None
        kick_start = s + int(rel[0])

        hold    = max(1, int(_KICK_HOLD_S * fs))
        min_run = int(_KICK_MIN_RUN_S * fs)
        run_below = 0
        for i in range(kick_start, end):
            if not active[i]:
                run_below += 1
                if run_below >= hold:
                    bk = i - hold + 1            # where the band first went quiet
                    if (bk - kick_start) < min_run:
                        return None              # kick run too short to trust the drop
                    return min(max(bk, s + 1), end - 1)
            else:
                run_below = 0
        return None                              # never went quiet in-window → refuse

    except Exception:
        return None


# ── collapse guard, shared by every breakout detector (Phase 76 fix, 2026-08-20) ───
_BREAKOUT_MIN_SWIM_CYCLES = 2.0   # a breakout override must leave at least this many
                                  # stroke cycles of swim behind it, or it is disbelieved


def _breakout_leaves_swim(t, vel, breakout_idx, swim_end_idx):
    """True when the swim a breakout override would leave behind still looks like swimming.

    The detect_breakout_* functions answer a LOCAL question — "did the kick band go quiet",
    "did the arm cycle turn on" — and none of them can see what its answer does to the swim
    it leaves behind. When one is wrong late, `ip_end` lands near `swim_end`, the segmenter
    gets a couple of seconds to work with, and the session ships `stroke_count = 0`: a
    confidently EMPTY answer, which is the one outcome the refuse-to-answer convention
    exists to prevent. Measured on the committed processed/breaststroke_sample.csv fixture
    driven as freestyle: ip_end 15.95 s → 25.54 s, stroke_count 11 → 0.

    So this is the plausibility gate _window_from_ridge already applies to the swim window
    (_WINDOW_MIN_CYCLES = 4.0), applied to the window an override would LEAVE: does
    [breakout_idx, swim_end_idx) span at least _BREAKOUT_MIN_SWIM_CYCLES at the rhythm the
    ridge actually tracks there? Measured on the 23 annotated free/back/fly DB sessions —
    every real freestyle detection leaves >= 2.45 cycles, while collapsed windows leave
    0.47-1.72, so the floor sits in a real gap and is not fitted to the fixture.

    The asymmetry matches _WINDOW_MIN_CYCLES and 76-D2: refusing costs only the breakout
    improvement on that session (the caller keeps its incumbent boundary), while accepting
    a collapse ships an empty session. Returns True when no frequency can be measured —
    there is then nothing to disbelieve WITH, and the detector's own gates still apply.

    Pure; never raises.
    """
    try:
        fs = _compute_fs(t)
        span_s = (int(swim_end_idx) - int(breakout_idx)) / fs
        if span_s <= 0:
            return False
        ridge_freq, _ridge_power = _cwt_ridge(vel, fs)
        if ridge_freq is None:
            return True
        seg = ridge_freq[int(breakout_idx):int(swim_end_idx)]
        if seg.size == 0:
            return True
        f_local = float(np.median(seg))
        if not np.isfinite(f_local) or f_local <= 0:
            return True
        return (span_s * f_local) >= _BREAKOUT_MIN_SWIM_CYCLES
    except Exception:
        return True


# ── BREAKOUT BY ARM-CYCLE APPEARANCE (Phase 77) ───────────────────────────────
#
# The Underwater→Swim breakout for BUTTERFLY. The Phase-76 detector above cannot be
# reused here and measured WORSE than the incumbent on fly (4.46 s vs 2.43 s) for a
# physical reason: butterfly is a dolphin kick with arms bolted on. Its SURFACE stroke
# IS two dolphin kicks per arm cycle, in the same ~2 Hz band, so the kick band never
# switches off (Pk_uw/sf ≈ 1) and there is no disappearance to detect.
#
# Fly is an APPEARANCE problem instead. Measured on the 16 annotated fly sessions, the
# breakout is a spectral REORGANIZATION — the single underwater ~1.2 Hz kick line SPLITS
# into an arm cycle plus two kick beats. The per-frequency P_surface/P_uw fingerprint
# (the ratio cancels the CWT 1/f bias; freestyle is the positive control, its kick bands
# drop 0.19-0.29x):
#
#     0.8-1.1 Hz  arm cycle             1.81x (14/16)   APPEARS
#     1.1-1.5 Hz  uw kick fundamental   0.52x ( 5/16)   DROPS
#     1.5-2.0 Hz  2-beat harmonic       2.04x (15/16)   APPEARS
#
# So the feature is the RATIO arm ÷ fundamental, which encodes the appearance AND the
# disappearance in one scale-invariant number, and the detector is a rise-AFTER-sustained-
# low (requiring the low run first is what skips the push-off transient). Scored against
# the coach's stroke_start_s marks: median |err| 2.67 s (incumbent) → 0.35 s, 12/15 ≤ 1 s.
#
# ⚠ Raw arm-band appearance alone was REJECTED — only 1.45x uw→sf, far weaker than the
# ratio. ⚠ No learned model (D2): 16 sessions from ONE swimmer is where 59-05's no-overfit
# rule bites hardest, and one physical ratio already wins.
#
# ⚠ BUTTERFLY ONLY — the caller (compute_session_metrics) enforces it. Free/back stay on
# detect_breakout_kickband; breaststroke has a pulldown, not a kick train, and is untouched.
_FLY_ARM_HZ     = (0.8, 1.1)    # arm-cycle band — APPEARS at breakout
_FLY_FUND_HZ    = (1.1, 1.5)    # uw dolphin-kick fundamental — DROPS at breakout
_FLY_SCALO_HZ   = (0.5, 5.0)    # wider CWT so both bands are visible; the same grid the
                                # 0.35 s measurement was made on (breakout_band_probe.py)
_FLY_SCALO_N    = _KICK_SCALO_N  # geometric scales spanning _FLY_SCALO_HZ
_FLY_SMOOTH_S   = 0.4           # rolling-mean smoothing of the ratio trace (s)
_FLY_LOW_FRAC   = 0.5           # ratio is "underwater-low" below this × its 20-80 pct range
_FLY_RISE_FRAC  = 0.5           # ratio is "surface-high" above this × its 20-80 pct range
_FLY_MIN_LOW_S  = 0.8           # sustained low required BEFORE a rise counts (skips push-off)
_FLY_HOLD_S     = 0.5           # the rise must persist this long to count as the breakout
_FLY_MIN_CONTRAST = 1.5         # the 80th pct of the ratio must be at least this x its 20th,
                                # or there was no reorganization to detect -> refuse (D4).
                                # ⚠ NOT decoration, and ⚠ NOT free. The low/rise thresholds
                                # are taken from the ratio's OWN 20-80 range, so without this
                                # a threshold always sits inside the observed spread and a
                                # merely RIPPLING ratio eventually supplies a low run and a
                                # "rise" — the detector could then never refuse for lack of
                                # signal, only for running out of window.
                                # Measured on the 16 annotated fly sessions (the contrast
                                # sweep tools/breakout_band_probe.py prints). Refusals fall
                                # back to the incumbent, so
                                # over-refusing costs accuracy directly:
                                #     floor   1.0    1.5    2.0    2.5    3.0    4.0
                                #     median  0.38   0.38   0.63   0.63   0.80   2.04
                                #     <=1.0s  12/16  12/16  10/16  10/16   9/16   4/16
                                #     refused  1      1      4      5      6     12
                                # 1.0-1.5 is a flat plateau; 1.5 is its top, keeping a real
                                # floor without paying anything. Anything >= 2.0 starts
                                # converting good detections into incumbent fallbacks.
                                # ⚠ On a SYNTHETIC stationary tone the contrast lands at
                                # 1.35-1.49, i.e. just under this floor — see the test class
                                # for why those cases are asserted with the floor raised
                                # rather than on that margin.


# Per-session band refinement (D5). UNSUPERVISED — it reads the session's own underwater
# spectrum, never the ground-truth marks, so it does not violate the no-overfit rule. It is
# hardening with a fixed-band fallback, not rescue: the fixed bands already survive a 4×4
# band-edge jitter grid (every cell beats the incumbent). Default set by MEASUREMENT — see
# the refine-bands row in tools/breakout_band_probe.py.
_FLY_REFINE_BANDS = False       # ⚠ MEASURED AND REJECTED, not merely left off. On the 16
                                # annotated fly sessions: fixed bands 0.38 s median |err|
                                # (1 refusal) vs per-session f0 2.33 s (7 refusals). The
                                # peak-pick keys on whatever dominates the first seconds
                                # after uw_start, which on a short or weak underwater is
                                # already the arm cycle — so it derives its "fundamental"
                                # from the very thing it is supposed to measure against.
                                # Kept (not deleted) because it is the swimmer-invariant
                                # idea and one corpus of ONE swimmer cannot refute it;
                                # flip it only against a multi-swimmer corpus.
_FLY_F0_WINDOW_S  = 3.0         # length of the post-uw_start span the f0 peak-pick reads
_FLY_F0_HZ        = (1.0, 1.6)  # where a dolphin-kick fundamental can plausibly sit
_FLY_ARM_OF_F0    = 1.3         # arm cycle ≈ fundamental / this
_FLY_F0_HALF_HZ   = 0.20        # half-width of the derived fundamental band
_FLY_ARM_HALF_HZ  = 0.15        # half-width of the derived arm band


def _fly_scalogram(vel, fs):
    """(power[n_f, n_t], freqs_hz) over _FLY_SCALO_HZ, or (None, None) if unreadable.

    A DEDICATED wider CWT, NOT _cwt_ridge — the production ridge's 0.25-2.0 Hz grid clips
    the 2-beat harmonic, and its grid spacing is itself part of what the 0.35 s result was
    measured on. Same wavelet and detrend as production; np.nan_to_num because stored
    velocity_profiles carry magnet-dropout nulls.
    """
    active = _detrend_for_cwt(np.nan_to_num(np.asarray(vel, dtype=float)), fs)
    if not np.any(np.isfinite(active)) or float(np.max(np.abs(active))) < 1e-9:
        return None, None
    dt = 1.0 / fs
    target = np.geomspace(_FLY_SCALO_HZ[0], _FLY_SCALO_HZ[1], _FLY_SCALO_N)
    scales = pywt.central_frequency(_WAVELET) / (target * dt)
    coeffs, freqs = pywt.cwt(active, scales, _WAVELET, sampling_period=dt)
    return np.abs(coeffs) ** 2, freqs


def _fly_band(power, freqs, band, fs):
    """Smoothed mean power in `band` at each sample, or None when no scale lands in it."""
    sel = (freqs >= band[0]) & (freqs <= band[1])
    if not sel.any():
        return None
    p = power[sel].mean(axis=0)
    w = max(1, int(_FLY_SMOOTH_S * fs))
    return np.convolve(p, np.ones(w) / w, mode="same")


def _fly_bands(power, freqs, fs, uw_start_idx):
    """The (arm, fundamental) bands to use for this session, in Hz.

    Fixed physical bands by default. With _FLY_REFINE_BANDS, peak-pick the underwater
    window's OWN spectrum for its kick fundamental f0 and derive both bands from it, so
    the detector can follow a swimmer whose kick rate differs from this corpus's. Falls
    back to the fixed bands whenever f0 is unreadable.
    """
    if not _FLY_REFINE_BANDS:
        return _FLY_ARM_HZ, _FLY_FUND_HZ
    i0 = max(0, int(uw_start_idx))
    i1 = min(power.shape[1], i0 + int(_FLY_F0_WINDOW_S * fs))
    sel = (freqs >= _FLY_F0_HZ[0]) & (freqs <= _FLY_F0_HZ[1])
    if i1 <= i0 or not sel.any():
        return _FLY_ARM_HZ, _FLY_FUND_HZ
    col = power[sel, i0:i1].mean(axis=1)
    if not np.any(np.isfinite(col)):
        return _FLY_ARM_HZ, _FLY_FUND_HZ
    f0 = float(freqs[sel][int(np.argmax(col))])
    if not np.isfinite(f0) or f0 <= 0:
        return _FLY_ARM_HZ, _FLY_FUND_HZ
    arm_c = f0 / _FLY_ARM_OF_F0
    return ((arm_c - _FLY_ARM_HALF_HZ, arm_c + _FLY_ARM_HALF_HZ),
            (f0 - _FLY_F0_HALF_HZ, f0 + _FLY_F0_HALF_HZ))


def _fly_band_ratio(vel, fs, uw_start_idx=0):
    """Smoothed P(arm band) / P(fundamental band) at each sample, or None if unreadable.

    The fly breakout feature: it rises when the ~1 Hz arm cycle turns on underneath the
    ~2 Hz kick that keeps running. Scale-invariant, so it needs no amplitude calibration.
    """
    power, freqs = _fly_scalogram(vel, fs)
    if power is None:
        return None
    arm_hz, fund_hz = _fly_bands(power, freqs, fs, uw_start_idx)
    arm  = _fly_band(power, freqs, arm_hz, fs)
    fund = _fly_band(power, freqs, fund_hz, fs)
    if arm is None or fund is None:
        return None
    return arm / (fund + 1e-12)


def detect_breakout_fly(t, vel, uw_start_idx, swim_end_idx=None):
    """Underwater→Swim breakout via arm-cycle appearance (BUTTERFLY).

    Returns the full-trace index where the arm ÷ fundamental band-power ratio rises AFTER
    a sustained low run, or None when the ratio carries no trustworthy answer — the
    refuse-to-answer convention (see detect_swim_window). Refuses when:
      * uw_start is degenerate or the window is under two seconds;
      * the signal is too flat / all-NaN to carry a scalogram, or the ratio has no range;
      * the ratio's in-window contrast is under _FLY_MIN_CONTRAST — it ripples but never
        reorganizes, so a rise found in it would be noise dressed as a breakout;
      * no sustained low run exists after uw_start — without the settled underwater kick
        region there is nothing for a rise to be measured against, and the push-off
        transient would trigger instead;
      * the ratio never cleanly steps up INSIDE the swim window. This is the short-
        underwater class: the arm structure only becomes unambiguous past swim_end, so
        bounding the search there turns those +2 to +4 s confident misses into refusals
        and the caller keeps the incumbent boundary. Same bound detect_breakout_kickband
        applies, for the same reason.

    Pure; never raises. BUTTERFLY only — do not call for free/back (their surface kick
    band disappears, which is detect_breakout_kickband's signal) or breaststroke.
    """
    try:
        fs = _compute_fs(t)
        n  = len(vel)
        s  = max(0, int(uw_start_idx))
        end = min(int(swim_end_idx), n) if swim_end_idx is not None else n
        if s >= end - 1 or (end - s) < int(2 * fs):
            return None

        ratio = _fly_band_ratio(vel, fs, s)
        if ratio is None:
            return None

        seg = ratio[s:end]
        seg = seg[np.isfinite(seg)]
        if seg.size < int(2 * fs):
            return None

        lo, hi = np.percentile(seg, 20), np.percentile(seg, 80)
        if not np.isfinite(lo) or not np.isfinite(hi) or (hi - lo) < 1e-9:
            return None
        if lo <= 0 or (hi / lo) < _FLY_MIN_CONTRAST:
            return None                      # no reorganization in-window -> refuse
        low_thr  = lo + _FLY_LOW_FRAC * (hi - lo)
        rise_thr = lo + _FLY_RISE_FRAC * (hi - lo)

        min_low = max(1, int(_FLY_MIN_LOW_S * fs))
        hold    = max(1, int(_FLY_HOLD_S * fs))
        low_run, established, rise_run = 0, False, 0
        for i in range(s, end):
            v = ratio[i]
            if not np.isfinite(v):
                continue
            if not established:
                # the underwater phase: the fundamental dominates, so the ratio sits low
                if v <= low_thr:
                    low_run += 1
                    if low_run >= min_low:
                        established = True
                else:
                    low_run = 0
                continue
            if v >= rise_thr:
                rise_run += 1
                if rise_run >= hold:
                    bk = i - hold + 1        # where the arm cycle first turned on
                    return min(max(bk, s + 1), end - 1)
            else:
                rise_run = 0
        return None                          # never rose in-window → refuse

    except Exception:
        return None


def time_to_distance(t, dist, target_m, baseline_end_idx, head_waist_m=0.0):
    """
    Elapsed time from baseline_end until the swimmer's head reaches target_m.

    The wheel measures waist position.  Head is head_waist_m ahead of the waist,
    so the wheel reads (target_m - head_waist_m) when the head crosses target_m.

    Returns float seconds, or None if target is unreachable.
    """
    waist_target = target_m - head_waist_m
    if waist_target <= 0:
        return None

    dist_from_start = dist[baseline_end_idx:] - dist[baseline_end_idx]
    if len(dist_from_start) == 0 or dist_from_start[-1] < waist_target:
        return None

    idx = int(np.searchsorted(dist_from_start, waist_target))
    if idx >= len(dist_from_start):
        return None

    return float(t[baseline_end_idx + idx] - t[baseline_end_idx])


def extract_cycle_peaks(vel, cycles):
    """
    For each trough-bounded segment, classify peaks as arm-pull and kick.

    Arm-pull = highest-amplitude prominent peak in the cycle.  This is more
    robust than "first chronological" because filter-ringing bumps at the
    trough boundary are always low-amplitude (~0.3–0.5 m/s) while the real
    arm-pull is the dominant velocity event in the cycle (~1–2+ m/s).

    Kick = highest prominent peak that occurs after the arm-pull in time.

    Mutates each cycle dict in-place, adding:
        arm_peak_idx   – index of the pull peak
        arm_peak_vel   – velocity at pull peak (m/s)
        kick_peak_idx  – index of the kick peak, or None if not found
        kick_peak_vel  – velocity at kick peak, or None
    Also updates peak_idx to match arm_peak_idx.
    Returns the same list for convenience.
    """
    # v95 over the span the cycles actually cover, not the full trace (Phase 57) — a
    # post-swim dead tail would otherwise lower this and with it the peak-prominence
    # floor, which is a DETECTION threshold, not just a reported number.
    v95      = (_window_v95(vel, cycles[0]["start_idx"], cycles[-1]["end_idx"])
                if cycles else float(np.percentile(np.abs(vel), 95)))
    min_prom = _PEAK_MIN_PROM_FRAC * v95

    for cyc in cycles:
        a, b = cyc["start_idx"], cyc["end_idx"]
        seg  = vel[a:b]

        pks, _ = find_peaks(seg, prominence=min_prom)

        if len(pks) == 0:
            pull_off = int(np.argmax(seg))   # fallback: argmax
        else:
            # Highest-amplitude peak = arm-pull
            pull_off = int(pks[np.argmax(seg[pks])])

        cyc["arm_peak_idx"] = a + pull_off
        cyc["arm_peak_vel"] = float(seg[pull_off])

        # Kick: highest prominent peak after the arm-pull in time
        rest = seg[pull_off + 1:]
        if len(rest) >= 2:
            kick_pks, _ = find_peaks(rest, prominence=min_prom)
        else:
            kick_pks = []
        if len(kick_pks) > 0:
            best_kick = int(kick_pks[np.argmax(rest[kick_pks])])
            cyc["kick_peak_idx"] = a + pull_off + 1 + best_kick
            cyc["kick_peak_vel"] = float(rest[best_kick])
        else:
            cyc["kick_peak_idx"] = None
            cyc["kick_peak_vel"] = None

        cyc["peak_idx"] = cyc["arm_peak_idx"]

    return cycles


# ── METRICS ──────────────────────────────────────────────────────────────────

def compute_session_metrics(t, vel, dist, head_waist_m=0.0, manual=None, stroke_type=None):
    """
    Top-level function: run the full breaststroke analysis pipeline.

    stroke_type (optional, Phase 59-02): selects the segmenter via SEGMENTER_BY_STROKE.
        None or an unrecognised value → the default (wavelet), which is what every
        stroke resolves to while that table is empty. Ignored entirely when
        manual["cycle_bounds"] is supplied, since human boundaries bypass segmentation.

    manual (optional, Phase 47): dict of human-annotation overrides — any subset of
        baseline_end_idx  – replaces detect_phases baseline_end
        ip_end_idx        – replaces detect_initial_phase end (cyclic analysis start)
        swim_end_idx      – replaces detect_phases swim_end (exclusive slice end)
        cycle_bounds      – list of (start_idx, end_idx) FULL-TRACE index pairs;
                            bypasses the wavelet segmenter entirely
    All indices are full-trace. Omitted keys fall back to auto-detection, so the
    default (manual=None) path is identical to the pre-Phase-47 behavior.

    Returns a dict with two keys:
        'session'   – single-value session-level metrics
        'cycles'    – list of per-cycle dicts (one entry per stroke)
    """
    manual = manual or {}
    fs  = _compute_fs(t)

    # ── phase detection ────────────────────────────────────────────────────
    # baseline_end still comes from detect_phases — it marks where MOTION begins (the
    # dive), which is the right question for that boundary and feeds baseline_end_s.
    phases   = detect_phases(t, vel)
    b_end    = phases["baseline_end"]
    swim_end = phases["swim_end"]
    if manual.get("baseline_end_idx") is not None:
        b_end = min(max(int(manual["baseline_end_idx"]), 0), len(t) - 1)

    # ── swim window by RHYTHM (Phase 59-03) ────────────────────────────────
    # Supersedes the two AUTO boundaries. Measured on 23 annotated sessions: ip_end
    # median |error| 3.93 s → 2.16 s, finish 3.82 s → 1.20 s. Returns None when the
    # trace is too short or flat to carry a ridge, in which case the old values stand.
    # ⚠ A manual value always wins over this — applied below, exactly as before.
    win = detect_swim_window(t, vel, stroke_type)
    if win is not None:
        swim_end = min(max(int(win[1]), b_end + 1), len(t))
    if manual.get("swim_end_idx") is not None:
        swim_end = min(max(int(manual["swim_end_idx"]), b_end + 1), len(t))

    # ── initial phase detection (dive + pulldown) ──────────────────────────
    # ⚠ Still trough-based, deliberately: this call supplies the dive/pulldown fields
    # annotations.build_seed reads. Phase 59-03 changes which function decides the
    # WINDOW, not the whole front end. Its initial_phase_end_idx is superseded when the
    # rhythm detector runs; pulldown_duration_s remains measured to the TROUGH, so it
    # is not the interval from the pulldown peak to the new stroke start.
    # Order preserved from pre-59-03: this runs AFTER the manual baseline override.
    initial_phase = detect_initial_phase(t, vel, b_end)
    ip_end = initial_phase["initial_phase_end_idx"]
    if win is not None:
        ip_end = min(max(int(win[0]), b_end), swim_end - 1)
        initial_phase["initial_phase_end_idx"] = ip_end

    # ── breakout by kick-band disappearance (Phase 76) ─────────────────────
    # Free/back only: supersede the rhythm-settle ip_end with the true Underwater→Swim
    # breakout where the ~2 Hz dolphin-kick band goes quiet. detect_underwater_start is
    # the SAME window start resolve_boundaries uses, so the underwater-metric window and
    # the segmentation start agree by construction. Refuses (→ keeps the value above) on
    # weak/short/kept-kicking underwater, and _breakout_leaves_swim vetoes any answer
    # that would leave less than ~2 stroke cycles of swim behind it (a late wrong
    # breakout otherwise ships stroke_count = 0). Butterfly/breaststroke/None never enter the
    # branch, so their ip_end and every downstream metric stay byte-identical. Runs
    # BEFORE the manual override, so a human ip_end still wins (Phase 47 precedence).
    if stroke_type in ("freestyle", "backstroke") and swim_end > b_end:
        uw = detect_underwater_start(t, vel, b_end)
        if uw is not None:
            bk = detect_breakout_kickband(t, vel, uw, swim_end)
            if bk is not None and _breakout_leaves_swim(t, vel, bk, swim_end):
                ip_end = min(max(int(bk), b_end), swim_end - 1)
                initial_phase["initial_phase_end_idx"] = ip_end

    # ── breakout by arm-cycle APPEARANCE (Phase 77) ────────────────────────
    # Butterfly only, and a sibling of the block above rather than a widening of it: fly
    # keeps its ~2 Hz kick band on the surface (the stroke IS two dolphin kicks per arm
    # cycle), so nothing disappears and the 76 detector measured WORSE than the incumbent
    # here. What appears instead is a ~1 Hz arm cycle underneath the kick, which
    # detect_breakout_fly reads as a rise in the arm ÷ fundamental band-power ratio.
    # The two branches are mutually exclusive by stroke_type. Same collapse guard, same
    # refusal fallback, and still BEFORE the manual override so a human ip_end wins.
    if stroke_type == "butterfly" and swim_end > b_end:
        uw = detect_underwater_start(t, vel, b_end)
        if uw is not None:
            bk = detect_breakout_fly(t, vel, uw, swim_end)
            if bk is not None and _breakout_leaves_swim(t, vel, bk, swim_end):
                ip_end = min(max(int(bk), b_end), swim_end - 1)
                initial_phase["initial_phase_end_idx"] = ip_end

    if manual.get("ip_end_idx") is not None:
        ip_end = min(max(int(manual["ip_end_idx"]), b_end), swim_end - 1)

    # v95 over the SWIM WINDOW (Phase 57) — must come after b_end/swim_end are final,
    # which is why it is here and not at the top with fs. Its only consumer in this
    # function is the dead-spot threshold in the per-cycle loop below.
    v95 = _window_v95(vel, b_end, swim_end)

    # ── segmentation (from initial-phase end to swim_end) ──────────────────
    t_seg    = t[ip_end:swim_end]
    vel_seg  = vel[ip_end:swim_end]
    vel_swim = vel[b_end:swim_end]   # full window for session velocity stats

    manual_bounds = manual.get("cycle_bounds")
    if manual_bounds:
        # Human-annotated boundaries (Phase 47) — already full-trace indices, so
        # no ip_end offset. Peak = velocity argmax within the cycle (same anchor
        # role as the segmenters' peak_idx; refined by extract_cycle_peaks below).
        cycles = []
        for a, b in manual_bounds:
            a = min(max(int(a), 0), len(t) - 1)
            b = min(int(b), len(t))
            if b - a < 2:
                continue  # degenerate (<2 samples) — cannot support per-cycle metrics
            cycles.append({
                "cycle_num": len(cycles),
                "start_idx": a,
                "end_idx":   b,
                "peak_idx":  a + int(np.argmax(vel[a:b])),
            })
    else:
        # Routing is TABLE-DRIVEN as of Phase 59-02 — see SEGMENTER_BY_STROKE above.
        # That table is currently EMPTY, so every stroke still resolves to the
        # wavelet/CWT ridge exactly as Phase 16-05 shipped it, at placeholder quality
        # (see session["segmentation_reliable"] below and 16-04-SUMMARY).
        # segment_cycles_trough is still never called from here, but it is no longer
        # merely a backup: it is a scored candidate for 59-04. Phase 59-01 measured it
        # at 0.00 against ground truth, which is a MISFEED rather than a failure — it
        # keys on velocity below 0.20 x v95, and Phase 57 made the swim window
        # authoritative, removing the dead tail those deep troughs lived in.
        cycles = resolve_segmenter(stroke_type)(t_seg, vel_seg)
        if cycles is None:
            cycles = []

        # Offset indices so they map back to the full-trace arrays
        for c in cycles:
            c["start_idx"] += ip_end
            c["end_idx"]   += ip_end
            c["peak_idx"]  += ip_end

    # Phase 61-01 (D5) REMOVED the steady/ramp_up cycle split that used to live here.
    # Every cycle now counts toward every session metric, so the per-cycle charts and the
    # session summary describe the same population — the coach's report that "the numbers
    # don't reflect what's shown on the graph" was literally true of the old split.
    #
    # ⚠ THE OLD FILTER WAS MISNAMED. It gated on arm_peak < 0.50 x p75 — a velocity test,
    # not a positional one — and measurement (tools/rampup_impact.py, 2026-08-11) showed it
    # overwhelmingly marked the swimmer DECELERATING INTO THE WALL, not accelerating from
    # rest: median normalized position 0.91, 59% in the final 20% of the swim, and 0 of 13
    # affected sessions in the raw/ corpus had a leading run. Do not reintroduce it under
    # its old name expecting it to mean "ramp up".
    #
    # ⚠ CONSEQUENCE, ACCEPTED: the wall-touch cycle is now a stroke. On the 20 affected
    # sessions of 53 measured, cv_arm_peak_vel +70% and fatigue_index_pct +110%. Sessions
    # stored before this change are on the old scale — the fourth such break after Phases
    # 57, 59-03 and 59-05.

    # ── sub-peak extraction ───────────────────────────────────────────────
    extract_cycle_peaks(vel, cycles)

    # ── per-cycle derived metrics ─────────────────────────────────────────
    for cyc in cycles:
        a, b      = cyc["start_idx"], cyc["end_idx"]
        seg_t     = t[a:b]
        seg_v     = vel[a:b]
        duration  = float(t[b - 1] - t[a])

        cyc["duration_s"]     = duration
        cyc["dist_m"]         = float(dist[b - 1] - dist[a])
        cyc["impulse_m"]      = float(trapezoid(np.maximum(seg_v, 0), seg_t))
        cyc["mean_vel_ms"]    = float(np.mean(seg_v))
        cyc["trough_vel_ms"]  = float(np.min(seg_v))  # minimum velocity at recovery

        # Dead spot: |vel| < 10% of v95. v95 is session-wide but SWIM-WINDOWED since
        # Phase 57 — it was a full-trace percentile here and in swim_metrics.ipynb.
        dead_mask = np.abs(seg_v) < _DEAD_SPOT_THRESH * v95
        cyc["dead_spot_s"]    = float(dead_mask.sum() / fs)

        # Coast fraction: fraction of cycle below 50% of this cycle's arm-pull vel
        coast_thresh = _COAST_FRAC_THRESH * cyc["arm_peak_vel"]
        coast_mask   = seg_v < coast_thresh
        cyc["coast_fraction"] = float(coast_mask.sum() / max(1, len(seg_v)))

        # Arm-kick delay
        if cyc["kick_peak_idx"] is not None:
            cyc["arm_kick_delay_s"] = float(t[cyc["kick_peak_idx"]] - t[cyc["arm_peak_idx"]])
            cyc["arm_kick_vel_ratio"] = (float(cyc["kick_peak_vel"]) /
                                         float(cyc["arm_peak_vel"]))
        else:
            cyc["arm_kick_delay_s"]    = None
            cyc["arm_kick_vel_ratio"]  = None

    # ── session-level summary (ALL cycles — Phase 61-01 D5) ───────────────
    # stroke_count IS the total cycle count. Before 61-01 it was the steady-state count,
    # which is why the per-cycle charts showed more dots than the number beside them.
    n_cycles   = len(cycles)

    if cycles:
        mean_dur        = float(np.mean([c["duration_s"] for c in cycles]))
        stroke_rate_spm = 60.0 / mean_dur
    else:
        stroke_rate_spm = float("nan")

    session = {
        "lap_time_s":          float(t[-1]),
        "total_dist_m":        float(dist[-1]),
        "baseline_end_s":      float(t[b_end]),
        "stroke_rate_spm":     stroke_rate_spm,
        "stroke_count":        n_cycles,
        "mean_vel_ms":         float(np.mean(vel_swim[vel_swim > 0])) if vel_swim.size else float("nan"),
        "max_vel_ms":          float(np.max(vel_swim)) if vel_swim.size else float("nan"),
    }

    if n_cycles > 0:
        arm_vels   = np.array([c["arm_peak_vel"]   for c in cycles])
        durations  = np.array([c["duration_s"]     for c in cycles])
        dists      = np.array([c["dist_m"]         for c in cycles])
        impulses   = np.array([c["impulse_m"]      for c in cycles])
        coast_vals = np.array([c["coast_fraction"] for c in cycles])
        trough     = np.array([c["trough_vel_ms"]  for c in cycles])

        session["mean_arm_peak_vel_ms"] = float(arm_vels.mean())
        session["cv_arm_peak_vel"]      = float(arm_vels.std() / arm_vels.mean())
        session["mean_isi_s"]           = float(durations.mean())
        session["cv_isi"]               = float(durations.std() / durations.mean())
        session["mean_dps_m"]           = float(dists.mean())
        session["mean_impulse_m"]       = float(impulses.mean())
        session["mean_coast_fraction"]  = float(coast_vals.mean())
        session["mean_trough_vel_ms"]   = float(trough.mean())

        # Fatigue index: (mean of first quarter peak vel − last quarter) / first quarter
        q    = max(1, n_cycles // 4)
        q1   = float(arm_vels[:q].mean())
        q4   = float(arm_vels[-q:].mean())
        session["fatigue_index_pct"] = (q1 - q4) / q1 * 100.0

        # Kick metrics (only cycles where kick was detected)
        kick_ratios = [c["arm_kick_vel_ratio"] for c in cycles
                       if c["arm_kick_vel_ratio"] is not None]
        kick_delays = [c["arm_kick_delay_s"]   for c in cycles
                       if c["arm_kick_delay_s"]   is not None]
        session["pct_cycles_with_kick"] = len(kick_ratios) / n_cycles * 100.0
        if kick_ratios:
            session["mean_arm_kick_ratio"]  = float(np.mean(kick_ratios))
            session["mean_arm_kick_delay_s"] = float(np.mean(kick_delays))
        else:
            session["mean_arm_kick_ratio"]   = None
            session["mean_arm_kick_delay_s"] = None
    else:
        for k in ("mean_arm_peak_vel_ms", "cv_arm_peak_vel", "mean_isi_s", "cv_isi",
                  "mean_dps_m", "mean_impulse_m", "mean_coast_fraction", "mean_trough_vel_ms",
                  "fatigue_index_pct",
                  "pct_cycles_with_kick", "mean_arm_kick_ratio", "mean_arm_kick_delay_s"):
            session[k] = None

    # ── cycle quality ─────────────────────────────────────────────────────────
    total_cycles_raw = len(cycles)

    # Outlier: cycle with duration < 80% of median (all cycles since Phase 61-01)
    outlier_cycle_count = 0
    if cycles:
        med_dur = float(np.median([c["duration_s"] for c in cycles]))
        outlier_cycle_count = sum(1 for c in cycles if c["duration_s"] < 0.80 * med_dur)

    # Implausible: any cycle outside physically reasonable breaststroke range
    implausible_cycle_count = sum(
        1 for c in cycles
        if c["duration_s"] < 0.5 or c["duration_s"] > 4.0
    )

    session["total_cycles_raw"]        = total_cycles_raw
    session["outlier_cycle_count"]     = outlier_cycle_count
    session["implausible_cycle_count"] = implausible_cycle_count
    session["kick_metrics_reliable"]   = False  # LP filter merges arm/kick; see CLAUDE.md
    # Wavelet ridge shipped as placeholder (16-05) → False; human-annotated cycle
    # boundaries (Phase 47) ARE the ground truth → True.
    session["segmentation_reliable"]   = bool(manual_bounds)

    return {"session": session, "cycles": cycles, "initial_phase": initial_phase}


# ── pose integration ─────────────────────────────────────────────────────

def attach_pose_to_cycles(cycles, merged_df, t):
    """
    Attach pose-derived metrics to each cycle dict in-place.

    merged_df comes from merge_streams.py: encoder columns + pose columns,
    joined on time_s.  t is the same time array used for segmentation so
    cycle indices map back to timestamps.

    Adds to each cycle dict:
        mean_elbow_angle_at_arm_peak  – mean(l, r) elbow angle at arm-pull peak frame
        mean_knee_angle_at_kick       – mean(l, r) knee angle at kick peak frame (None if no kick)
        elbow_symmetry                – mean |l_elbow - r_elbow| over the pull phase
                                        (start_idx → arm_peak_idx)

    Cycles with no matching pose rows get None for all three keys.
    Returns cycles for convenience.
    """
    pose_cols = ["l_elbow_angle_deg", "r_elbow_angle_deg",
                 "l_knee_angle_deg",  "r_knee_angle_deg"]

    # Bail out gracefully if pose columns aren't in the merged file
    if not all(c in merged_df.columns for c in pose_cols):
        for cyc in cycles:
            cyc["mean_elbow_angle_at_arm_peak"] = None
            cyc["mean_knee_angle_at_kick"]       = None
            cyc["elbow_symmetry"]                = None
        return cycles

    ts = merged_df["time_s"].values

    def _nearest_row(target_t):
        """Return the merged_df row closest to target_t, or None if all NaN."""
        idx = int(np.argmin(np.abs(ts - target_t)))
        row = merged_df.iloc[idx]
        return row if pd.notna(row["l_elbow_angle_deg"]) else None

    def _window_rows(t_lo, t_hi):
        """Return merged_df rows where time_s is in [t_lo, t_hi]."""
        mask = (ts >= t_lo) & (ts <= t_hi)
        return merged_df[mask]

    for cyc in cycles:
        # ── elbow angle at arm-pull peak ──────────────────────────────────
        arm_t = float(t[cyc["arm_peak_idx"]])
        row   = _nearest_row(arm_t)
        if row is not None:
            l_el = row["l_elbow_angle_deg"]
            r_el = row["r_elbow_angle_deg"]
            vals = [v for v in (l_el, r_el) if pd.notna(v)]
            cyc["mean_elbow_angle_at_arm_peak"] = float(np.mean(vals)) if vals else None
        else:
            cyc["mean_elbow_angle_at_arm_peak"] = None

        # ── knee angle at kick peak ────────────────────────────────────────
        if cyc.get("kick_peak_idx") is not None:
            kick_t = float(t[cyc["kick_peak_idx"]])
            row_k  = _nearest_row(kick_t)
            if row_k is not None:
                l_kn = row_k["l_knee_angle_deg"]
                r_kn = row_k["r_knee_angle_deg"]
                vals = [v for v in (l_kn, r_kn) if pd.notna(v)]
                cyc["mean_knee_angle_at_kick"] = float(np.mean(vals)) if vals else None
            else:
                cyc["mean_knee_angle_at_kick"] = None
        else:
            cyc["mean_knee_angle_at_kick"] = None

        # ── elbow symmetry over pull phase (start → arm peak) ─────────────
        pull_rows = _window_rows(float(t[cyc["start_idx"]]), arm_t)
        if len(pull_rows) > 0:
            diff = (pull_rows["l_elbow_angle_deg"] - pull_rows["r_elbow_angle_deg"]).abs()
            diff = diff.dropna()
            cyc["elbow_symmetry"] = float(diff.mean()) if len(diff) > 0 else None
        else:
            cyc["elbow_symmetry"] = None

    return cycles


# ── helpers ───────────────────────────────────────────────────────────────

def _compute_fs(t):
    return 1.0 / float(np.diff(t).mean())


def _estimate_period(t, vel):
    """
    Estimate stroke period (seconds) from the autocorrelation of velocity.

    Removes DC (mean) before computing ACF so slow drift doesn't bias the
    result.  Searches for the first ACF peak between 0.5 s and 4.0 s —
    the physically possible range for breaststroke (15–120 SPM).

    Returns the estimated period in seconds, or None if the ACF has no
    clear peak (e.g. too few cycles, very noisy signal).
    """
    fs = _compute_fs(t)
    v  = np.nan_to_num(vel - np.nanmean(vel))   # remove DC, replace NaN with 0

    acf = np.correlate(v, v, mode="full")
    acf = acf[len(acf) // 2:]                   # keep positive lags only
    if acf[0] == 0:
        return None
    acf /= acf[0]                               # normalise to [−1, 1]

    # Search window: 0.5 s → 4.0 s
    lo = max(1, int(0.5 * fs))
    hi = min(len(acf) - 1, int(4.0 * fs))
    if lo >= hi:
        return None

    peaks, _ = find_peaks(acf[lo:hi])
    if len(peaks) == 0:
        return None

    # First peak in the search window = fundamental stroke period
    return float((peaks[0] + lo) / fs)


# ── CLI ───────────────────────────────────────────────────────────────────

def _print_results(csv_file, result):
    t   = result["_t"]
    s   = result["session"]
    sep = "=" * 58

    print(f"\n{sep}")
    print(f"  {csv_file}")
    print(sep)
    for k, v in s.items():
        if v is None:
            val = "—"
        elif isinstance(v, float):
            val = f"{v:.4f}"
        else:
            val = str(v)
        print(f"  {k:<32}  {val}")

    if result.get("_print_cycles"):
        ss = result["cycles"]
        print(f"\n  Per-cycle  (n={len(ss)})")
        print(f"  {'#':<4} {'t_peak':>7} {'v_arm':>7} {'trough':>8} {'coast%':>7} {'dur':>6} {'dps':>6}")
        for i, c in enumerate(ss):
            print(f"  {i+1:<4} {t[c['peak_idx']]:7.2f} {c['arm_peak_vel']:7.3f}"
                  f" {c['trough_vel_ms']:8.3f} {c['coast_fraction']*100:6.1f}%"
                  f"  {c['duration_s']:6.3f} {c['dist_m']:6.3f}")


def _plot_results(title, t_full, vel_full, dist_full, t_start=None, t_end=None):
    from matplotlib.widgets import RangeSlider
    from matplotlib.patches import Patch

    _CYCLE_COLOR   = "#4a90d9"
    _PARTIAL_COLOR = "#aaaaaa"
    _OUTLIER_COLOR = "#e8a0a0"   # pinkish — short/suspect cycles shown but flagged
    _EXCL_COLOR    = "#dddddd"
    _GRID_KW       = dict(color="#e0e0e0", linewidth=0.6)

    lo_init = t_start if t_start is not None else float(t_full[0])
    hi_init = t_end   if t_end   is not None else float(t_full[-1])

    fig = plt.figure(figsize=(15, 9))
    fig.suptitle(str(title), fontsize=10, y=0.99)

    gs = gridspec.GridSpec(2, 4, figure=fig, hspace=0.6, wspace=0.38,
                           top=0.93, bottom=0.18)
    ax_vel = fig.add_subplot(gs[0, :])
    ax_spd = fig.add_subplot(gs[1, 0])
    ax_dps = fig.add_subplot(gs[1, 1])
    ax_cst = fig.add_subplot(gs[1, 2])
    ax_isi = fig.add_subplot(gs[1, 3])

    ax_sl = fig.add_axes([0.1, 0.05, 0.8, 0.03])
    fig.text(0.5, 0.10, "Analysis window (s)", ha="center", va="bottom", fontsize=8)
    slider = RangeSlider(ax_sl, "", float(t_full[0]), float(t_full[-1]),
                         valinit=(lo_init, hi_init))

    def _draw(lo, hi):
        mask = (t_full >= lo) & (t_full <= hi)
        if mask.sum() < 10:
            return
        t_w    = t_full[mask]
        vel_w  = vel_full[mask]
        dist_w = dist_full[mask] - dist_full[mask][0]

        try:
            result_w = compute_session_metrics(t_w, vel_w, dist_w)
        except Exception:
            return

        cycles = result_w["cycles"]

        # Interior cycles: drop first and last (window-edge boundary artifacts)
        interior = cycles[1:-1] if len(cycles) > 2 else cycles

        # Flag outlier cycles: duration < 0.80 × median — still shown but greyed
        if len(interior) > 2:
            med_dur  = float(np.median([c["duration_s"] for c in interior]))
            is_out   = [c["duration_s"] < 0.80 * med_dur for c in interior]
        else:
            is_out   = [False] * len(interior)

        # ── velocity trace ───────────────────────────────────────────────
        ax_vel.cla()
        ax_vel.axvspan(t_full[0], lo,        alpha=0.35, color=_EXCL_COLOR, zorder=0)
        ax_vel.axvspan(hi,        t_full[-1], alpha=0.35, color=_EXCL_COLOR, zorder=0)
        ax_vel.plot(t_full, vel_full, color="#aaaaaa", lw=0.8, zorder=1)
        ax_vel.axhline(0, color="#999999", lw=0.5, ls="--")

        interior_set = set(id(c) for c in interior)
        outlier_set  = set(id(c) for c, o in zip(interior, is_out) if o)

        for i, cyc in enumerate(cycles):
            a         = cyc["start_idx"]
            b         = min(cyc["end_idx"], len(t_w) - 1)
            is_bnd    = (i == 0 or i == len(cycles) - 1)
            is_outlier = id(cyc) in outlier_set

            if is_bnd:
                c_shade = _PARTIAL_COLOR
            elif is_outlier:
                c_shade = _OUTLIER_COLOR
            else:
                c_shade = _CYCLE_COLOR

            # Shade cycle region on the velocity trace
            ax_vel.axvspan(t_w[a], t_w[b], alpha=0.18, color=c_shade, zorder=2)
            ax_vel.axvline(t_w[a], color=c_shade, lw=0.7, alpha=0.6, zorder=2)
            ax_vel.plot(t_w[cyc["peak_idx"]], vel_w[cyc["peak_idx"]],
                        marker="^", ms=7, color=c_shade, zorder=3)

            # Number label — stagger alternating peaks up/down to avoid overlap
            y_offset = 8 if i % 2 == 0 else 18
            label    = "b" if is_bnd else str(i)
            ax_vel.annotate(
                label,
                xy=(t_w[cyc["peak_idx"]], vel_w[cyc["peak_idx"]]),
                xytext=(0, y_offset), textcoords="offset points",
                ha="center", va="bottom", fontsize=6,
                color=c_shade, fontweight="bold",
            )

        ax_vel.set_xlabel("Time (s)", fontsize=8)
        ax_vel.set_ylabel("Velocity (m/s)", fontsize=8)
        ax_vel.set_title("Velocity trace  (▲ = arm-pull peak, numbered to match charts below)", fontsize=8)
        ax_vel.tick_params(labelsize=7)
        ax_vel.grid(**_GRID_KW)
        ax_vel.set_xlim(t_full[0], t_full[-1])
        ax_vel.legend(
            handles=[Patch(color=_CYCLE_COLOR,   alpha=0.5, label="cycle"),
                     Patch(color=_OUTLIER_COLOR, alpha=0.5, label="short cycle (flagged)"),
                     Patch(color=_PARTIAL_COLOR, alpha=0.5, label="boundary (excluded)"),
                     Patch(color=_EXCL_COLOR,    alpha=0.6, label="outside window")],
            fontsize=7, loc="lower right", ncol=2)

        # ── per-cycle bar charts ─────────────────────────────────────────
        if not interior:
            for ax in (ax_spd, ax_dps, ax_cst, ax_isi):
                ax.cla()
            fig.canvas.draw_idle()
            return

        labels = [str(i + 1) for i in range(len(interior))]
        bar_colors = []
        for cyc, out in zip(interior, is_out):
            bar_colors.append(_OUTLIER_COLOR if out else _CYCLE_COLOR)

        def _bar(ax, values, ylabel, title_str, fmt=".2f", scale=1.0, mean_val=None):
            ax.cla()
            vals = [v * scale if v is not None else float("nan") for v in values]
            xs   = list(range(len(vals)))

            bars = ax.bar(labels, vals, color=bar_colors, edgecolor="white", linewidth=0.4)

            # Hatch outlier bars so they're doubly distinct
            for bar, out in zip(bars, is_out):
                if out:
                    bar.set_hatch("//")
                    bar.set_edgecolor("#cc6666")

            # Trend line over non-outlier bars only
            good = [(x, v) for x, v, o in zip(xs, vals, is_out)
                    if not o and not np.isnan(v)]
            if len(good) >= 2:
                gx, gv = zip(*good)
                ax.plot(list(gx), list(gv), color="#333333", lw=1.2,
                        marker="o", ms=3, zorder=4)

            if mean_val is not None:
                ax.axhline(mean_val * scale, color="#888888", lw=1.0, ls="--",
                           label=f"mean {mean_val * scale:{fmt}}")
                ax.legend(fontsize=6, handlelength=1.2)

            # Y-axis: lo anchored to global min (so outlier bars stay visible),
            # hi and padding based on non-outlier spread so variation is readable
            all_vals  = [v for v in vals if not np.isnan(v)]
            good_vals = [v for v, o in zip(vals, is_out) if not o and not np.isnan(v)]
            if good_vals and all_vals:
                lo_y = min(all_vals)
                hi_y = max(good_vals)
                pad  = (max(good_vals) - min(good_vals)) * 0.35 if len(good_vals) > 1 else hi_y * 0.05
                ax.set_ylim(lo_y - pad * 0.5, hi_y + pad)

            ax.set_xlabel("Cycle #", fontsize=8)
            ax.set_ylabel(ylabel, fontsize=8)
            ax.set_title(title_str, fontsize=8)
            ax.tick_params(labelsize=7)
            ax.grid(axis="y", **_GRID_KW)

        # Mean excludes outlier cycles
        def _mean(key, scale=1.0):
            vals = [c[key] for c, o in zip(interior, is_out)
                    if not o and c.get(key) is not None]
            return float(np.mean(vals)) / scale if vals else None

        _bar(ax_spd, [c["arm_peak_vel"]  for c in interior],
             "m/s", "Arm-pull peak velocity",
             mean_val=_mean("arm_peak_vel"))
        _bar(ax_dps, [c["dist_m"]         for c in interior],
             "m",   "Distance per stroke",
             mean_val=_mean("dist_m"))
        _bar(ax_cst, [c["coast_fraction"] for c in interior],
             "%",   "Coast fraction", scale=100.0,
             mean_val=_mean("coast_fraction"))
        _bar(ax_isi, [c["duration_s"]     for c in interior],
             "s",   "Cycle duration (ISI)",
             mean_val=_mean("duration_s"))

        fig.canvas.draw_idle()

    slider.on_changed(lambda val: _draw(*val))
    _draw(lo_init, hi_init)
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Extract breaststroke metrics from a processed CSV.")
    parser.add_argument(
        "input", nargs="?", default=f"processed/{SESSION_STEM}.csv",
        help="Processed CSV file or folder of CSV files (default: %(default)s)",
    )
    parser.add_argument(
        "--cycles", action="store_true",
        help="Print per-cycle breakdown in addition to the session summary",
    )
    parser.add_argument(
        "--plot", action="store_true",
        help="Show matplotlib charts for the velocity trace and per-cycle metrics",
    )
    parser.add_argument(
        "--start", type=float, default=None, metavar="T",
        help="Start time in seconds (inclusive); trim data before this point",
    )
    parser.add_argument(
        "--end", type=float, default=None, metavar="T",
        help="End time in seconds (inclusive); trim data after this point",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.is_dir():
        csv_files = sorted(input_path.glob("*.csv"))
        if not csv_files:
            print(f"No CSV files found in {input_path}")
            return
    elif input_path.suffix == ".csv":
        csv_files = [input_path]
    else:
        print(f"Error: {input_path} is not a CSV file or directory")
        return

    for csv_file in csv_files:
        df        = pd.read_csv(csv_file)
        t_full    = df["time_s"].values
        vel_full  = df["vel_ms"].values
        dist_full = df["dist_m"].values

        # Slice for text output
        t, vel, dist = t_full, vel_full, dist_full
        if args.start is not None or args.end is not None:
            lo   = args.start if args.start is not None else t_full[0]
            hi   = args.end   if args.end   is not None else t_full[-1]
            mask = (t_full >= lo) & (t_full <= hi)
            t    = t_full[mask]
            vel  = vel_full[mask]
            dist = dist_full[mask] - dist_full[mask][0]

        result = compute_session_metrics(t, vel, dist)
        result["_t"]            = t
        result["_print_cycles"] = args.cycles
        _print_results(csv_file, result)
        if args.plot:
            _plot_results(csv_file, t_full, vel_full, dist_full,
                          t_start=args.start, t_end=args.end)


if __name__ == "__main__":
    main()
