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
from scipy.fft import rfft, rfftfreq
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
# NOTE: the 2.5 Hz LP filter applied in vel_acc_extraction.py merges the arm-pull
# and leg-kick contributions into one broad peak. Kick detection is therefore only
# viable if the processed file used a higher LP cutoff. With the default 2.5 Hz
# filter, pct_cycles_with_kick will typically be 0.
_KICK_MIN_PROM_FRAC  = 0.10   # kick peak prominence must exceed this × v95
_KICK_MIN_VEL_FRAC   = 0.30   # kick velocity must exceed this × arm-pull velocity
_DEAD_SPOT_THRESH    = 0.10   # |vel| below this × v95 → dead spot
_COAST_FRAC_THRESH   = 0.50   # |vel| below this × arm_peak_vel → coasting (per cycle)


# ── public API ───────────────────────────────────────────────────────────────

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

    return {"baseline_end": b_end, "steady_start": b_end}


def estimate_cycle_frequency(t, vel):
    """
    Estimate breaststroke cycle frequency from the FFT of vel.

    Returns dict:
        f_cycle_hz      – dominant cycle frequency (Hz)
        stroke_rate_spm – strokes per minute
        T_cycle_s       – stroke period (s)
    """
    dt    = _compute_fs(t) ** -1
    N     = len(vel)
    freqs = rfftfreq(N, d=dt)
    spec  = np.abs(rfft(vel - vel.mean())) / N
    band  = (freqs >= 0.3) & (freqs <= 2.0)
    f_cyc = float(freqs[band][np.argmax(spec[band])])
    return {
        "f_cycle_hz":      f_cyc,
        "stroke_rate_spm": f_cyc * 60.0,
        "T_cycle_s":       1.0 / f_cyc,
    }


def segment_cycles(t, vel, T_cycle):
    """
    Segment the velocity trace into individual stroke cycles.

    Strategy: find arm-pull peaks (the dominant positive velocity peak, one
    per cycle) using height + distance guards, then place each cycle boundary
    at the velocity minimum between consecutive peaks.

    Returns list of dicts, one per cycle:
        peak_idx    – index of the arm-pull peak
        start_idx   – index of the cycle's left boundary (inclusive)
        end_idx     – index of the cycle's right boundary (exclusive)
    """
    fs        = _compute_fs(t)
    v95       = float(np.percentile(np.abs(vel), 95))
    peak_dist = max(1, int(_PEAK_DIST_FRAC * T_cycle * fs))
    peaks, _  = find_peaks(vel, height=_PEAK_HEIGHT_FRAC * v95, distance=peak_dist)

    if len(peaks) < 2:
        return []

    # Cycle boundaries: argmin of vel between consecutive peaks
    bounds = [0]
    for i in range(len(peaks) - 1):
        seg    = vel[peaks[i] : peaks[i + 1]]
        offset = int(np.argmin(seg))
        bounds.append(peaks[i] + offset)
    bounds.append(len(vel))

    cycles = []
    for i, pk in enumerate(peaks):
        cycles.append({
            "peak_idx":  int(pk),
            "start_idx": int(bounds[i]),
            "end_idx":   int(bounds[i + 1]),
        })
    return cycles


def extract_cycle_peaks(vel, cycles):
    """
    For each cycle segment find the arm-pull peak and (optionally) the kick peak.

    Mutates each cycle dict in-place, adding:
        arm_peak_idx   – index of the arm-pull peak (same as cycle['peak_idx'])
        arm_peak_vel   – velocity at arm-pull peak (m/s)
        kick_peak_idx  – index of the kick peak, or None
        kick_peak_vel  – velocity at kick peak, or None
        arm_kick_delay – time between arm and kick peak (s), or None
    Returns the same list for convenience.
    """
    v95 = float(np.percentile(np.abs(vel), 95))
    min_kick_prom = _KICK_MIN_PROM_FRAC * v95

    for cyc in cycles:
        a, b      = cyc["start_idx"], cyc["end_idx"]
        seg       = vel[a:b]
        arm_idx   = cyc["peak_idx"]
        arm_vel   = float(vel[arm_idx])

        cyc["arm_peak_idx"] = arm_idx
        cyc["arm_peak_vel"] = arm_vel

        # Search for kick peak: local max in seg, distinct from arm-pull
        sub_peaks, props = find_peaks(seg, prominence=min_kick_prom)
        # Exclude the arm-pull itself
        arm_off   = arm_idx - a
        # Kick always follows the arm pull; only search after arm_off
        sub_peaks = sub_peaks[sub_peaks > arm_off]

        if len(sub_peaks) > 0:
            best     = sub_peaks[np.argmax(seg[sub_peaks])]
            kick_vel = float(seg[best])
            # Require kick to be at least 30% of arm-pull velocity
            if kick_vel >= _KICK_MIN_VEL_FRAC * arm_vel:
                kick_idx = a + int(best)
                cyc["kick_peak_idx"] = kick_idx
                cyc["kick_peak_vel"] = kick_vel
            else:
                cyc["kick_peak_idx"] = None
                cyc["kick_peak_vel"] = None
        else:
            cyc["kick_peak_idx"] = None
            cyc["kick_peak_vel"] = None

    return cycles


def compute_session_metrics(t, vel, dist):
    """
    Top-level function: run the full breaststroke analysis pipeline.

    Returns a dict with two keys:
        'session'   – single-value session-level metrics
        'cycles'    – list of per-cycle dicts (one entry per stroke)
    """
    fs  = _compute_fs(t)
    v95 = float(np.percentile(np.abs(vel), 95))

    # ── phase detection ────────────────────────────────────────────────────
    phases    = detect_phases(t, vel)
    ss_start  = phases["steady_start"]

    t_ss   = t[ss_start:]
    vel_ss = vel[ss_start:]
    dist_ss = dist[ss_start:]

    # ── cycle frequency ───────────────────────────────────────────────────
    freq_info = estimate_cycle_frequency(t_ss, vel_ss)
    T_cycle   = freq_info["T_cycle_s"]

    # ── segmentation (full trace so indices are absolute) ─────────────────
    cycles = segment_cycles(t, vel, T_cycle)

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

    session = {
        "lap_time_s":          float(t[-1]),
        "total_dist_m":        float(dist[-1]),
        "baseline_end_s":      float(t[phases["baseline_end"]]),
        "stroke_rate_spm":     freq_info["stroke_rate_spm"],
        "stroke_count":        n_ss,
        "mean_vel_ms":         float(np.mean(vel_ss[vel_ss > 0])) if vel_ss.size else float("nan"),
        "max_vel_ms":          float(np.max(vel_ss)),
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

    return {"session": session, "cycles": cycles}


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
