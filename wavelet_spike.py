"""
wavelet_spike.py — Spike: Morlet CWT stroke-rate ridge vs. trough-based
cycle segmentation. Opens an overlay comparison as an HTML page in the browser.

Standalone diagnostic — does not modify metrics.py or any production file.

Per 16-03-SUMMARY.md, three shape-matching variants (single-template
motif-matching, chains/CAC, multi-length PMP — segment_motif_spike.py) all
failed the same underlying way: each asks "does this window's *shape*
resemble that window's shape," which degenerates under stroke-rate drift
(regime-locking) and structurally distinct sub-phases (dive/pulldown
contamination). This spike tests the reframe named the standing front-runner
since 16-01: instead of shape-matching, ask "what's the dominant oscillation
frequency *right now*" — a question where drift is the *expected output* (a
ridge is a time-varying rate estimate by definition) rather than a failure
mode to survive.

CLAUDE.md's "Wavelet notes" already document the recipe: a Morlet CWT
(`cmor1.5-1.0`) on velocity *detrended by a 3-second rolling mean* produces
"a clean stroke-rate ridge" (raw velocity produces dark nodes at stroke
boundaries because velocity genuinely touches near-zero between strokes —
detrending removes that artifact before the transform runs). This spike
implements that recipe directly: builds the scalogram, extracts the
per-instant ridge frequency, integrates it into cumulative phase
Φ(t) = ∫rate(t')dt', and places a candidate cycle boundary at each integer
crossing (16-01-SUMMARY's mechanism sketch — the same idea used to derive
heartbeat boundaries from a time-varying heart-rate signal).

Validation strategy (16-04-PLAN.md): cross-check ridge-derived boundaries
and implied rate against segment_cycles' trough-based output — and against
stroke_rate_spm — on the breaststroke sessions, where that output is already
trusted production ground truth. Only then is the same machinery's output on
freestyle/butterfly (no trough to anchor on, no ground truth to check
against) interpretable rather than just "looks plausible."

Usage
-----
    python wavelet_spike.py processed/session.csv
    python wavelet_spike.py processed/s1.csv processed/s2.csv
    python wavelet_spike.py processed/              # all CSVs in folder
"""

import argparse
import sys
import tempfile
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd
import pywt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import metrics as m

# ── colours ───────────────────────────────────────────────────────────────────
_C_VEL    = "#185fa5"
_C_TROUGH = "#aaaaaa"
_C_RIDGE  = "#d62728"
_C_RATE   = "#d62728"
_C_SPM    = "#2ca02c"

# Recipe per CLAUDE.md "Wavelet notes": Morlet cmor1.5-1.0, 3s rolling-mean
# detrend. Period search range mirrors segment_motif_spike's PMP sweep
# (metrics._estimate_period's own ACF window, "the physically possible range
# for breaststroke [15-120 SPM]") — an existing, validated bound, not a new
# threshold; freestyle/fly tempos fall well inside it too.
_WAVELET           = "cmor1.5-1.0"
_DETREND_WINDOW_S  = 3.0
_PERIOD_MIN_S      = 0.5
_PERIOD_MAX_S      = 4.0
_N_SCALES          = 80


# ── data ──────────────────────────────────────────────────────────────────────

def _load(csv_path):
    df     = pd.read_csv(csv_path)
    t      = df["time_s"].values
    vel    = df["vel_ms"].values
    dist   = df["dist_m"].values
    result = m.compute_session_metrics(t, vel, dist)
    return t, vel, dist, result


def _anchors_from_marks(vel, marks):
    """Boundary-mark indices -> {cycle_num, peak_idx, start_idx, end_idx}
    anchors (dominant peak per span), so trough and ridge segmentations
    overlay through the same shape. Mirrors segment_motif_spike's helper —
    duplicated rather than imported so this spike stays standalone and
    independent of the now-closed shape-matching family."""
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


def _boundary_times(t, cycles):
    if not cycles:
        return []
    xs = [t[c["start_idx"]] for c in cycles]
    xs.append(t[min(cycles[-1]["end_idx"], len(t) - 1)])
    return xs


# ── wavelet ridge ─────────────────────────────────────────────────────────────

