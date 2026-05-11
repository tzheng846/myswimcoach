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

st.set_page_config(layout="centered", page_title="SwimCoach")

# ── Phase color palette ───────────────────────────────────────────────────────
_C_STEADY   = "#4c9be8"
_C_RAMP     = "#e8a24c"
_C_OUTLIER  = "#e87070"
_C_BOUNDARY = "#aaaaaa"
_C_EXCL     = "#cccccc"

SUGGESTED = [
    "How does my stroke rate look?",
    "What's causing my velocity drops?",
    "How consistent am I stroke-to-stroke?",
    "How do my last strokes compare to the first?",
]

SUGGESTED_COMPARE = [
    "What improved between sessions?",
    "What got worse?",
    "Where should I focus next?",
    "Why did my speed change?",
]

_CSV_A = "processed/sample_br_1.csv"
_CSV_B = "processed/sample_br_2.csv"


def _cycle_color(c: dict, is_outlier: bool, is_boundary: bool) -> str:
    if is_boundary:
        return _C_BOUNDARY
    if is_outlier:
        return _C_OUTLIER
    return _C_STEADY if c.get("phase") == "steady" else _C_RAMP


def _abs_cycle_num(t_peak: float, full_boundaries: list) -> str:
    """Return 1-indexed absolute cycle number by matching peak time."""
    for i, (_, _, tp) in enumerate(full_boundaries):
        if not np.isnan(tp) and abs(tp - t_peak) < 0.15:
            return str(i + 1)
    return ""


# ── Cached: full-range cycle boundaries for slider sync ──────────────────────
@st.cache_data
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


# ── Cached: trimmed data + metrics ───────────────────────────────────────────
@st.cache_data
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
        c["t_peak_s"] = float(t[idx]) if idx is not None and idx < len(t) else float("nan")

    return t_full, vel_full, accel_full, t, vel, accel, result


# ── Velocity (+ optional acceleration) chart ─────────────────────────────────
def _build_vel_chart(t_full, vel_full, accel_full, t_start, t_end, cycles,
                     full_boundaries, show_accel=True, show_labels=True):
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
    ), **vel_kw)

    # Zero line
    if show_accel:
        fig.add_hline(y=0, line=dict(color="rgba(150,150,150,0.6)", width=0.8, dash="dash"), row=1, col=1)
    else:
        fig.add_hline(y=0, line=dict(color="rgba(150,150,150,0.6)", width=0.8, dash="dash"))

    # Excluded region shading
    t_lo, t_hi = t_full[0], t_full[-1]
    for x0, x1 in [(t_lo, t_start), (t_end, t_hi)]:
        if x0 < x1:
            if show_accel:
                for row in (1, 2):
                    fig.add_vrect(x0=x0, x1=x1, fillcolor=_C_EXCL, opacity=0.35,
                                  layer="below", line_width=0, row=row, col=1)
            else:
                fig.add_vrect(x0=x0, x1=x1, fillcolor=_C_EXCL, opacity=0.35,
                              layer="below", line_width=0)

    # Arm-pull peak markers with cycle number labels
    if cycles:
        med_dur    = np.median([c["duration_s"] for c in cycles])
        bound_ids  = {id(cycles[0]), id(cycles[-1])} if len(cycles) > 1 else set()

        px, py, pt, pc, pcd = [], [], [], [], []
        for c in cycles:
            t_pk = c.get("t_peak_s", float("nan"))
            v_pk = c.get("arm_peak_vel", float("nan"))
            if np.isnan(t_pk) or np.isnan(v_pk):
                continue
            is_out = c["duration_s"] < 0.80 * med_dur
            is_bnd = id(c) in bound_ids
            color  = _cycle_color(c, is_out, is_bnd)
            label  = _abs_cycle_num(t_pk, full_boundaries)
            px.append(t_pk); py.append(v_pk)
            pt.append(label); pc.append(color)
            pcd.append([
                label,
                f"{c.get('trough_vel_ms', float('nan')):.3f}",
                f"{c.get('coast_fraction', float('nan'))*100:.1f}",
                f"{c.get('duration_s', float('nan')):.2f}",
                f"{c.get('dist_m', float('nan')):.3f}",
                "yes" if is_out else "no",
            ])

        marker_colors = pc if show_labels else ["#999999"] * len(px)
        scatter_kw = dict(
            x=px, y=py,
            mode="markers+text" if show_labels else "markers",
            marker=dict(symbol="triangle-up", size=10, color=marker_colors,
                        line=dict(color="white", width=1)),
            text=pt if show_labels else [""] * len(pt),
            textposition="top center",
            textfont=dict(size=11, color=marker_colors),
            showlegend=False,
        )
        if show_labels:
            scatter_kw["customdata"] = pcd
            scatter_kw["hovertemplate"] = (
                "<b>Stroke %{customdata[0]}</b>  t=%{x:.2f}s<br>"
                "arm peak: %{y:.3f} m/s<br>"
                "trough: %{customdata[1]} m/s<br>"
                "glide: %{customdata[2]}%<br>"
                "duration: %{customdata[3]}s<br>"
                "dist/stroke: %{customdata[4]} m<br>"
                "outlier: %{customdata[5]}"
                "<extra></extra>"
            )
        else:
            scatter_kw["customdata"] = pcd
            scatter_kw["hovertemplate"] = "Stroke %{customdata[0]}<extra></extra>"
        fig.add_trace(go.Scatter(**scatter_kw), **vel_kw)

    if show_accel:
        fig.add_trace(go.Scatter(
            x=t_full, y=accel_full,
            mode="lines", line=dict(color="#f97316", width=0.9),
            showlegend=False,
        ), row=2, col=1)
        fig.update_yaxes(title_text="vel (m/s)", row=1, col=1)
        fig.update_yaxes(title_text="accel (m/s²)", row=2, col=1)
        fig.update_xaxes(title_text="time (s)", row=2, col=1)
        fig.update_layout(height=420, margin=dict(l=60, r=20, t=30, b=40))
    else:
        fig.update_yaxes(title_text="Speed (m/s)")
        fig.update_xaxes(title_text="Time (s)")
        fig.update_layout(height=280, margin=dict(l=60, r=20, t=30, b=40))

    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.2)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.2)")
    return fig


