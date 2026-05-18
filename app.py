"""
app.py — Streamlit swim coaching demo.

Run:
    streamlit run app.py
"""

import os
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from pathlib import Path
import anthropic

from metrics import compute_session_metrics
from coach import _build_system_prompt, _build_user_message, MODEL

# Read API key: .env for local dev, st.secrets for Streamlit Cloud
_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY")
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        if _line.strip().startswith("ANTHROPIC_API_KEY="):
            _API_KEY = _line.split("=", 1)[1].strip()
            break
if not _API_KEY:
    try:
        _API_KEY = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        pass

st.set_page_config(layout="centered", page_title="Swimnetics")

# ── Color palette ────────────────────────────────────────────────────────────
_C_STEADY  = "#4c9be8"   # used in per-cycle line charts
_C_OUTLIER = "#e87070"   # used in per-cycle line charts

# Stroke palette: cycles alternate through these colors
_STROKE_PALETTE = ["#4c85d4", "#e8784a", "#4cb87a", "#a06cd5", "#d4b84c", "#4cb8c8"]

# ── Metric rating ranges (breaststroke) ──────────────────────────────────────
_METRIC_RANGES = {
    "stroke_rate_spm": {
        "good":   lambda v: 45 <= v <= 65,
        "ok":     lambda v: 35 <= v <= 80,
        "ranges": "Good: 45–65 spm · OK: 35–80 spm · Needs work: outside that range",
    },
    "mean_vel_ms": {
        "good":   lambda v: v >= 1.2,
        "ok":     lambda v: v >= 0.8,
        "ranges": "Good: ≥ 1.2 m/s · OK: 0.8–1.2 m/s · Needs work: < 0.8 m/s",
    },
    "mean_dps_m": {
        "good":   lambda v: v >= 1.5,
        "ok":     lambda v: v >= 1.0,
        "ranges": "Good: ≥ 1.5 m · OK: 1.0–1.5 m · Needs work: < 1.0 m",
    },
    "mean_coast_fraction": {
        "good":   lambda v: 0.30 <= v <= 0.55,
        "ok":     lambda v: 0.20 <= v <= 0.65,
        "ranges": "Good: 30–55% · OK: 20–65% · Needs work: outside that range",
    },
    "fatigue_index_pct": {
        "good":   lambda v: v < 8,
        "ok":     lambda v: v < 20,
        "ranges": "Good: < 8% · OK: 8–20% · Needs work: > 20%",
    },
    "cv_arm_peak_vel": {
        "good":   lambda v: v < 0.10,
        "ok":     lambda v: v < 0.20,
        "ranges": "Good: < 0.10 · OK: 0.10–0.20 · Needs work: > 0.20",
    },
}


