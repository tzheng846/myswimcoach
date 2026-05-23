"""
metrics.py — Breaststroke feature extraction from processed tether-wheel data.

Inputs:  t (s), vel (m/s), dist (m) as numpy arrays at a uniform sample rate.
Outputs: dicts from compute_session_metrics() and segment_cycles().

All functions are pure (no I/O, no plots).
"""

import argparse
import numpy as np
import pandas as pd
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


# ── SEGMENTATION ─────────────────────────────────────────────────────────────

def detect_phases(t, vel):
    """
    Identify baseline and swimming regions.

    Returns dict with integer indices into t/vel:
        baseline_end   – last index of the near-zero baseline
        steady_start   – same as baseline_end (ramp-up flagged per-cycle later)
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



def segment_cycles_trough(t, vel):
    """
    Segment at deep velocity troughs (glide phase) — literature-recommended
    approach for breaststroke.

    The tethered-wheel velocity drops near zero during each glide; those deep
    minima are unambiguous cycle boundaries and are immune to the arm+kick
    double-peak problem.  The dominant peak within each trough-bounded segment
    becomes the stroke anchor.

    Requires no T_cycle estimate.  Returns same format as segment_cycles,
    or None if fewer than 2 qualifying troughs are found.
    """
    fs  = _compute_fs(t)
    n   = len(vel)
    v95 = float(np.percentile(np.abs(vel), 95))

    # Glide troughs: velocity below 20 % of v95, at least 0.5 s apart.
    # 0.5 s corresponds to 120 SPM — faster than any realistic breaststroke.
    troughs, _ = find_peaks(
        -vel,
        height   = -0.20 * v95,          # vel must be < 0.20 × v95
        distance = max(1, int(0.5 * fs)),
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
    For each trough-bounded segment, find all prominent peaks in chronological order.
    First peak = arm pull, second peak = kick.

    Mutates each cycle dict in-place, adding:
        arm_peak_idx   – index of the pull peak
        arm_peak_vel   – velocity at pull peak (m/s)
        kick_peak_idx  – index of the kick peak, or None if only one peak found
        kick_peak_vel  – velocity at kick peak, or None
    Also updates peak_idx to match arm_peak_idx.
    Returns the same list for convenience.
    """
    v95 = float(np.percentile(np.abs(vel), 95))
    min_prom = _PEAK_MIN_PROM_FRAC * v95

    for cyc in cycles:
        a, b = cyc["start_idx"], cyc["end_idx"]
        seg  = vel[a:b]

        peaks, _ = find_peaks(seg, prominence=min_prom)

        if len(peaks) == 0:
            # No prominent peak — use argmax as fallback pull anchor
            pull_off = int(np.argmax(seg))
            cyc["arm_peak_idx"] = a + pull_off
            cyc["arm_peak_vel"] = float(seg[pull_off])
            cyc["kick_peak_idx"] = None
            cyc["kick_peak_vel"] = None
        elif len(peaks) == 1:
            cyc["arm_peak_idx"] = a + int(peaks[0])
            cyc["arm_peak_vel"] = float(seg[peaks[0]])
            cyc["kick_peak_idx"] = None
            cyc["kick_peak_vel"] = None
        else:
            # First chronologically = pull, second = kick
            # If >2 peaks, kick is the highest among peaks[1:]
            pull_off = int(peaks[0])
            kick_off = int(peaks[1]) if len(peaks) == 2 else int(peaks[1:][np.argmax(seg[peaks[1:]])])
            cyc["arm_peak_idx"] = a + pull_off
            cyc["arm_peak_vel"] = float(seg[pull_off])
            cyc["kick_peak_idx"] = a + kick_off
            cyc["kick_peak_vel"] = float(seg[kick_off])

        cyc["peak_idx"] = cyc["arm_peak_idx"]

    return cycles


# ── METRICS ──────────────────────────────────────────────────────────────────