# Jump-penalty weight for _track_ridge's DP cost (lambda * delta-log-freq^2 vs.
# -log of per-column-normalized power). Chosen empirically against connor_br_2
# (the session whose per-instant-argmax ridge visibly thrashed between ~4 bands,
# -41 SPM off production) -- large enough that a single-frame harmonic spike
# can't justify a jump-and-back, small enough that a genuinely sustained band
# change (the legitimate push-off -> stroke -> glide staircases connor_br_1/3/4
# already showed) still wins on accumulated power over the path.
_RIDGE_JUMP_PENALTY = 4.0

# Bias toward the lower-frequency band when two compete (in log-power cost
# per unit of log-frequency). sid_br_2/leo_br_1 showed two simultaneous bands
# roughly an octave apart (~2:1) -- on the user's reading, plausibly the
# stroke cycle and a kick-or-pull sub-motion nested inside it (CLAUDE.md's
# standing "kick metrics unreliable" limitation, viewed through a frequency
# lens instead of shape-matching's failed peak-resolution approach). The
# user's plan sequences these deliberately -- segment by stroke first, resolve
# kick/pull *within* already-known cycles later -- so this spike doesn't need
# to know which band physiologically *is* which, only that a stroke cycle is,
# by definition, the slower/outer oscillation a sub-motion nests inside, and a
# fixed "prefer lower" convention is what a from-scratch resolver would have
# to guess at anyway. ~0.5 nats of cost per octave: enough to swing a close
# call (e.g. two bands within ~40% power of each other, log-power gap ~0.3-0.5)
# toward the lower one, small enough that a clearly dominant *higher* band
# (the only band present -- most sessions) still wins outright.
_RIDGE_LOW_BAND_BIAS = 0.5


def _track_ridge(power, freqs_hz):
    """
    Continuity- and low-band-biased ridge extraction via dynamic programming
    -- replaces a per-instant argmax(power), which (a) can snap onto a
    harmonic for a few frames whenever it briefly outpowers the fundamental
    (the visible cause of connor_br_2's -41 SPM miss: a ridge that thrashed
    between ~4 bands instead of holding one -- though connor_br_2 turned out
    to be a sensor-dropout outlier, not a tracking failure), and (b) has no
    way to prefer one of two simultaneously-present, comparably-loud bands
    over the other (sid_br_2/leo_br_1's dual-band sessions).

    node_cost[f, t] = -log(normalized_power[f, t]) + BIAS * log_freq[f]
    cost[f, t]      = min over f' of { cost[f', t-1] + LAMBDA*(logfreq[f]-logfreq[f'])^2 }
                      + node_cost[f, t]

    Frequencies are compared in log-space throughout because pywt scales (and
    hence this axis) are geometrically spaced -- a fixed Hz delta means
    something very different at the low end of the range than the high end,
    but a fixed log-ratio doesn't (this is also why the bias is linear in
    log-freq: "half an octave" should cost the same whether it's a move from
    20->28 SPM or 60->85 SPM). Power is normalized per time-column (divided by
    its max) before taking -log, so neither term's relative weight drifts with
    a session's absolute CWT magnitude -- only the *shape* of each column's
    power distribution (which bands are present and how loud relative to each
    other) drives the choice, exactly the quantities a continuity/preference
    trade-off should run on.

    A single bad frame can't win a jump (one frame's power gain is capped by
    -log(1) = 0 at best); a sustained band change accumulates enough gain over
    many frames to outweigh the one-time jump cost. The bias only tips a
    *close* call -- a lone, clearly-dominant high band still wins outright,
    since BIAS*log_freq is small relative to a large -log(power) gap.

    Returns ridge_idx: the optimal scale-index path, same shape/role as the
    argmax(power, axis=0) it replaces.
    """
    n_scales, n_times = power.shape
    log_freqs = np.log(freqs_hz)
    jump_cost = _RIDGE_JUMP_PENALTY * (log_freqs[:, None] - log_freqs[None, :]) ** 2  # [from, to]

    col_max  = power.max(axis=0, keepdims=True)
    log_pow  = np.log(power / col_max + 1e-12)
    node_cost = -log_pow + (_RIDGE_LOW_BAND_BIAS * log_freqs)[:, None]

    cost     = np.empty((n_scales, n_times))
    backptr  = np.empty((n_scales, n_times), dtype=np.int64)
    cost[:, 0] = node_cost[:, 0]

    for ti in range(1, n_times):
        # totals[from, to] = cost-to-reach `from` at t-1, plus jumping `from`->`to`
        totals = cost[:, ti - 1][:, None] + jump_cost
        backptr[:, ti] = np.argmin(totals, axis=0)
        cost[:, ti] = totals[backptr[:, ti], np.arange(n_scales)] + node_cost[:, ti]

    path = np.empty(n_times, dtype=np.int64)
    path[-1] = np.argmin(cost[:, -1])
    for ti in range(n_times - 1, 0, -1):
        path[ti - 1] = backptr[path[ti], ti]
    return path


