"""
pipeline_view.py — Feature-extraction deep inspection for a single session.

Fetches a processed session from Supabase, runs every metrics.py extraction
step, and opens an annotated browser view showing:
  - Velocity trace with all extraction overlays
    (phase boundaries, troughs, cycle shading, arm/kick peaks)
  - ACF panel showing T_est estimation
  - Per-cycle metrics table

Usage
-----
    python pipeline_view.py              # list latest 20 sessions, pick one
    python pipeline_view.py --limit 50
"""

import argparse
import os
import sys
import tempfile
import webbrowser
from pathlib import Path

# Remove bare path entries so local supabase/ folder doesn't shadow supabase-py
sys.path = [p for p in sys.path if p not in ('', '.')]

import numpy as np
from dotenv import load_dotenv
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from supabase import create_client

load_dotenv()

SUPABASE_URL              = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

FS = 100.0

# Re-add project dir so we can import metrics
_here = str(Path(__file__).parent)
if _here not in sys.path:
    sys.path.insert(0, _here)

import metrics as m

# ── colours ──────────────────────────────────────────────────────────────────
_C_VEL    = "#185fa5"
_C_STEADY = "#4a90d9"
_C_RAMP   = "#f5a623"
_C_TROUGH = "#888888"
_C_ARM    = "#2ca02c"
_C_KICK   = "#d62728"
_C_ACF    = "#185fa5"
_C_TEST   = "#e67e22"


# ── Supabase helpers (mirrors fetch_sessions.py) ──────────────────────────────