def compute_session_metrics(t, vel, dist, head_waist_m=0.0):
    """
    Top-level function: run the full breaststroke analysis pipeline.

    Returns a dict with two keys:
        'session'   – single-value session-level metrics
        'cycles'    – list of per-cycle dicts (one entry per stroke)
    """
    fs  = _compute_fs(t)
    v95 = float(np.percentile(np.abs(vel), 95))

    # ── phase detection ────────────────────────────────────────────────────
    phases   = detect_phases(t, vel)
    b_end    = phases["baseline_end"]
    swim_end = phases["swim_end"]

    # ── initial phase detection (dive + pulldown) ──────────────────────────
    initial_phase = detect_initial_phase(t, vel, b_end)
    ip_end = initial_phase["initial_phase_end_idx"]

    # ── segmentation (from initial-phase end to swim_end) ──────────────────
    t_seg    = t[ip_end:swim_end]
    vel_seg  = vel[ip_end:swim_end]
    vel_swim = vel[b_end:swim_end]   # full window for session velocity stats

    cycles = segment_cycles_trough(t_seg, vel_seg)
    if cycles is None:
        cycles = []

    # Offset indices so they map back to the full-trace arrays
    for c in cycles:
        c["start_idx"] += ip_end
        c["end_idx"]   += ip_end
        c["peak_idx"]  += ip_end

    # Tag cycles as ramp-up or steady based on arm-pull velocity.
    # steady_floor = 50% of the 75th-pct peak velocity across all cycles.
    # After initial tagging, promote isolated ramp_up cycles surrounded by steady cycles.
    if cycles:
        arm_vels     = np.array([vel[c["peak_idx"]] for c in cycles])
        steady_floor = 0.50 * float(np.percentile(arm_vels, 75))
        phases_raw   = [vel[c["peak_idx"]] >= steady_floor for c in cycles]
        # Smooth: an isolated False surrounded by True on both sides becomes True
        phases_smooth = list(phases_raw)
        for i in range(1, len(phases_raw) - 1):
            if not phases_raw[i] and phases_raw[i - 1] and phases_raw[i + 1]:
                phases_smooth[i] = True
        for cyc, is_steady in zip(cycles, phases_smooth):
            cyc["phase"] = "steady" if is_steady else "ramp_up"

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

        # Dead spot: |vel| < 10% of v95 (global threshold, matches swim_metrics.ipynb)
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

    # ── session-level summary (steady-state cycles only) ──────────────────
    ss_cycles  = [c for c in cycles if c.get("phase") == "steady"]
    n_ss       = len(ss_cycles)

    if ss_cycles:
        mean_dur        = float(np.mean([c["duration_s"] for c in ss_cycles]))
        stroke_rate_spm = 60.0 / mean_dur
    else:
        stroke_rate_spm = float("nan")

    session = {
        "lap_time_s":          float(t[-1]),
        "total_dist_m":        float(dist[-1]),
        "baseline_end_s":      float(t[b_end]),
        "stroke_rate_spm":     stroke_rate_spm,
        "stroke_count":        n_ss,
        "mean_vel_ms":         float(np.mean(vel_swim[vel_swim > 0])) if vel_swim.size else float("nan"),
        "max_vel_ms":          float(np.max(vel_swim)) if vel_swim.size else float("nan"),
    }

    if n_ss > 0:
        arm_vels_ss  = np.array([c["arm_peak_vel"] for c in ss_cycles])
        durations_ss = np.array([c["duration_s"]   for c in ss_cycles])
        dists_ss     = np.array([c["dist_m"]         for c in ss_cycles])
        impulses_ss  = np.array([c["impulse_m"]      for c in ss_cycles])
        coast_ss     = np.array([c["coast_fraction"] for c in ss_cycles])
        trough_ss    = np.array([c["trough_vel_ms"]  for c in ss_cycles])

        session["mean_arm_peak_vel_ms"] = float(arm_vels_ss.mean())
        session["cv_arm_peak_vel"]      = float(arm_vels_ss.std() / arm_vels_ss.mean())
        session["mean_isi_s"]           = float(durations_ss.mean())
        session["cv_isi"]               = float(durations_ss.std() / durations_ss.mean())
        session["mean_dps_m"]           = float(dists_ss.mean())
        session["mean_impulse_m"]       = float(impulses_ss.mean())
        session["mean_coast_fraction"]  = float(coast_ss.mean())
        session["mean_trough_vel_ms"]   = float(trough_ss.mean())

        # Fatigue index: (mean of first quarter peak vel − last quarter) / first quarter
        q    = max(1, n_ss // 4)
        q1   = float(arm_vels_ss[:q].mean())
        q4   = float(arm_vels_ss[-q:].mean())
        session["fatigue_index_pct"] = (q1 - q4) / q1 * 100.0

        # Kick metrics (only cycles where kick was detected)
        kick_ratios = [c["arm_kick_vel_ratio"] for c in ss_cycles
                       if c["arm_kick_vel_ratio"] is not None]
        kick_delays = [c["arm_kick_delay_s"]   for c in ss_cycles
                       if c["arm_kick_delay_s"]   is not None]
        session["pct_cycles_with_kick"] = len(kick_ratios) / n_ss * 100.0
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
        ss = [c for c in result["cycles"] if c.get("phase") == "steady"]
        print(f"\n  Per-cycle  (steady, n={len(ss)})")
        print(f"  {'#':<4} {'t_peak':>7} {'v_arm':>7} {'trough':>8} {'coast%':>7} {'dur':>6} {'dps':>6}")
        for i, c in enumerate(ss):
            print(f"  {i+1:<4} {t[c['peak_idx']]:7.2f} {c['arm_peak_vel']:7.3f}"
                  f" {c['trough_vel_ms']:8.3f} {c['coast_fraction']*100:6.1f}%"
                  f"  {c['duration_s']:6.3f} {c['dist_m']:6.3f}")


def _plot_results(title, t_full, vel_full, dist_full, t_start=None, t_end=None):
    from matplotlib.widgets import RangeSlider
    from matplotlib.patches import Patch

    _RAMP_COLOR    = "#f5a623"
    _STEADY_COLOR  = "#4a90d9"
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
                c_shade = _STEADY_COLOR if cyc.get("phase") == "steady" else _RAMP_COLOR

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
            handles=[Patch(color=_STEADY_COLOR,  alpha=0.5, label="steady"),
                     Patch(color=_RAMP_COLOR,    alpha=0.5, label="ramp-up"),
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
            if out:
                bar_colors.append(_OUTLIER_COLOR)
            elif cyc.get("phase") == "steady":
                bar_colors.append(_STEADY_COLOR)
            else:
                bar_colors.append(_RAMP_COLOR)

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