def _detrend(vel, fs):
    """Subtract a centered 3-second rolling mean — the documented fix for the
    near-zero dark-node artifact a raw-velocity CWT produces (velocity
    genuinely touches near-zero between strokes; detrending removes that
    so the transform sees oscillation shape, not the absolute level)."""
    window = max(3, int(round(_DETREND_WINDOW_S * fs)))
    rolling_mean = pd.Series(vel).rolling(window, center=True, min_periods=1).mean().values
    return vel - rolling_mean


def find_ridge(t, vel):
    """
    Morlet CWT on the detrended, masked active region -> instantaneous
    stroke-rate ridge -> integer-phase-crossing cycle boundaries.

    Masking mirrors find_motif_anchors (detect_phases supplies baseline_end /
    swim_end — the same boundaries the production pipeline already computes,
    no new threshold logic). Unlike stumpy's self-join, pywt.cwt can't run on
    NaN-containing input, so the transform runs on the active slice directly
    (vel[baseline_end:swim_end]) rather than a NaN-masked full-length array —
    a different masking *mechanism* than the shape-matching spike used, but
    the same masking *boundaries* and the same reason for them (baseline/tail
    are near-constant; there is no oscillation there for a rate estimate to
    find, genuine or spurious).

    Scales are built from a target frequency range (1/period for period in
    [_PERIOD_MIN_S, _PERIOD_MAX_S]) via the wavelet's central frequency —
    pywt has no frequency2scale, so this is the documented inverse of
    scale2frequency(wavelet, scale) = central_frequency(wavelet) / scale.

    Returns (t_active, freqs_hz, power, ridge_freq, anchors, fs):
    t_active/freqs_hz/power are the scalogram (time, frequency axis, |CWT|^2 —
    for rendering); ridge_freq is the per-instant dominant frequency in Hz
    (= instantaneous stroke rate in strokes/sec, the quantity 16-04-PLAN.md's
    hypothesis is about); anchors are the integer-phase-crossing boundaries
    in trough-cycle shape (via _anchors_from_marks, against unmasked vel) for
    overlay; fs lets the renderer convert rate to SPM for the stroke_rate_spm
    cross-check.
    """
    fs = m._compute_fs(t)
    dt = 1.0 / fs

    phases       = m.detect_phases(t, vel)
    baseline_end = phases["baseline_end"]
    swim_end     = phases["swim_end"]

    active        = _detrend(vel, fs)[baseline_end:swim_end]
    t_active      = t[baseline_end:swim_end]
    print(f"    active region {t_active[-1] - t_active[0]:.1f}s "
          f"({len(active)} samples) -- baseline [0:{baseline_end}], "
          f"tail [{swim_end}:{len(vel)}]")

    f_min, f_max  = 1.0 / _PERIOD_MAX_S, 1.0 / _PERIOD_MIN_S
    target_freqs  = np.geomspace(f_min, f_max, _N_SCALES)
    central_freq  = pywt.central_frequency(_WAVELET)
    scales        = central_freq / (target_freqs * dt)

    coeffs, freqs_hz = pywt.cwt(active, scales, _WAVELET, sampling_period=dt)
    power = np.abs(coeffs) ** 2

    ridge_idx  = _track_ridge(power, freqs_hz)
    ridge_freq = freqs_hz[ridge_idx]                        # Hz = instantaneous stroke rate
    print(f"    ridge frequency range [{ridge_freq.min():.2f}, {ridge_freq.max():.2f}] Hz "
          f"-> [{ridge_freq.min() * 60:.0f}, {ridge_freq.max() * 60:.0f}] SPM "
          f"(search range was [{f_min * 60:.0f}, {f_max * 60:.0f}] SPM)")

    # Phase = cumulative cycle count; a boundary falls at each integer crossing
    # (16-01-SUMMARY's Phi(t) = integral of rate(t') dt' mechanism sketch).
    phase = np.concatenate(([0.0], np.cumsum(ridge_freq[:-1] * np.diff(t_active))))
    marks = []
    n_target = 1
    for i in range(1, len(phase)):
        if phase[i - 1] < n_target <= phase[i]:
            marks.append(baseline_end + i)
            n_target += 1
    marks = np.array(marks, dtype=np.int64)
    print(f"    ridge-derived boundaries: {len(marks)} (vs. trough cycles below)")

    anchors = _anchors_from_marks(vel, marks)

    return t_active, freqs_hz, power, ridge_freq, anchors, fs


