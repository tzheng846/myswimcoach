"""
inspect_cycles.py — Diagnostic plot for per-cycle velocity structure.
Opens as an HTML page in the browser via Plotly.

Usage
-----
    python inspect_cycles.py processed/session.csv
    python inspect_cycles.py processed/s1.csv processed/s2.csv
    python inspect_cycles.py processed/              # all CSVs in folder
    python inspect_cycles.py processed/ --cycles 3 9
"""

import argparse
import sys
import tempfile
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import metrics as m

# ── colours ───────────────────────────────────────────────────────────────────
_C_VEL    = "#185fa5"
_C_TROUGH = "#aaaaaa"
_C_ARM    = "#2ca02c"
_C_KICK   = "#d62728"
_C_MEAN   = "#333333"


# ── data ──────────────────────────────────────────────────────────────────────

def _load(csv_path):
    df     = pd.read_csv(csv_path)
    t      = df["time_s"].values
    vel    = df["vel_ms"].values
    dist   = df["dist_m"].values
    result = m.compute_session_metrics(t, vel, dist)
    return t, vel, dist, result


def _steady(result):
    return [c for c in result["cycles"] if c.get("phase") == "steady"]


# ── subplot renderers ─────────────────────────────────────────────────────────

def _add_timeseries(fig, row, col, t, vel, cycles, show_legend):
    """Velocity trace + trough boundaries + arm/kick peak markers."""
    if not cycles:
        return

    a_idx  = cycles[0]["start_idx"]
    b_idx  = min(cycles[-1]["end_idx"], len(t) - 1)
    mask   = (t >= t[a_idx]) & (t <= t[b_idx])
    v_max  = float(np.nanmax(vel[mask])) if mask.any() else 3.0

    # Trough boundary lines (scatter traces keep them scoped to this subplot)
    boundaries = [t[c["start_idx"]] for c in cycles] + [t[b_idx]]
    for x_t in boundaries:
        fig.add_trace(go.Scatter(
            x=[x_t, x_t], y=[0, v_max * 1.08],
            mode="lines",
            line=dict(color=_C_TROUGH, width=0.8, dash="dash"),
            showlegend=False, hoverinfo="skip",
        ), row=row, col=col)

    # Velocity trace
    fig.add_trace(go.Scatter(
        x=t[mask], y=vel[mask],
        mode="lines", line=dict(color=_C_VEL, width=1.5),
        name="velocity", legendgroup="velocity", showlegend=show_legend,
    ), row=row, col=col)

    # Arm-pull peaks
    fig.add_trace(go.Scatter(
        x=[t[c["arm_peak_idx"]] for c in cycles],
        y=[vel[c["arm_peak_idx"]] for c in cycles],
        mode="markers",
        marker=dict(symbol="triangle-up", size=11, color=_C_ARM,
                    line=dict(color="white", width=1)),
        name="arm pull", legendgroup="arm_pull", showlegend=show_legend,
    ), row=row, col=col)

    # Kick peaks (only cycles where kick was detected)
    kick_cycles = [c for c in cycles if c.get("kick_peak_idx") is not None]
    if kick_cycles:
        fig.add_trace(go.Scatter(
            x=[t[c["kick_peak_idx"]] for c in kick_cycles],
            y=[vel[c["kick_peak_idx"]] for c in kick_cycles],
            mode="markers",
            marker=dict(symbol="triangle-down", size=11, color=_C_KICK,
                        line=dict(color="white", width=1)),
            name="kick", legendgroup="kick", showlegend=show_legend,
        ), row=row, col=col)


def _add_epochs(fig, row, col, t, vel, cycles, show_legend):
    """Individual cycles aligned at trough start, overlaid, with mean."""
    if not cycles:
        return

    N_INTERP     = 300
    interp_segs  = []
    n_cyc        = len(cycles)
    legend_shown = False

    for i, cyc in enumerate(cycles):
        a     = cyc["start_idx"]
        b     = min(cyc["end_idx"], len(t) - 1)
        seg_t = t[a:b] - t[a]
        seg_v = vel[a:b]
        if len(seg_t) < 2:
            continue

        opacity = 0.15 + 0.55 * (i / max(1, n_cyc - 1))
        fig.add_trace(go.Scatter(
            x=seg_t, y=seg_v,
            mode="lines", line=dict(color=_C_VEL, width=1.0),
            opacity=opacity,
            name="cycles", legendgroup="cycles",
            showlegend=(show_legend and not legend_shown),
            hoverinfo="skip",
        ), row=row, col=col)
        legend_shown = True

        t_norm = np.linspace(0, 1, N_INTERP)
        interp_segs.append(np.interp(t_norm, seg_t / seg_t[-1], seg_v))

    if interp_segs:
        mean_v   = np.mean(interp_segs, axis=0)
        mean_dur = float(np.mean([
            t[min(c["end_idx"], len(t) - 1)] - t[c["start_idx"]] for c in cycles
        ]))
        fig.add_trace(go.Scatter(
            x=np.linspace(0, mean_dur, N_INTERP), y=mean_v,
            mode="lines", line=dict(color=_C_MEAN, width=2.5, dash="dash"),
            name=f"mean (n={len(interp_segs)})",
            legendgroup="mean", showlegend=show_legend,
        ), row=row, col=col)