def _rate_metric(key: str, value) -> tuple:
    """Return (label, hex_color) rating for a metric value."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "", ""
    r = _METRIC_RANGES.get(key)
    if r is None:
        return "", ""
    if r["good"](value):
        return "Good", "#2d9e5f"
    if r["ok"](value):
        return "OK", "#d4860a"
    return "Needs work", "#c0392b"

SUGGESTED = [
    "What should I focus on next?",
    "Why did my technique change mid-set?",
    "How do I improve my pacing?",
    "What's holding back my speed?",
]

SUGGESTED_COMPARE = [
    "What improved between sessions?",
    "What got worse?",
    "Where should I focus next?",
    "Why did my speed change?",
]

_CSV_A = "processed/sample_br_1.csv"
_CSV_B = "processed/sample_br_2.csv"


def _abs_cycle_num(t_peak: float, full_boundaries: list) -> str:
    """Return 1-indexed absolute cycle number by matching peak time."""
    for i, (_, _, tp) in enumerate(full_boundaries):
        if not np.isnan(tp) and abs(tp - t_peak) < 0.15:
            return str(i + 1)
    return ""


# ── full-range cycle boundaries for slider sync ──────────────────────────────
def load_full_cycles(csv_path: str):
    """Compute cycle boundaries on the full recording (used for slider sync)."""
    df   = pd.read_csv(csv_path)
    t    = df["time_s"].values
    vel  = df["vel_ms"].values
    dist = df["dist_m"].values - df["dist_m"].values[0]
    result = compute_session_metrics(t, vel, dist)
    boundaries = []
    for c in result["cycles"]:
        idx  = c.get("peak_idx")
        t_pk = float(t[idx]) if idx is not None and idx < len(t) else float("nan")
        si   = c.get("start_idx")
        ei   = c.get("end_idx")
        t_s  = float(t[si]) if si is not None else float("nan")
        t_e  = float(t[ei - 1]) if ei else float("nan")
        boundaries.append((t_s, t_e, t_pk))
    return float(t[0]), float(t[-1]), boundaries


# ── trimmed data + metrics ────────────────────────────────────────────────────
def load_and_compute(csv_path: str, t_start: float, t_end: float):
    df         = pd.read_csv(csv_path)
    t_full     = df["time_s"].values
    vel_full   = df["vel_ms"].values
    dist_full  = df["dist_m"].values
    accel_full = df["accel_ms2"].values

    mask = (t_full >= t_start) & (t_full <= t_end)
    t    = t_full[mask]
    vel  = vel_full[mask]
    dist = dist_full[mask] - dist_full[mask][0]
    accel = accel_full[mask]

    result = compute_session_metrics(t, vel, dist)
    for c in result["cycles"]:
        idx = c.get("peak_idx")
        si  = c.get("start_idx")
        ei  = c.get("end_idx")
        c["t_peak_s"]  = float(t[idx]) if idx is not None and idx < len(t) else float("nan")
        c["t_start_s"] = float(t[si])  if si  is not None and si  < len(t) else float("nan")
        c["t_end_s"]   = float(t[min(ei - 1, len(t) - 1)]) if ei is not None and ei > 0 else float("nan")

    return t_full, vel_full, accel_full, t, vel, accel, result


# ── Velocity (+ optional acceleration) chart ─────────────────────────────────
def _build_vel_chart(t_full, vel_full, accel_full, t_start, t_end, cycles,
                     full_boundaries, show_accel=True):
    if show_accel:
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.65, 0.35],
            vertical_spacing=0.06,
        )
    else:
        fig = go.Figure()

    vel_kw = dict(row=1, col=1) if show_accel else {}

    # Raw velocity trace
    fig.add_trace(go.Scatter(
        x=t_full, y=vel_full,
        mode="lines", line=dict(color="#aaaaaa", width=0.9),
        showlegend=False,
        hoverinfo="skip",
    ), **vel_kw)

    # Zero line
    if show_accel:
        fig.add_hline(y=0, line=dict(color="rgba(150,150,150,0.6)", width=0.8, dash="dash"), row=1, col=1)
    else:
        fig.add_hline(y=0, line=dict(color="rgba(150,150,150,0.6)", width=0.8, dash="dash"))

    # Shaded stroke regions + arm-pull peak markers
    if cycles:
        med_dur = np.median([c["duration_s"] for c in cycles])

        # Shaded region per stroke
        for i, c in enumerate(cycles):
            t_s = c.get("t_start_s", float("nan"))
            t_e = c.get("t_end_s",   float("nan"))
            if np.isnan(t_s) or np.isnan(t_e) or t_e <= t_s:
                continue
            color = _STROKE_PALETTE[i % len(_STROKE_PALETTE)]
            vrect_kw = dict(x0=t_s, x1=t_e, fillcolor=color, opacity=0.18,
                            layer="below", line_width=0)
            if show_accel:
                for row in (1, 2):
                    fig.add_vrect(**vrect_kw, row=row, col=1)
            else:
                fig.add_vrect(**vrect_kw)

        # One invisible hover point per stroke at the region midpoint.
        # hovermode="x" (set below) matches by x-distance only, so the hover
        # boundary aligns exactly with the visual vrect boundary regardless of y.
        hx, hy, hcd = [], [], []
        for i, c in enumerate(cycles):
            t_s  = c.get("t_start_s", float("nan"))
            t_e  = c.get("t_end_s",   float("nan"))
            t_pk = c.get("t_peak_s",  float("nan"))
            v_pk = c.get("arm_peak_vel", float("nan"))
            if any(np.isnan(v) for v in [t_s, t_e, v_pk]):
                continue
            num = _abs_cycle_num(t_pk, full_boundaries) or str(i + 1)
            hx.append((t_s + t_e) / 2)
            hy.append(v_pk)
            hcd.append([num])

        if hx:
            fig.add_trace(go.Scatter(
                x=hx, y=hy,
                mode="markers",
                marker=dict(size=1, opacity=0),
                customdata=hcd,
                hovertemplate="<b>Stroke %{customdata[0]}</b><extra></extra>",
                showlegend=False,
            ), **vel_kw)

    if show_accel:
        fig.add_trace(go.Scatter(
            x=t_full, y=accel_full,
            mode="lines", line=dict(color="#f97316", width=0.9),
            showlegend=False,
            hoverinfo="skip",
        ), row=2, col=1)
        fig.update_yaxes(title_text="vel (m/s)", row=1, col=1)
        fig.update_yaxes(title_text="accel (m/s²)", row=2, col=1)
        fig.update_xaxes(title_text="time (s)", row=2, col=1)
        fig.update_layout(height=420, margin=dict(l=60, r=20, t=30, b=40),
                          hovermode="x")
    else:
        fig.update_yaxes(title_text="Speed (m/s)")
        fig.update_xaxes(title_text="Time (s)")
        fig.update_layout(height=280, margin=dict(l=60, r=20, t=30, b=40),
                          hovermode="x")

    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.2)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.2)")
    return fig


# ── Stats metric cards ────────────────────────────────────────────────────────
def _build_stats_table(session: dict, simple: bool = False):
    # (label, session_key, format_fn, explanation)
    all_stats = [
        ("Stroke Rate", "stroke_rate_spm",
         lambda v: f"{v:.1f} spm",
         "Strokes per minute. High = fast tempo, less time per stroke. "
         "Low = slower, more deliberate. Elite breaststroke: 45–60 spm."),

        ("Average Speed", "mean_vel_ms",
         lambda v: f"{v:.2f} m/s",
         "Mean forward speed. Higher is always faster. "
         "Recreational: 0.8–1.1 m/s. Competitive: > 1.3 m/s."),

        ("Dist per Stroke", "mean_dps_m",
         lambda v: f"{v:.2f} m",
         "Meters traveled per stroke. Higher = more efficient — each pull takes you further. "
         "Low DPS means effort that isn't converting to distance."),

        ("Glide Time", "mean_coast_fraction",
         lambda v: f"{v * 100:.0f}%",
         "Fraction of each stroke spent gliding after the kick. "
         "Too low = choppy, not using momentum. Too high = dead time, losing speed."),

        ("Fatigue Index", "fatigue_index_pct",
         lambda v: f"{v:.1f}%",
         "Drop in arm power from first quarter to last quarter of the set. "
         "Negative = still building. Near zero = well-paced. High positive = fatiguing fast."),

        ("Stroke Consistency", "cv_arm_peak_vel",
         lambda v: f"{v:.3f}",
         "Coefficient of variation in arm-pull peak velocity. "
         "Lower = more repeatable technique stroke to stroke."),
    ]
    stats = all_stats[:3] if simple else all_stats
    cols = st.columns(3)
    for i, (label, key, fmt, explanation) in enumerate(stats):
        raw = session.get(key)
        formatted = fmt(raw) if raw is not None else "—"
        ranges_text = _METRIC_RANGES.get(key, {}).get("ranges", "")
        tip = explanation + (f"\n\n{ranges_text}" if ranges_text else "")
        rating_label, rating_color = _rate_metric(key, raw)
        with cols[i % 3]:
            st.metric(label=label, value=formatted, help=tip)
            if rating_label:
                st.markdown(
                    f"<span style='color:{rating_color};font-size:0.82em'>"
                    f"● {rating_label}</span>",
                    unsafe_allow_html=True,
                )


# ── Per-cycle line chart ──────────────────────────────────────────────────────
def _build_line_chart(labels, values, is_outlier_flags, title, y_label):
    non_out_vals = [v for v, o in zip(values, is_outlier_flags) if not o]
    mean_val     = float(np.mean(non_out_vals)) if non_out_vals else None
    point_colors = [_C_OUTLIER if o else _C_STEADY for o in is_outlier_flags]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=values,
        mode="lines+markers",
        line=dict(color="#cccccc", width=1.5),
        marker=dict(size=8, color=point_colors, line=dict(color="white", width=1)),
        hovertemplate="%{x}: %{y:.3f}<extra></extra>",
        showlegend=False,
    ))
    if mean_val is not None:
        fig.add_hline(y=mean_val, line=dict(color="#888888", width=1.2, dash="dash"))

    fig.update_layout(title=dict(text=title, font=dict(size=13)),
                      yaxis_title=y_label, height=260,
                      margin=dict(l=50, r=10, t=40, b=50))
    fig.update_xaxes(showgrid=False, tickangle=-45)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.2)")
    return fig


# ── Question-card system ──────────────────────────────────────────────────────

def _compute_q1_q4(cycles):
    """First- and last-quarter mean arm-peak velocity from steady cycles."""
    ss = [c for c in cycles if c.get("phase") == "steady"]
    if len(ss) < 2:
        return None, None
    q = max(1, len(ss) // 4)
    return (float(np.mean([c["arm_peak_vel"] for c in ss[:q]])),
            float(np.mean([c["arm_peak_vel"] for c in ss[-q:]])))


def _compute_verdicts(session: dict, cycles: list) -> dict:
    fi       = session.get("fatigue_index_pct")
    cv_isi   = session.get("cv_isi")    # keep None distinct from 0
    pct_kick = session.get("pct_cycles_with_kick")

    if fi is None:
        tech = {"verdict": "unknown", "icon": "—", "label": "Not enough data", "text": ""}
    elif fi < -10:
        tech = {"verdict": "building", "icon": "📈", "label": "Building",
                "text": "Stroke power built through the set — still warming up."}
    elif fi < 8:
        tech = {"verdict": "held", "icon": "✅", "label": "Held",
                "text": "Stroke power stayed consistent throughout."}
    elif fi < 20:
        tech = {"verdict": "partial", "icon": "⚠️", "label": "Minor fade",
                "text": f"Stroke power dropped {fi:.0f}% from first to last quarter."}
    else:
        tech = {"verdict": "broke_down", "icon": "🔴", "label": "Broke down",
                "text": f"Significant fatigue — stroke power fell {fi:.0f}% by the end."}
    if fi is not None:
        tech["fi"] = fi

    if cv_isi is None:
        pacing = {"state": "no_data", "cv_isi": None}
    elif cv_isi > 0.20:
        pacing = {"state": "variable", "cv_isi": cv_isi}
    else:
        pacing = {"state": "consistent", "cv_isi": cv_isi}

    if pct_kick is None:
        kick = {"state": "no_data", "pct_kick": None, "ratio": None}
    elif pct_kick > 30:
        kick = {"state": "yes", "pct_kick": pct_kick,
                "ratio": session.get("mean_arm_kick_ratio")}
    else:
        kick = {"state": "not_detected", "pct_kick": pct_kick, "ratio": None}

    return {"technique": tech, "pacing": pacing, "kick": kick}


def _render_speed_card(session: dict, q1, q4):
    mean_vel = session.get("mean_vel_ms") or 0
    with st.container(border=True):
        st.markdown("**How fast was that?**")
        if mean_vel > 0:
            pace_s = 100 / mean_vel
            st.markdown(f"### {int(pace_s // 60)}:{int(pace_s % 60):02d} / 100m")
        else:
            st.markdown("### —")
        if q1 is not None and q4 is not None:
            arrow = "↗" if q4 > q1 * 1.02 else "↘" if q4 < q1 * 0.98 else "→"
            st.caption(f"Stroke power: {q1:.2f} {arrow} {q4:.2f} m/s (first → last quarter)")


def _render_technique_card(session: dict, v: dict):
    with st.container(border=True):
        st.markdown("**Did technique hold up?**")
        st.markdown(f"{v['icon']} **{v['label']}**")
        if v["text"]:
            st.caption(v["text"])
        with st.expander("Details"):
            fi = v.get("fi")
            cv_isi = session.get("cv_isi")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Fatigue Index", f"{fi:.1f}%" if fi is not None else "—")
            with c2:
                st.metric("Stroke Timing CV", f"{cv_isi:.3f}" if cv_isi is not None else "—")


def _render_pacing_card(v: dict):
    with st.container(border=True):
        st.markdown("**Were you pacing consistently?**")
        if v["state"] == "no_data":
            st.markdown("— **Not enough strokes**")
            st.caption("Widen the analysis window to see pacing consistency.")
        elif v["state"] == "variable":
            st.markdown("⚠️ **Variable**")
            st.caption("Stroke timing varied — some strokes were notably longer or shorter than average.")
            with st.expander("Details"):
                st.metric("Stroke Timing CV", f"{v['cv_isi']:.3f}")
                st.caption("Below 0.10 = very consistent · 0.20+ = high variation")
        else:
            st.markdown("✅ **Consistent**")
            st.caption("Stroke timing was steady throughout the window.")
            with st.expander("Details"):
                st.metric("Stroke Timing CV", f"{v['cv_isi']:.3f}")
                st.caption("Below 0.10 = very consistent · 0.20+ = high variation")


def _render_kick_card(v: dict):
    with st.container(border=True):
        st.markdown("**Is your kick contributing?**")
        if v["state"] == "no_data":
            st.markdown("— **Not enough data**")
            st.caption("Widen the analysis window to detect kick contribution.")
        elif v["state"] == "yes":
            st.markdown("✅ **Yes**")
            st.caption(f"Kick detected in {v['pct_kick']:.0f}% of strokes.")
            with st.expander("Details"):
                st.metric("Kick Presence", f"{v['pct_kick']:.0f}%")
                if v["ratio"] is not None:
                    st.metric("Kick / Arm Ratio", f"{v['ratio']:.2f}")
        else:
            st.markdown("— **Not detected**")
            st.caption("No distinct kick peak found. May be filtered at the current LP cutoff.")


def _render_question_cards(session: dict, cycles: list):
    verdicts = _compute_verdicts(session, cycles)
    q1, q4   = _compute_q1_q4(cycles)

    col1, col2 = st.columns(2)
    with col1:
        _render_speed_card(session, q1, q4)
    with col2:
        _render_technique_card(session, verdicts["technique"])

    col3, col4 = st.columns(2)
    with col3:
        _render_pacing_card(verdicts["pacing"])
    with col4:
        _render_kick_card(verdicts["kick"])


# ── Chat helpers ──────────────────────────────────────────────────────────────
def _build_chat_system(session: dict, cycles: list, simple: bool = False) -> str:
    metrics_block = _build_user_message("breaststroke", session, cycles)
    if simple:
        system = """\