def _get_client():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def _fetch_sessions(sb, limit):
    resp = (
        sb.table("sessions")
        .select("id, name, recorded_at, stroke_type, athlete_id, velocity_profile, distance_profile")
        .order("recorded_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = resp.data or []
    athlete_ids = list({r["athlete_id"] for r in rows if r.get("athlete_id")})
    athlete_names = {}
    if athlete_ids:
        try:
            ath = sb.table("athletes").select("id, name").in_("id", athlete_ids).execute()
            for a in (ath.data or []):
                athlete_names[a["id"]] = a.get("name", "")
        except Exception:
            pass
    for r in rows:
        aid = r.get("athlete_id") or ""
        r["_athlete_label"] = athlete_names.get(aid) or (aid[:8] if aid else "-")
    return rows


def _display_list(sessions):
    print(f"\n  {'#':<4} {'Date':<20} {'Athlete':<16} {'Stroke':<14} Name")
    print("  " + "-" * 70)
    for i, s in enumerate(sessions, 1):
        date    = (s.get("recorded_at") or "")[:19].replace("T", " ")
        athlete = s["_athlete_label"][:15]
        stroke  = (s.get("stroke_type") or "-")[:13]
        name    = s.get("name") or s["id"][:8]
        n_pts   = len(s.get("velocity_profile") or [])
        dur     = f"{n_pts / FS:.0f}s" if n_pts else "-"
        print(f"  {i:<4} {date:<20} {athlete:<16} {stroke:<14} {name}  ({dur})")
    print()


def _load_arrays(session):
    vel  = session.get("velocity_profile") or []
    dist = session.get("distance_profile") or []
    n    = len(vel)
    if n == 0:
        return None, None, None
    t    = np.arange(n) / FS
    vel  = np.array([float(v) if v is not None else float("nan") for v in vel])
    dist = np.array([float(d) if d is not None else float("nan") for d in dist])
    return t, vel, dist


# ── ACF computation ───────────────────────────────────────────────────────────

def _full_acf(t, vel):
    """Return (lags_s, acf_normalised) up to 6 s lag."""
    fs = float(1.0 / np.diff(t).mean())
    v  = np.nan_to_num(vel - np.nanmean(vel))
    acf = np.correlate(v, v, mode="full")
    acf = acf[len(acf) // 2:]
    if acf[0] == 0:
        return None, None
    acf    = acf / acf[0]
    max_lag = min(len(acf), int(6.0 * fs))
    lags_s = np.arange(max_lag) / fs
    return lags_s, acf[:max_lag]


# ── figure builder ────────────────────────────────────────────────────────────

def build_figure(session_label, t, vel, dist):
    result  = m.compute_session_metrics(t, vel, dist)
    session = result["session"]
    cycles  = result["cycles"]
    ip      = result["initial_phase"]

    phases   = m.detect_phases(t, vel)
    b_end    = phases["baseline_end"]
    swim_end = phases["swim_end"]
    ip_end   = ip["initial_phase_end_idx"]

    T_est       = m._estimate_period(t[b_end:swim_end], vel[b_end:swim_end])
    lags_s, acf = _full_acf(t[b_end:swim_end], vel[b_end:swim_end])

    v_max = float(np.nanmax(vel)) * 1.12

    fig = make_subplots(
        rows=3, cols=1,
        row_heights=[0.50, 0.18, 0.32],
        specs=[[{"type": "xy"}], [{"type": "xy"}], [{"type": "table"}]],
        subplot_titles=[
            "Velocity — feature extraction overlay",
            f"ACF — T_est = {T_est:.3f} s  ({60/T_est:.1f} SPM)" if T_est else "ACF",
            "Per-cycle metrics",
        ],
        vertical_spacing=0.07,
    )

    # ── row 1: velocity trace ─────────────────────────────────────────────────

    # Cycle shading (behind everything)
    for cyc in cycles:
        a   = cyc["start_idx"]
        b   = min(cyc["end_idx"], len(t) - 1)
        col = _C_STEADY if cyc.get("phase") == "steady" else _C_RAMP
        fig.add_trace(go.Scatter(
            x=[t[a], t[a], t[b], t[b], t[a]],
            y=[0,    v_max, v_max, 0,    0],
            fill="toself", fillcolor=col,
            mode="lines", line=dict(width=0),
            opacity=0.13, showlegend=False, hoverinfo="skip",
        ), row=1, col=1)

    # Phase boundary vertical lines (as scatter so they're scoped to row 1)
    boundaries = [
        (b_end,        "baseline_end", "#999999", "dash"),
        (ip_end,       "ip_end",       "#2ca02c", "dot"),
        (swim_end - 1, "swim_end",     "#d62728", "dash"),
    ]
    for idx, label, color, dash in boundaries:
        if 0 <= idx < len(t):
            fig.add_trace(go.Scatter(
                x=[t[idx], t[idx]], y=[0, v_max],
                mode="lines+text",
                line=dict(color=color, width=1.5, dash=dash),
                text=["", label], textposition="top center",
                textfont=dict(size=9, color=color),
                showlegend=False, hoverinfo="skip",
            ), row=1, col=1)

    # Trough markers at each cycle boundary
    trough_idx = [c["start_idx"] for c in cycles]
    fig.add_trace(go.Scatter(
        x=[t[i] for i in trough_idx],
        y=[vel[i] for i in trough_idx],
        mode="markers",
        marker=dict(symbol="circle-open", size=10, color=_C_TROUGH,
                    line=dict(width=2)),
        name="trough",
    ), row=1, col=1)

    # Velocity line
    fig.add_trace(go.Scatter(
        x=t, y=vel,
        mode="lines", line=dict(color=_C_VEL, width=1.6),
        name="velocity",
    ), row=1, col=1)

    # Arm-pull peaks
    fig.add_trace(go.Scatter(
        x=[t[c["arm_peak_idx"]] for c in cycles],
        y=[vel[c["arm_peak_idx"]] for c in cycles],
        mode="markers",
        marker=dict(symbol="triangle-up", size=13, color=_C_ARM,
                    line=dict(color="white", width=1)),
        name="arm-pull",
        customdata=[[c["arm_peak_vel"]] for c in cycles],
        hovertemplate="arm-pull  %{y:.3f} m/s<extra></extra>",
    ), row=1, col=1)

    # Kick peaks
    kick_c = [c for c in cycles if c.get("kick_peak_idx") is not None]
    if kick_c:
        fig.add_trace(go.Scatter(
            x=[t[c["kick_peak_idx"]] for c in kick_c],
            y=[vel[c["kick_peak_idx"]] for c in kick_c],
            mode="markers",
            marker=dict(symbol="triangle-down", size=13, color=_C_KICK,
                        line=dict(color="white", width=1)),
            name="kick",
            hovertemplate="kick  %{y:.3f} m/s<extra></extra>",
        ), row=1, col=1)

    # Cycle number annotations
    for i, cyc in enumerate(cycles):
        col = _C_STEADY if cyc.get("phase") == "steady" else _C_RAMP
        fig.add_annotation(
            x=t[cyc["arm_peak_idx"]],
            y=vel[cyc["arm_peak_idx"]],
            text=str(i), yshift=16, showarrow=False,
            font=dict(size=8, color=col),
            row=1, col=1,
        )

    # ── row 2: ACF ───────────────────────────────────────────────────────────
    if lags_s is not None:
        # Search window
        fig.add_trace(go.Scatter(
            x=[0.5, 0.5, 4.0, 4.0, 0.5],
            y=[-0.5, 1.05, 1.05, -0.5, -0.5],
            fill="toself", fillcolor="rgba(200,200,200,0.25)",
            mode="lines", line=dict(width=0),
            showlegend=False, hoverinfo="skip",
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=lags_s, y=acf,
            mode="lines", line=dict(color=_C_ACF, width=1.5),
            name="ACF", showlegend=False,
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=[0, lags_s[-1]], y=[0, 0],
            mode="lines", line=dict(color="#cccccc", width=0.8),
            showlegend=False, hoverinfo="skip",
        ), row=2, col=1)
        if T_est is not None:
            fig.add_trace(go.Scatter(
                x=[T_est, T_est], y=[-0.5, 1.05],
                mode="lines",
                line=dict(color=_C_TEST, width=2, dash="dash"),
                name=f"T_est={T_est:.2f}s", showlegend=False,
            ), row=2, col=1)

    # ── row 3: per-cycle table ────────────────────────────────────────────────
    def _f(v, fmt=".3f"):
        if v is None:
            return "-"
        try:
            return f"{v:{fmt}}" if not np.isnan(float(v)) else "-"
        except (TypeError, ValueError):
            return str(v)

    col_headers = ["#", "phase", "t_start(s)", "dur(s)",
                   "arm_vel(m/s)", "kick_vel(m/s)",
                   "dps(m)", "coast%", "impulse(m)"]
    col_data = [[] for _ in col_headers]
    row_colors = []

    for i, cyc in enumerate(cycles):
        col_data[0].append(str(i))
        col_data[1].append(cyc.get("phase", "-"))
        col_data[2].append(_f(t[cyc["start_idx"]], ".2f"))
        col_data[3].append(_f(cyc.get("duration_s"), ".2f"))
        col_data[4].append(_f(cyc.get("arm_peak_vel")))
        col_data[5].append(_f(cyc.get("kick_peak_vel")))
        col_data[6].append(_f(cyc.get("dist_m"), ".2f"))
        coast = cyc.get("coast_fraction")
        col_data[7].append(_f(coast * 100 if coast is not None else None, ".1f"))
        col_data[8].append(_f(cyc.get("impulse_m")))
        row_colors.append("#ddeeff" if cyc.get("phase") == "steady" else "#fff3e0")

    fig.add_trace(go.Table(
        header=dict(
            values=col_headers,
            fill_color="#eeeeee",
            font=dict(size=11, color="black"),
            align="center",
            height=28,
        ),
        cells=dict(
            values=col_data,
            fill_color=[row_colors] * len(col_headers),
            font=dict(size=10),
            align="center",
            height=24,
        ),
    ), row=3, col=1)

    # ── layout ────────────────────────────────────────────────────────────────
    name   = session_label
    sr     = session.get("stroke_rate_spm")
    n_ss   = session.get("stroke_count", 0)
    arm_v  = session.get("mean_arm_peak_vel_ms")
    title  = (
        f"{name}  |  {n_ss} steady cycles"
        + (f"  |  {sr:.1f} SPM" if sr else "")
        + (f"  |  arm-pull {arm_v:.2f} m/s" if arm_v else "")
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=12)),
        height=980,
        template="plotly_white",
        legend=dict(orientation="h", y=-0.01, x=0.0, font=dict(size=10)),
        font=dict(size=10),
    )
    fig.update_yaxes(title_text="Velocity (m/s)", row=1, col=1)
    fig.update_xaxes(title_text="Time (s)", row=1, col=1)
    fig.update_yaxes(title_text="ACF", row=2, col=1, range=[-0.6, 1.1])
    fig.update_xaxes(title_text="Lag (s)", row=2, col=1)

    return fig


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Feature-extraction pipeline inspector — single session, full detail."
    )
    parser.add_argument("--limit", type=int, default=20,
                        help="Max sessions to list (default: 20)")
    args = parser.parse_args()

    sb       = _get_client()
    sessions = _fetch_sessions(sb, args.limit)

    if not sessions:
        print("No sessions found.")
        sys.exit(0)

    _display_list(sessions)

    try:
        raw = input("Select one session: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        sys.exit(0)

    try:
        idx = int(raw) - 1
        assert 0 <= idx < len(sessions)
    except (ValueError, AssertionError):
        print("Invalid selection.")
        sys.exit(1)

    session = sessions[idx]
    t, vel, dist = _load_arrays(session)
    if t is None:
        print("Session has no signal data.")
        sys.exit(1)

    label = (session.get("name") or session["id"][:8])
    print(f"\nProcessing {label}...")

    fig = build_figure(label, t, vel, dist)

    out = Path(tempfile.gettempdir()) / "pipeline_view.html"
    fig.write_html(str(out))
    webbrowser.open(out.as_uri())
    print(f"Opened -> {out}")


if __name__ == "__main__":
    main()