# ── subplot renderers ─────────────────────────────────────────────────────────

def _add_segmentation(fig, row, col, t, vel, trough_cycles, ridge_anchors,
                      baseline_end, swim_end, show_legend):
    """Velocity trace with BOTH segmentations' boundary lines overlaid (only
    two methods now, vs. shape-matching's three — legible on one axes), plus
    the masked-region shading."""
    v_max = float(np.nanmax(vel)) if len(vel) else 1.0

    if baseline_end > 0:
        fig.add_vrect(x0=t[0], x1=t[baseline_end], fillcolor="lightgray",
                      opacity=0.30, line_width=0, layer="below", row=row, col=col)
    if swim_end < len(t):
        fig.add_vrect(x0=t[swim_end], x1=t[-1], fillcolor="lightgray",
                      opacity=0.30, line_width=0, layer="below", row=row, col=col)

    for cycles, color, dash, label in (
        (trough_cycles, _C_TROUGH, "dash", "trough"),
        (ridge_anchors, _C_RIDGE,  "dot",  "ridge"),
    ):
        legend_shown = False
        for x_t in _boundary_times(t, cycles):
            fig.add_trace(go.Scatter(
                x=[x_t, x_t], y=[0, v_max * 1.08],
                mode="lines", line=dict(color=color, width=1.4, dash=dash),
                name=f"{label} anchor", legendgroup=label,
                showlegend=(show_legend and not legend_shown),
                hoverinfo="skip",
            ), row=row, col=col)
            legend_shown = True

    fig.add_trace(go.Scatter(
        x=t, y=vel,
        mode="lines", line=dict(color=_C_VEL, width=1.3),
        name="velocity", legendgroup="velocity",
        showlegend=(show_legend and row == 1),
    ), row=row, col=col)


def _add_scalogram(fig, row, col, t_active, freqs_hz, power, ridge_freq, show_legend):
    """Scalogram (frequency x time, color = wavelet power) with the extracted
    ridge overlaid — the structural analog of segment_motif_spike's
    motif-heatmap (length x time, color = conservation): both are 2-D views
    that may be tracking the same underlying quantity, instantaneous stroke
    period, via unrelated mechanisms (per 16-03-PLAN's framing)."""
    fig.add_trace(go.Heatmap(
        x=t_active, y=freqs_hz * 60.0, z=power,
        colorscale="Viridis", showscale=False,
        hovertemplate="t=%{x:.2f}s  rate=%{y:.0f} SPM  power=%{z:.3g}<extra></extra>",
    ), row=row, col=col)
    fig.add_trace(go.Scatter(
        x=t_active, y=ridge_freq * 60.0,
        mode="lines", line=dict(color=_C_RIDGE, width=1.6),
        name="ridge", legendgroup="ridge_line", showlegend=show_legend,
    ), row=row, col=col)