You are a friendly swim coach giving feedback to a swimmer who doesn't know technical terms.
Use plain, encouraging language. Focus on 1-2 concrete things they can work on next.
Avoid jargon: say 'stroke rate' not 'SPM', 'how far each stroke takes you' not 'DPS',
'glide' not 'coast fraction', 'arm power' not 'arm-peak velocity or CV'.
Keep your answer short — 3 to 5 sentences maximum.
"""
    else:
        system = _build_system_prompt("breaststroke")
    return system + "\n\nSESSION DATA:\n" + metrics_block


def _build_compare_metrics(session_a: dict, session_b: dict, newer_is_b: bool):
    baseline = session_a if newer_is_b else session_b
    newer    = session_b if newer_is_b else session_a
    base_label  = "sample_br_1 (baseline)" if newer_is_b else "sample_br_2 (baseline)"
    newer_label = "sample_br_2 (newer)"    if newer_is_b else "sample_br_1 (newer)"

    st.caption(f"Baseline: {base_label} → Newer: {newer_label}. Delta = % change from baseline.")

    specs = [
        ("Stroke Rate",        "stroke_rate_spm",    lambda v: f"{v:.1f} spm", "off"),
        ("Average Speed",      "mean_vel_ms",         lambda v: f"{v:.2f} m/s", "normal"),
        ("Dist per Stroke",    "mean_dps_m",          lambda v: f"{v:.2f} m",   "normal"),
        ("Glide Time",         "mean_coast_fraction", lambda v: f"{v*100:.0f}%","off"),
        ("Fatigue Index",      "fatigue_index_pct",   lambda v: f"{v:.1f}%",    "inverse"),
        ("Stroke Consistency", "cv_arm_peak_vel",     lambda v: f"{v:.3f}",     "inverse"),
    ]
    cols = st.columns(3)
    for i, (label, key, fmt, delta_color) in enumerate(specs):
        b_val = baseline.get(key) or 0
        n_val = newer.get(key) or 0
        pct   = ((n_val - b_val) / abs(b_val) * 100) if b_val != 0 else 0.0
        with cols[i % 3]:
            st.metric(label=label, value=fmt(n_val),
                      delta=f"{pct:+.1f}%", delta_color=delta_color)


def _build_compare_chat_system(session_a, cycles_a, session_b, cycles_b,
                                newer_is_b: bool, simple: bool = False) -> str:
    if newer_is_b:
        base_session, base_cycles, base_name    = session_a, cycles_a, "sample_br_1"
        newer_session, newer_cycles, newer_name = session_b, cycles_b, "sample_br_2"
    else:
        base_session, base_cycles, base_name    = session_b, cycles_b, "sample_br_2"
        newer_session, newer_cycles, newer_name = session_a, cycles_a, "sample_br_1"

    block_base  = _build_user_message("breaststroke", base_session,  base_cycles)
    block_newer = _build_user_message("breaststroke", newer_session, newer_cycles)

    if simple:
        system = """\