# ── console summary ───────────────────────────────────────────────────────────

def _print_summary(name, steady, plot_cycles):
    n_kick    = sum(1 for c in plot_cycles if c.get("kick_peak_idx") is not None)
    arm_vels  = [c["arm_peak_vel"] for c in plot_cycles]
    kick_vels = [c["kick_peak_vel"] for c in plot_cycles if c.get("kick_peak_vel") is not None]
    print(f"\n-- {name} --")
    print(f"  Steady cycles   : {len(steady)}")
    print(f"  Plotted cycles  : {len(plot_cycles)}")
    print(f"  Kick detected   : {n_kick}/{len(plot_cycles)}")
    if arm_vels:
        print(f"  Arm-pull vel    : {np.mean(arm_vels):.3f} ± {np.std(arm_vels):.3f} m/s")
    if kick_vels:
        print(f"  Kick vel        : {np.mean(kick_vels):.3f} ± {np.std(kick_vels):.3f} m/s")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Inspect per-cycle velocity structure. Opens in browser.",
    )
    parser.add_argument(
        "inputs", nargs="+",
        help="Processed CSV file(s) or a folder of CSVs",
    )
    parser.add_argument(
        "--cycles", nargs=2, type=int, default=[2, 8],
        metavar=("START", "END"),
        help="0-indexed steady-state cycle range to plot (default: 2 8)",
    )
    args = parser.parse_args()
    cyc_start, cyc_end = args.cycles

    # Expand directories → sorted CSV list
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
    if n > 10:
        print(f"Note: rendering {n} sessions — figure will scroll horizontally in browser")

    # Build subplot grid
    subplot_titles = [p.stem for p in paths] + ["Cycles overlaid"] * n
    fig = make_subplots(
        rows=2, cols=n,
        subplot_titles=subplot_titles,
        vertical_spacing=0.14,
        horizontal_spacing=0.03,
    )

    COL_W    = 480   # px per column
    n_loaded = 0

    for col, path in enumerate(paths, start=1):
        show_legend = (col == 1)
        try:
            t, vel, dist, result = _load(path)
        except Exception as e:
            print(f"  Error loading {path.name}: {e}", file=sys.stderr)
            continue

        steady      = _steady(result)
        plot_cycles = steady[cyc_start:cyc_end]

        _print_summary(path.stem, steady, plot_cycles)
        _add_timeseries(fig, row=1, col=col, t=t, vel=vel,
                        cycles=plot_cycles, show_legend=show_legend)
        _add_epochs(fig, row=2, col=col, t=t, vel=vel,
                    cycles=plot_cycles, show_legend=show_legend)
        n_loaded += 1

    if n_loaded == 0:
        print("No data to plot.", file=sys.stderr)
        sys.exit(1)

    fig.update_layout(
        title=dict(
            text=(
                f"Per-cycle velocity inspection — arm-pull (▲)  kick (▼)"
                f"  |  steady cycles {cyc_start}–{cyc_end - 1}"
            ),
            font=dict(size=13),
        ),
        width=max(720, COL_W * n + 120),
        height=720,
        template="plotly_white",
        legend=dict(orientation="h", y=-0.06, x=0.0, font=dict(size=10)),
        font=dict(size=10),
    )

    fig.update_yaxes(title_text="Velocity (m/s)", col=1)
    fig.update_xaxes(title_text="Time (s)", row=1)
    fig.update_xaxes(title_text="Time from cycle start (s)", row=2)

    out = Path(tempfile.gettempdir()) / "inspect_cycles.html"
    fig.write_html(str(out))
    webbrowser.open(str(out))
    print(f"\nOpened -> {out}")


if __name__ == "__main__":
    main()