def _add_rate_curve(fig, row, col, t_active, ridge_freq, stroke_rate_spm, show_legend):
    """Ridge-implied instantaneous rate over time vs. the session's existing
    (single-number) stroke_rate_spm — the breaststroke cross-check 16-04-PLAN
    calls for: does the ridge's average track the trusted production number?"""
    fig.add_trace(go.Scatter(
        x=t_active, y=ridge_freq * 60.0,
        mode="lines", line=dict(color=_C_RATE, width=1.4),
        name="ridge rate (SPM)", legendgroup="rate", showlegend=show_legend,
    ), row=row, col=col)
    if np.isfinite(stroke_rate_spm):
        fig.add_trace(go.Scatter(
            x=[t_active[0], t_active[-1]], y=[stroke_rate_spm, stroke_rate_spm],
            mode="lines", line=dict(color=_C_SPM, width=1.4, dash="dash"),
            name="stroke_rate_spm (production)", legendgroup="spm", showlegend=show_legend,
        ), row=row, col=col)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Spike: wavelet/CWT stroke-rate ridge vs. trough segmentation. Opens in browser.",
    )
    parser.add_argument(
        "inputs", nargs="+",
        help="Processed CSV file(s) or a folder of CSVs",
    )
    args = parser.parse_args()

    paths = []
    for inp in args.inputs:
        p = Path(inp)
        if p.is_dir():
            paths.extend(sorted(p.glob("*.csv")))
        elif p.suffix == ".csv":
            paths.append(p)
        else:
            print(f"Skipping {inp} — not a CSV or directory", file=sys.stderr)

    if not paths:
        print("No CSV files found.", file=sys.stderr)
        sys.exit(1)

    n = len(paths)
    subplot_titles = (
        [p.stem for p in paths]
        + ["segmentation overlay"] * n
        + ["scalogram + ridge"] * n
        + ["instantaneous rate"] * n
    )
    fig = make_subplots(
        rows=3, cols=n,
        subplot_titles=subplot_titles,
        vertical_spacing=0.07,
        horizontal_spacing=0.03,
        shared_xaxes=True,
    )

    COL_W    = 480
    n_loaded = 0

    for col, path in enumerate(paths, start=1):
        show_legend = (col == 1)
        try:
            t, vel, dist, result = _load(path)
        except Exception as e:
            print(f"  Error loading {path.name}: {e}", file=sys.stderr)
            continue

        trough_cycles   = result["cycles"]
        stroke_rate_spm = result["session"]["stroke_rate_spm"]
        print(f"\n-- {path.stem} --  (trough cycles: {len(trough_cycles)}, "
              f"stroke_rate_spm: {stroke_rate_spm:.1f})")

        phases       = m.detect_phases(t, vel)
        baseline_end = phases["baseline_end"]
        swim_end     = phases["swim_end"]

        t_active, freqs_hz, power, ridge_freq, ridge_anchors, fs = find_ridge(t, vel)
        ridge_spm_mean = float(np.mean(ridge_freq) * 60.0)
        print(f"    ridge mean rate: {ridge_spm_mean:.1f} SPM  "
              f"(production stroke_rate_spm: {stroke_rate_spm:.1f}, "
              f"diff: {ridge_spm_mean - stroke_rate_spm:+.1f})")

        _add_segmentation(fig, row=1, col=col, t=t, vel=vel,
                          trough_cycles=trough_cycles, ridge_anchors=ridge_anchors,
                          baseline_end=baseline_end, swim_end=swim_end,
                          show_legend=show_legend)
        _add_scalogram(fig, row=2, col=col, t_active=t_active, freqs_hz=freqs_hz,
                       power=power, ridge_freq=ridge_freq, show_legend=show_legend)
        _add_rate_curve(fig, row=3, col=col, t_active=t_active, ridge_freq=ridge_freq,
                        stroke_rate_spm=stroke_rate_spm, show_legend=show_legend)
        n_loaded += 1

    if n_loaded == 0:
        print("No data to plot.", file=sys.stderr)
        sys.exit(1)

    fig.update_layout(
        title=dict(
            text=("Wavelet/CWT stroke-rate ridge vs. trough segmentation — "
                  "row 1: velocity with trough (grey, dashed) / ridge-derived "
                  "(red, dotted) boundary lines, shaded band = baseline/tail "
                  "masked out; row 2: CWT scalogram (color = power) with "
                  "extracted ridge (red line) overlaid, y-axis = instantaneous "
                  "stroke rate in SPM; row 3: ridge rate over time (red) vs. "
                  "production stroke_rate_spm (green dashed) — do they agree, "
                  "and does the ridge track drift smoothly rather than "
                  "fragmenting at regime-change / dive-pulldown points?"),
            font=dict(size=13),
        ),
        width=max(720, COL_W * n + 120),
        height=1320,
        template="plotly_white",
        legend=dict(orientation="h", y=-0.05, x=0.0, font=dict(size=10)),
        font=dict(size=10),
    )

    fig.update_yaxes(title_text="Velocity (m/s)", col=1, row=1)
    fig.update_yaxes(title_text="Rate (SPM)", col=1, row=2)
    fig.update_yaxes(title_text="Rate (SPM)", col=1, row=3)
    fig.update_xaxes(title_text="Time (s)", row=3)

    out = Path(tempfile.gettempdir()) / "wavelet_spike.html"
    fig.write_html(str(out))
    webbrowser.open(str(out))
    print(f"\nOpened -> {out}")


if __name__ == "__main__":
    main()