You are a friendly swim coach comparing two breaststroke sessions for a swimmer who doesn't know technical terms.
Use plain, encouraging language. Focus on 1-2 concrete differences and whether they improved.
Avoid jargon. Keep your answer to 3-5 sentences.
"""
    else:
        system = _build_system_prompt("breaststroke")

    return (
        system
        + f"\n\nBASELINE SESSION ({base_name}):\n" + block_base
        + f"\n\nNEWER SESSION ({newer_name}):\n"   + block_newer
    )


def _coaching_stream_multi(system_prompt: str, messages: list):
    client = anthropic.Anthropic(api_key=_API_KEY)
    with client.messages.stream(
        model=MODEL,
        max_tokens=2048,
        system=[{"type": "text", "text": system_prompt,
                 "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text


# ── Main app ──────────────────────────────────────────────────────────────────
def main():
    st.sidebar.title("Swimnetics")
    compare_mode = st.sidebar.checkbox("Compare sessions", key="compare_mode")

    # ── Mode toggle (shared across both modes) ────────────────────────────────
    mode   = st.radio("View", ["Simple", "Advanced"], horizontal=True,
                      key="mode", label_visibility="collapsed")
    simple = (mode == "Simple")

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPARE MODE
    # ═══════════════════════════════════════════════════════════════════════════
    if compare_mode:
        newer_key  = st.sidebar.radio("Which is newer?", ["sample_br_1", "sample_br_2"],
                                      key="newer_session")
        newer_is_b = (newer_key == "sample_br_2")

        # Init state once per compare session
        if not st.session_state.get("compare_initialized"):
            for suffix, csv in (("_a", _CSV_A), ("_b", _CSV_B)):
                t_min, t_max, boundaries = load_full_cycles(csv)
                n = len(boundaries)
                t_min_s = float(np.floor(t_min * 10) / 10)
                t_max_s = float(np.ceil(t_max * 10) / 10)
                st.session_state[f"t_min{suffix}"]            = t_min_s
                st.session_state[f"t_max{suffix}"]            = t_max_s
                st.session_state[f"n_cycles{suffix}"]         = n
                st.session_state[f"cycle_boundaries{suffix}"] = boundaries
                st.session_state[f"time_range{suffix}"]       = (t_min_s, t_max_s)
                st.session_state[f"cycle_range{suffix}"]      = (1, max(n, 1))
            st.session_state.messages_compare   = []
            st.session_state.compare_initialized = True

        # Sync callbacks — session A
        def _on_time_change_a():
            t_s, t_e = st.session_state.time_range_a
            bounds   = st.session_state.cycle_boundaries_a
            visible  = [i + 1 for i, (_, _, tp) in enumerate(bounds)
                        if not np.isnan(tp) and t_s <= tp <= t_e]
            if visible:
                st.session_state.cycle_range_a = (min(visible), max(visible))

        def _on_cycle_change_a():
            c_s, c_e = st.session_state.cycle_range_a
            bounds   = st.session_state.cycle_boundaries_a
            t_s = bounds[c_s - 1][0]; t_e = bounds[c_e - 1][1]
            if not (np.isnan(t_s) or np.isnan(t_e)):
                st.session_state.time_range_a = (round(t_s, 1), round(t_e, 1))

        # Sync callbacks — session B
        def _on_time_change_b():
            t_s, t_e = st.session_state.time_range_b
            bounds   = st.session_state.cycle_boundaries_b
            visible  = [i + 1 for i, (_, _, tp) in enumerate(bounds)
                        if not np.isnan(tp) and t_s <= tp <= t_e]
            if visible:
                st.session_state.cycle_range_b = (min(visible), max(visible))

        def _on_cycle_change_b():
            c_s, c_e = st.session_state.cycle_range_b
            bounds   = st.session_state.cycle_boundaries_b
            t_s = bounds[c_s - 1][0]; t_e = bounds[c_e - 1][1]
            if not (np.isnan(t_s) or np.isnan(t_e)):
                st.session_state.time_range_b = (round(t_s, 1), round(t_e, 1))

        st.title("Session Comparison")

        with st.expander("Session A window (sample_br_1)", expanded=False):
            st.slider("Analysis window (s)",
                min_value=st.session_state.t_min_a,
                max_value=st.session_state.t_max_a, step=0.1,
                key="time_range_a", on_change=_on_time_change_a)
            st.slider("Stroke range",
                min_value=1, max_value=max(st.session_state.n_cycles_a, 1), step=1,
                key="cycle_range_a", on_change=_on_cycle_change_a)

        with st.expander("Session B window (sample_br_2)", expanded=False):
            st.slider("Analysis window (s)",
                min_value=st.session_state.t_min_b,
                max_value=st.session_state.t_max_b, step=0.1,
                key="time_range_b", on_change=_on_time_change_b)
            st.slider("Stroke range",
                min_value=1, max_value=max(st.session_state.n_cycles_b, 1), step=1,
                key="cycle_range_b", on_change=_on_cycle_change_b)

        t_start_a, t_end_a = st.session_state.time_range_a
        t_start_b, t_end_b = st.session_state.time_range_b

        t_full_a, vel_full_a, accel_full_a, _, _, _, result_a = load_and_compute(
            _CSV_A, t_start_a, t_end_a)
        t_full_b, vel_full_b, accel_full_b, _, _, _, result_b = load_and_compute(
            _CSV_B, t_start_b, t_end_b)

        cycles_a  = result_a["cycles"];  session_a = result_a["session"]
        cycles_b  = result_b["cycles"];  session_b = result_b["session"]
        bounds_a  = st.session_state.cycle_boundaries_a
        bounds_b  = st.session_state.cycle_boundaries_b

        for c in cycles_a:
            c["abs_num"] = _abs_cycle_num(c.get("t_peak_s", float("nan")), bounds_a) or None
        for c in cycles_b:
            c["abs_num"] = _abs_cycle_num(c.get("t_peak_s", float("nan")), bounds_b) or None

        st.markdown("**Session A — sample_br_1**")
        st.plotly_chart(
            _build_vel_chart(t_full_a, vel_full_a, accel_full_a, t_start_a, t_end_a,
                             cycles_a, bounds_a, show_accel=False),
            use_container_width=True)
        st.caption("Click and drag to zoom. Double-click to reset.")

        st.markdown("**Session B — sample_br_2**")
        st.plotly_chart(
            _build_vel_chart(t_full_b, vel_full_b, accel_full_b, t_start_b, t_end_b,
                             cycles_b, bounds_b, show_accel=False),
            use_container_width=True)
        st.caption("Click and drag to zoom. Double-click to reset.")

        st.divider()
        _build_compare_metrics(session_a, session_b, newer_is_b)
        st.divider()

        st.subheader("Coach Chat")
        msgs       = st.session_state.messages_compare
        used_turns = sum(1 for m in msgs if m["role"] == "user")
        remaining  = 5 - used_turns
        if remaining <= 0:
            st.error("Question limit reached (0 / 5 remaining).")
        elif remaining == 1:
            st.warning("Last question! (1 / 5 remaining)")
        else:
            st.info(f"Questions remaining: {remaining} / 5")

        chip_cols = st.columns(len(SUGGESTED_COMPARE))
        for col, q in zip(chip_cols, SUGGESTED_COMPARE):
            with col:
                if st.button(q, use_container_width=True, disabled=remaining <= 0,
                             key=f"cmp_{q[:8]}"):
                    st.session_state.pending_compare_q = q

        for msg in msgs:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = None if remaining <= 0 else st.chat_input("Ask about both sessions...")
        if not user_input and "pending_compare_q" in st.session_state:
            user_input = st.session_state.pop("pending_compare_q")

        if user_input:
            msgs.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
            sys_prompt = _build_compare_chat_system(
                session_a, cycles_a, session_b, cycles_b, newer_is_b, simple)
            with st.chat_message("assistant"):
                response = st.write_stream(_coaching_stream_multi(sys_prompt, msgs))
            msgs.append({"role": "assistant", "content": response})

    # ═══════════════════════════════════════════════════════════════════════════
    # SINGLE-SESSION MODE
    # ═══════════════════════════════════════════════════════════════════════════
    else:
        st.session_state.compare_initialized = False

        processed_dir = Path("processed")
        csv_files = sorted(processed_dir.glob("*.csv"))
        if not csv_files:
            st.error("No CSV files found in processed/")
            return

        selected = st.sidebar.selectbox(
            "Session", csv_files, format_func=lambda p: p.stem
        )

        file_changed = st.session_state.get("current_file") != str(selected)
        slider_gone  = "time_range" not in st.session_state
        if file_changed or slider_gone:
            t_min, t_max, boundaries = load_full_cycles(str(selected))
            n = len(boundaries)
            t_min_s = float(np.floor(t_min * 10) / 10)
            t_max_s = float(np.ceil(t_max * 10) / 10)
            st.session_state.update({
                "current_file":     str(selected),
                "cycle_boundaries": boundaries,
                "t_min": t_min_s, "t_max": t_max_s, "n_cycles": n,
                "time_range":  (t_min_s, t_max_s),
                "cycle_range": (1, max(n, 1)),
            })
            if file_changed:
                st.session_state.messages = []

        t_min    = st.session_state.t_min
        t_max    = st.session_state.t_max
        n_cycles = st.session_state.n_cycles

        def _on_time_change():
            t_s, t_e = st.session_state.time_range
            bounds   = st.session_state.cycle_boundaries
            visible  = [i + 1 for i, (_, _, tp) in enumerate(bounds)
                        if not np.isnan(tp) and t_s <= tp <= t_e]
            if visible:
                st.session_state.cycle_range = (min(visible), max(visible))

        def _on_cycle_change():
            c_s, c_e = st.session_state.cycle_range
            bounds   = st.session_state.cycle_boundaries
            t_s = bounds[c_s - 1][0]; t_e = bounds[c_e - 1][1]
            if not (np.isnan(t_s) or np.isnan(t_e)):
                st.session_state.time_range = (round(t_s, 1), round(t_e, 1))

        t_start, t_end = st.session_state.time_range

        t_full, vel_full, accel_full, t, vel, accel, result = load_and_compute(
            str(selected), t_start, t_end)
        cycles  = result["cycles"]
        session = result["session"]
        st.session_state["_debug_freq"] = {
            "stroke_rate_spm": session.get("stroke_rate_spm", 0),
            "n_cycles":        len(cycles),
        }
        full_boundaries = st.session_state.cycle_boundaries

        for c in cycles:
            c["abs_num"] = _abs_cycle_num(c.get("t_peak_s", float("nan")),
                                          full_boundaries) or None

        st.title(f"Session: {selected.stem}")
        if dbg := st.session_state.get("_debug_freq"):
            st.caption(f"DEBUG — SPM: {dbg['stroke_rate_spm']:.1f}  |  "
                       f"strokes detected: {dbg['n_cycles']}")

        with st.expander("Adjust analysis window", expanded=False):
            if simple:
                st.caption(
                    "Try: narrow to 11–19 s to focus on top-end speeds. Watch the metrics change."
                )
            st.slider("Analysis window (s)",
                min_value=t_min, max_value=t_max, step=0.1,
                key="time_range", on_change=_on_time_change)
            st.slider("Stroke range",
                min_value=1, max_value=max(n_cycles, 1), step=1,
                key="cycle_range", on_change=_on_cycle_change)

        st.plotly_chart(
            _build_vel_chart(t_full, vel_full, accel_full, t_start, t_end,
                             cycles, full_boundaries,
                             show_accel=not simple),
            use_container_width=True)
        st.caption("Click and drag on the chart to zoom in. Double-click to reset.")

        _render_question_cards(session, cycles)
        if not simple:
            _build_stats_table(session, simple=False)

        st.divider()
        st.subheader("Coach Chat")

        used_turns = sum(1 for m in st.session_state.messages if m["role"] == "user")
        remaining  = 5 - used_turns
        if remaining <= 0:
            st.error("Question limit reached (0 / 5 remaining). Load a new file to reset.")
        elif remaining == 1:
            st.warning("Last question! (1 / 5 remaining)")
        else:
            st.info(f"Questions remaining: {remaining} / 5")

        chip_cols = st.columns(len(SUGGESTED))
        for col, q in zip(chip_cols, SUGGESTED):
            with col:
                if st.button(q, use_container_width=True, disabled=remaining <= 0):
                    st.session_state.pending_question = q

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = None if remaining <= 0 else st.chat_input("Ask your coach...")
        if not user_input and "pending_question" in st.session_state:
            user_input = st.session_state.pop("pending_question")

        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
            system_prompt = _build_chat_system(session, cycles, simple=simple)
            with st.chat_message("assistant"):
                response = st.write_stream(
                    _coaching_stream_multi(system_prompt, st.session_state.messages))
            st.session_state.messages.append({"role": "assistant", "content": response})

        if not simple:
            st.divider()
            interior = cycles[1:-1] if len(cycles) > 2 else cycles
            if interior:
                med_dur     = np.median([c["duration_s"] for c in cycles])
                labels      = [_abs_cycle_num(c.get("t_peak_s", float("nan")),
                               full_boundaries) or str(i + 1)
                               for i, c in enumerate(interior)]
                is_outliers = [c["duration_s"] < 0.80 * med_dur for c in interior]

                with st.expander("Stroke-by-stroke breakdown", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.plotly_chart(_build_line_chart(
                            labels, [c["arm_peak_vel"] for c in interior],
                            is_outliers, "Arm-pull Power", "m/s",
                        ), use_container_width=True)
                        st.plotly_chart(_build_line_chart(
                            labels, [c["coast_fraction"] * 100 for c in interior],
                            is_outliers, "Glide Time", "%",
                        ), use_container_width=True)
                    with col2:
                        st.plotly_chart(_build_line_chart(
                            labels, [c["dist_m"] for c in interior],
                            is_outliers, "Dist per Stroke", "m",
                        ), use_container_width=True)
                        st.plotly_chart(_build_line_chart(
                            labels, [c["duration_s"] for c in interior],
                            is_outliers, "Stroke Duration", "s",
                        ), use_container_width=True)

    st.divider()
    st.markdown("💬 **[Share your feedback](https://forms.gle/fb2QoNBGFUjE6WvN6)** — takes 2 minutes, helps a lot.")


if __name__ == "__main__":
    main()