# ── Stats metric cards ────────────────────────────────────────────────────────
def _build_stats_table(session: dict, simple: bool = False):
    all_stats = [
        ("Stroke Rate",
         f"{session.get('stroke_rate_spm', 0):.1f} spm",
         "Strokes per minute. High = fast tempo, less time per stroke. "
         "Low = slower, more deliberate. Typical breaststroke: 50–65 spm. "
         "Higher tempo often trades distance per stroke."),

        ("Average Speed",
         f"{session.get('mean_vel_ms', 0):.2f} m/s",
         "Mean forward speed over the session. Higher is faster, always."),

        ("Dist per Stroke",
         f"{session.get('mean_dps_m', 0):.2f} m",
         "Meters traveled per stroke. High = efficient, each pull takes you further. "
         "Low = energy wasted — you're working hard but not going far."),

        ("Glide Time",
         f"{session.get('mean_coast_fraction', 0) * 100:.0f}%",
         "Fraction of each stroke spent gliding. "
         "High with good speed = active, streamlined glide. "
         "High with low dist per stroke = passive drift, dead weight. "
         "Low = choppy rhythm, not using your momentum."),

        ("Fatigue Index",
         f"{session.get('fatigue_index_pct', 0):.1f}%",
         "Arm power drop from first quarter to last. "
         "High (>10%) = significant fatigue by the end. "
         "Low or negative = well-paced or still warming up."),

        ("Stroke Consistency",
         f"{session.get('cv_arm_peak_vel', 0):.3f}",
         "Variation in arm power stroke to stroke. "
         "Low (<0.10) = consistent, repeatable technique. "
         "High (>0.20) = big swings between strokes — technique breaking down."),
    ]
    stats = all_stats[:3] if simple else all_stats
    cols = st.columns(3)
    for i, (label, value, tip) in enumerate(stats):
        with cols[i % 3]:
            st.metric(label=label, value=value, help=tip)


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
    st.sidebar.title("SwimCoach")
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
                st.session_state[f"t_min{suffix}"]            = t_min
                st.session_state[f"t_max{suffix}"]            = t_max
                st.session_state[f"n_cycles{suffix}"]         = n
                st.session_state[f"cycle_boundaries{suffix}"] = boundaries
                st.session_state[f"time_range{suffix}"]       = (t_min, t_max)
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
                             cycles_a, bounds_a, show_accel=False, show_labels=not simple),
            use_container_width=True)
        st.caption("Click and drag to zoom. Double-click to reset.")

        st.markdown("**Session B — sample_br_2**")
        st.plotly_chart(
            _build_vel_chart(t_full_b, vel_full_b, accel_full_b, t_start_b, t_end_b,
                             cycles_b, bounds_b, show_accel=False, show_labels=not simple),
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
            st.session_state.update({
                "current_file":     str(selected),
                "cycle_boundaries": boundaries,
                "t_min": t_min, "t_max": t_max, "n_cycles": n,
                "time_range":  (t_min, t_max),
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
        full_boundaries = st.session_state.cycle_boundaries

        for c in cycles:
            c["abs_num"] = _abs_cycle_num(c.get("t_peak_s", float("nan")),
                                          full_boundaries) or None

        st.title(f"Session: {selected.stem}")

        if simple:
            st.info(
                "**How to use:** Select your session from the sidebar. "
                "The chart shows your speed over time — each numbered peak is one stroke. "
                "Use the analysis window below to zoom in on any section, "
                "then ask your coach a question."
            )

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
                             show_accel=not simple, show_labels=not simple),
            use_container_width=True)
        st.caption("Click and drag on the chart to zoom in. Double-click to reset.")

        _build_stats_table(session, simple=simple)

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
