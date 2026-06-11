"""
segment_motif_spike.py — Spike: matrix-profile motif-matching, time series
chains, and Arc Curve regime detection vs. trough-based cycle segmentation.
Opens an overlay comparison as an HTML page in the browser.

Standalone diagnostic — does not modify metrics.py or any production file.
Compares segment_cycles_trough (anchors on breaststroke's glide-phase trough)
against two stumpy shape-based candidates — motif-matching (resemblance to one
consensus template) and time series chains (a sequence of motifs that evolve
link-to-link, tracking the pacing/fatigue drift a single template missed) — to
test whether either generalizes to freestyle/butterfly, which have no velocity
dead-spot for a trough threshold to lock onto. A third pass plots the Corrected
Arc Curve, which independently tests whether a session's stroke shape really
does drift between sub-populations the way the trough/motif comparison hints.
A fourth pass sweeps the self-join across a *range* of subsequence lengths —
the Pan Matrix Profile, via stumpy's `stimp` (Madrid et al.'s "Matrix Profile
XX: ... Motifs of All Lengths") — and renders it as a motif-heatmap, testing
whether the single template's *fixed* window length is itself a source of the
regime-locking the other passes found: do multiple stroke-shape "regimes"
reveal themselves as separate, well-conserved bands at *different* lengths?

Usage
-----
    python segment_motif_spike.py processed/session.csv
    python segment_motif_spike.py processed/s1.csv processed/s2.csv
    python segment_motif_spike.py processed/              # all CSVs in folder
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
import stumpy

import metrics as m

# ── colours ───────────────────────────────────────────────────────────────────
_C_VEL    = "#185fa5"
_C_TROUGH = "#aaaaaa"
_C_MOTIF  = "#d62728"
_C_CHAIN  = "#2ca02c"
_C_MP     = "#9467bd"
_C_CAC    = "#ff7f0e"

_DEFAULT_T_EST_S = 1.0   # fallback stroke-period guess when _estimate_period gives up

# PMP length sweep -- [min, max] mirrors metrics._estimate_period's own ACF
# search window (0.5-4.0s = "the physically possible range for breaststroke
# [15-120 SPM]", metrics.py:534-541): an existing, validated bound, not a new
# threshold. step is samples-per-row -- a coarser sweep than the paper's
# step=1 (which targets n in the hundreds of thousands; ours runs to the low
# thousands). ~40 rows over a [50, 400]-sample range at fs=100Hz: enough to
# read bands, cheap enough to stay in spike-territory.
_PMP_MIN_PERIOD_S = 0.5
_PMP_MAX_PERIOD_S = 4.0
_PMP_STEP_SAMPLES = 8


# ── data ──────────────────────────────────────────────────────────────────────

def _load(csv_path):
    df     = pd.read_csv(csv_path)
    t      = df["time_s"].values
    vel    = df["vel_ms"].values
    dist   = df["dist_m"].values
    result = m.compute_session_metrics(t, vel, dist)
    return t, vel, dist, result


# ── motif matching ────────────────────────────────────────────────────────────

def _anchors_from_marks(vel, marks):
    """
    Convert a sorted array of boundary-mark indices into {cycle_num, peak_idx,
    start_idx, end_idx} anchors: virtual start/end boundaries at 0/len(vel),
    consecutive marks become cycle spans, dominant peak per span is the anchor
    (the same construction segment_cycles_trough uses). Takes the *unmasked*
    vel — argmax over NaN is undefined, and the genuine peak value is what
    should be reported regardless of which segmentation's masking produced
    the marks.

    Shared by find_motif_anchors (motif-match indices as marks) and
    find_chain_anchors (chain-member indices as marks) so every segmentation
    overlays through the same shape and the same _add_overlay machinery.
    """
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


def find_motif_anchors(t, vel):
    """
    Stroke-agnostic segmentation: self-join -> consensus-stroke template -> match.

    Masks the pre-swim baseline and post-swim tail with NaN before running stumpy.
    Both are near-constant (swimmer not moving yet / already stopped); z-normalized
    distance treats constant subsequences as trivially identical to each other, so
    an unmasked self-join locks onto "the quietest spot in the recording" instead
    of a genuine stroke. stumpy's documented NaN handling assigns inf distance to
    any window touching NaN, which keeps both template selection and matching
    confined to the active-swim region. detect_phases supplies the boundaries —
    the same phase detection the production pipeline already runs, no new
    threshold logic introduced here.

    Mirrors segment_cycles_trough's output shape ({"cycle_num", "peak_idx",
    "start_idx", "end_idx"}) so both can be overlaid with shared plotting code.

    Returns (anchors, mp_distance, baseline_end, swim_end, m_len, mp,
    vel_masked) — mp_distance is mp[:, 0] with inf -> nan (for plotting); the
    phase indices let the overlay shade the excluded region; m_len, the raw
    self-join array mp (whose columns 1-3 — profile/left/right indices — go
    unused here), and vel_masked are returned so find_chain_anchors,
    find_regime_change, and find_pmp can reuse this exact self-join (or, for
    find_pmp, its exact input — a self-join at one length and a pan-self-join
    across a length range are different computations, but must run on
    identical input to be comparable). stumpy.stump (numba JIT + the join
    itself) is the expensive step — recomputing it, or rebuilding the masked
    array from scratch, would be pure waste and would risk these analyses
    silently operating on a different vel_masked/m_len than the one already
    validated here.
    """
    T_est = m._estimate_period(t, vel)
    if T_est is None:
        T_est = _DEFAULT_T_EST_S
        print(f"    _estimate_period -> None; falling back to T_est={T_est}s")

    fs    = m._compute_fs(t)
    m_len = int(T_est * fs)

    phases       = m.detect_phases(t, vel)
    baseline_end = phases["baseline_end"]
    swim_end     = phases["swim_end"]

    vel_masked = vel.copy()
    vel_masked[:baseline_end] = np.nan
    vel_masked[swim_end:]     = np.nan
    print(f"    masked baseline [0:{baseline_end}] + tail [{swim_end}:{len(vel)}] "
          f"-- active region {t[swim_end - 1] - t[baseline_end]:.1f}s of "
          f"{t[-1] - t[0]:.1f}s total")

    mp     = stumpy.stump(vel_masked, m_len)
    mp_raw = mp[:, 0].astype(np.float64)         # inf where the window touches a masked region

    template_idx = int(np.argmin(mp_raw))        # argmin ignores inf -> always lands in active region
    Q            = vel_masked[template_idx : template_idx + m_len]

    matches    = stumpy.match(Q, vel_masked)
    match_idxs = np.sort(matches[:, 1].astype(np.int64))

    mp_distance = mp_raw.copy()
    mp_distance[np.isinf(mp_distance)] = np.nan   # inf -> nan so Plotly draws a clean gap

    print(f"    T_est={T_est:.3f}s  window={m_len} samples ({fs:.1f} Hz)  "
          f"template@idx={template_idx}  matches={len(match_idxs)}")

    anchors = _anchors_from_marks(vel, match_idxs)

    return anchors, mp_distance, baseline_end, swim_end, m_len, mp, vel_masked


# ── chains & regime detection ─────────────────────────────────────────────────

def find_chain_anchors(vel, mp):
    """
    Stroke-agnostic segmentation via time series chains: a sequence of motifs
    that gradually evolve link-to-link (A resembles A', A' resembles A'', and
    the chain as a whole may drift far from where it started) rather than one
    fixed consensus template — directly targeting the "single-template
    regime-locking" 16-01 found (pacing/fatigue/effort drift stroke shape over
    a swim; a chain has no "how many regimes" parameter, it just follows the
    drift wherever it leads).

    Reuses the masked self-join's left/right matrix-profile-index columns
    (mp[:, 2], mp[:, 3]) directly — no new self-join, no slicing needed: an
    active-region window's nearest neighbor can never be masked (that distance
    is always inf, so it can't win an argmin), and stumpy's chain-following
    explicitly stops at the -1 "no neighbor" sentinel every masked-touching row
    carries — so a chain structurally cannot cross into the masked region
    (confirmed empirically: 0 of its members do, on every session tried).

    Returns the single longest unanchored chain's member indices, converted
    into the same {cycle_num, peak_idx, start_idx, end_idx} shape
    find_motif_anchors produces (via the shared _anchors_from_marks), so all
    three segmentations overlay identically through _add_overlay.
    """
    IL = mp[:, 2].astype(np.int64)
    IR = mp[:, 3].astype(np.int64)

    _, unanchored_chain = stumpy.allc(IL, IR)
    chain_idxs = np.sort(np.asarray(unanchored_chain, dtype=np.int64))

    print(f"    chain length={len(chain_idxs)}  members={chain_idxs.tolist()}")

    return _anchors_from_marks(vel, chain_idxs)


def find_regime_change(mp, m_len, baseline_end, swim_end):
    """
    Arc Curve / Corrected Arc Curve (FLUSS): locates where a continuously-
    repeating, same-type signal's sub-population shifts — e.g. fast-paced vs.
    slow-paced strokes — a structural twin to "shape drift over a swim" that
    independently tests 16-01's regime-locking diagnosis without ever asking
    "does this window resemble that one" (the question that broke twice there).

    Unlike argmin — which "naturally" ignores the masked self-join's inf
    distances (see find_motif_anchors) — FLUSS's arc-counting has no such
    immunity: feeding it the full mp[:, 1] hijacks the regime search onto the
    masked baseline/edge in 3 of 4 spike sessions (cac=0.0 at the chosen
    location — the same species of "baseline hijacking" 16-01 found for
    matching, resurfacing here because FLUSS has nothing to inherit that fix
    from). Fix: slice the profile-index column to the active-swim region and
    re-base it to the slice's own frame first — stumpy's _nnmark treats *any*
    negative index as a self-loop ("no neighbor"), so the masked rows' -1
    sentinels stay correctly inert after re-basing (confirmed empirically: no
    NaN/inf, sane cac range, regime lands inside the active region on all four
    sessions vs. 1 of 4 unsliced). The result is re-offset back to global
    coordinates before returning, matching how everything else here
    (baseline_end, swim_end, anchors, ...) is expressed.

    Returns (cac, regime_idx): cac is indexed against t[baseline_end:swim_end]
    — shorter than t, so _add_arc_curve slices t to match — regime_idx is a
    global index for the vertical marker.
    """
    # len(mp) = len(vel) - m_len + 1 < len(vel); swim_end (which can equal
    # len(vel) when a session has no tail) is clamped to len(mp) by the slice.
    I_active = mp[baseline_end:swim_end, 1].astype(np.int64) - baseline_end

    cac, regime_locs = stumpy.fluss(I_active, L=m_len, n_regimes=2)
    regime_idx = int(regime_locs[0]) + baseline_end

    print(f"    CAC regime change @ idx={regime_idx}")

    return cac, regime_idx


# ── pan matrix profile ────────────────────────────────────────────────────────

def find_pmp(t, vel_masked):
    """
    Pan Matrix Profile: self-joins swept across a *range* of subsequence
    lengths, rather than committing to one T_est-derived m_len — the direct
    fix Madrid et al. ("Matrix Profile XX: Finding and Visualizing Time Series
    Motifs of All Lengths") propose for exactly the "fixed window length" half
    of 16-01/16-02's regime-locking diagnosis. stumpy's stimp *is* this
    paper's SKIMP algorithm (its docstring cites the identical PDF the user
    supplied) — not a new dependency, already installed.

    Runs on vel_masked — the exact same NaN-masked array find_motif_anchors
    builds and validates (see its docstring): stimp is built on stump/scrump,
    which already carry that confirmed inf-on-masked-window behaviour, so the
    masked baseline/tail are excluded here the same way, by the same mechanism
    — no new masking logic, no risk of operating on a different "active region"
    than the rest of this file already agrees on.

    Length range [min_m, max_m] = [0.5s, 4.0s] in samples, converted via this
    session's own fs — not a new threshold, but metrics._estimate_period's own
    ACF search window (metrics.py:534-541), reused for the purpose it already
    serves: bounding "the physically possible range for breaststroke
    [15-120 SPM]". step is coarser than the paper's step=1 (which targets n in
    the hundreds of thousands; ours runs to the low thousands) — see
    _PMP_STEP_SAMPLES. percentage=1.0 drives stimp to its underlying exact
    stump rather than scrump's approximation: the whole point of a motif-
    heatmap is letting a human spot faint secondary bands, which approximation
    noise could obscure, and n is small enough that "exact" isn't expensive
    here — confirmed empirically (0.5-1.2s/session at step=8) rather than
    assumed.

    Returns (PAN, M, fs): PAN is the continuous per-length-normalized self-join
    distance — pmp.pan(binary=False, contrast=False), NOT pmp.PAN_. Confirmed
    empirically that pmp.PAN_ is useless for this: its own docstring says it's
    "transformed (i.e., normalized, contrasted, BINARIZED, and repeated)",
    and it comes back containing exactly two values, {0., 1.}, at stumpy's
    default threshold=0.2 — a coarse pass/fail stamp at an untuned cutoff, not
    the "low value = well-conserved... same sense mp_distance already plots"
    gradient a motif-heatmap needs to show conservation *strength*. Calling
    pan() with binary=False, contrast=False instead yields the genuinely
    continuous normalized distance (confirmed empirically: smooth range
    roughly [0.1, 0.64], not a two-value mask) — the actual "low = resembles
    its neighbour" surface, comparable to mp_distance, that the heatmap is
    for. M is the matching array of subsequence lengths in samples (pmp.M_,
    row-aligned with PAN); fs lets the heatmap renderer convert M to seconds
    and mark m_len on the same axis for reference.
    """
    fs    = m._compute_fs(t)
    min_m = int(_PMP_MIN_PERIOD_S * fs)
    max_m = int(_PMP_MAX_PERIOD_S * fs)

    pmp = stumpy.stimp(vel_masked, min_m=min_m, max_m=max_m,
                       step=_PMP_STEP_SAMPLES, percentage=1.0)
    for _ in range(len(pmp.M_)):
        pmp.update()

    print(f"    PMP: {len(pmp.M_)} lengths over [{min_m}-{max_m}] samples "
          f"({min_m / fs:.2f}-{max_m / fs:.2f}s @ {fs:.1f} Hz, "
          f"step={_PMP_STEP_SAMPLES})")

    # M_/PAN_ come back breadth-first-search-ordered (confirmed empirically:
    # e.g. [25 16 34 13 22 ...], not [13 16 22 25 34 ...]) -- a heatmap's rows
    # must run in monotonic length order for adjacent rows to mean "adjacent
    # lengths" (the visual signature a "band" relies on), so re-sort both,
    # row-aligned, before handing them to the renderer.
    order = np.argsort(pmp.M_)
    PAN = pmp.pan(binary=False, contrast=False)
    return PAN[order], pmp.M_[order], fs


# ── subplot renderers ─────────────────────────────────────────────────────────

def _boundary_times(t, cycles):
    """Cycle start times plus the final end time — the vertical lines to draw."""
    if not cycles:
        return []
    xs = [t[c["start_idx"]] for c in cycles]
    xs.append(t[min(cycles[-1]["end_idx"], len(t) - 1)])
    return xs


def _add_segmentation(fig, row, col, t, vel, cycles, color, dash, label,
                      baseline_end, swim_end, show_legend):
    """Velocity trace with ONE segmentation method's boundary lines, plus the
    masked-region shading. Split out of a combined trough+motif+chain overlay
    that became unreadable as anchor counts grew — three colours/dash-styles
    of vertical line stacked on one axes were too dense to tell apart. One
    method per row (same velocity trace, same time axis) keeps each
    comparison legible while still letting you scan vertically to see where
    each method's anchors land relative to the others."""
    v_max = float(np.nanmax(vel)) if len(vel) else 1.0

    if baseline_end > 0:
        fig.add_vrect(x0=t[0], x1=t[baseline_end], fillcolor="lightgray",
                      opacity=0.30, line_width=0, layer="below", row=row, col=col)
    if swim_end < len(t):
        fig.add_vrect(x0=t[swim_end], x1=t[-1], fillcolor="lightgray",
                      opacity=0.30, line_width=0, layer="below", row=row, col=col)

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


def _add_matrix_profile(fig, row, col, t, mp_distance, show_legend):
    """Matrix-profile distance curve — low value = 'resembles the consensus template'."""
    fig.add_trace(go.Scatter(
        x=t[:len(mp_distance)], y=mp_distance,
        mode="lines", line=dict(color=_C_MP, width=1.2),
        name="matrix profile", legendgroup="mp", showlegend=show_legend,
    ), row=row, col=col)


def _add_arc_curve(fig, row, col, t, cac, baseline_end, regime_idx, show_legend):
    """Corrected arc curve over the active-swim region — find_regime_change
    slices + re-bases mp's profile-index column there, so cac is shorter than
    t and must be plotted against the matching t-slice (low value = likely
    sub-population boundary), with a dotted vertical marker at FLUSS's
    strongest candidate regime-change index (already in global coordinates,
    like everything else here)."""
    t_active = t[baseline_end : baseline_end + len(cac)]
    fig.add_trace(go.Scatter(
        x=t_active, y=cac,
        mode="lines", line=dict(color=_C_CAC, width=1.2),
        name="arc curve", legendgroup="cac", showlegend=show_legend,
    ), row=row, col=col)
    if 0 <= regime_idx < len(t):
        fig.add_vline(x=t[regime_idx], line=dict(color=_C_CAC, width=1.6, dash="dot"),
                      row=row, col=col)


def _add_motif_heatmap(fig, row, col, t, PAN, M, fs, baseline_end, swim_end,
                       m_len, show_legend):
    """Pan-matrix-profile motif-heatmap — Madrid et al.'s central "see
    conserved structure at a glance" tool (their Fig 4/6): y = subsequence
    length in seconds, x = time, color = self-join distance at that
    length/location. greys + reversescale so dark = low distance = well-
    conserved here — the paper's black-on-white convention, and the same
    "low = resembles its neighbour" sense mp_distance already plots, just
    drawn as colour instead of curve-height.

    Sliced to the active-swim region — the same slice rationale
    find_regime_change documents: left whole, the masked baseline/tail would
    paint a uniform extreme-distance band across *every* row (the
    z-normalized-distance degeneracy 16-01 Round 1 found, here visualized
    rather than argmin'd into a false template), swamping the one comparison
    this row exists to surface — do multiple distinct length-bands appear
    *within* the strokes themselves. Unlike CAC, no re-basing is needed: PAN's
    width is len(vel_masked) exactly (confirmed empirically — unlike a
    single-length matrix profile, truncated to len(vel) - m + 1), i.e. one
    column per original sample, the most direct alignment with t/vel possible
    — slicing both by the same [baseline_end:swim_end] keeps them aligned with
    no index arithmetic at all.

    The current single-template m_len is marked with a dotted reference line
    in motif red — the same colour as that method's anchors row — so the
    question reads visually at a glance: does that line sit on the heatmap's
    darkest band, or does a darker band sit somewhere else entirely?
    """
    t_active   = t[baseline_end:swim_end]
    PAN_active = PAN[:, baseline_end:swim_end]

    fig.add_trace(go.Heatmap(
        x=t_active, y=M / fs, z=PAN_active,
        colorscale="greys", reversescale=True, showscale=show_legend,
        name="PMP distance", showlegend=False,
    ), row=row, col=col)
    fig.add_hline(y=m_len / fs, line=dict(color=_C_MOTIF, width=1.4, dash="dot"),
                  row=row, col=col)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Spike: motif-matching vs. trough segmentation overlay. Opens in browser.",
    )
    parser.add_argument(
        "inputs", nargs="+",
        help="Processed CSV file(s) or a folder of CSVs",
    )
    args = parser.parse_args()

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
    subplot_titles = (
        [p.stem for p in paths]
        + ["motif-match"] * n
        + ["chain"] * n
        + ["matrix profile"] * n
        + ["arc curve"] * n
        + ["motif-heatmap (PMP)"] * n
    )
    fig = make_subplots(
        rows=6, cols=n,
        subplot_titles=subplot_titles,
        vertical_spacing=0.07,
        horizontal_spacing=0.03,
        shared_xaxes=True,
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

        trough_cycles = result["cycles"]
        print(f"\n-- {path.stem} --")
        print(f"    trough cycles : {len(trough_cycles)}")

        (motif_anchors, mp_distance, baseline_end, swim_end, m_len, mp,
         vel_masked) = find_motif_anchors(t, vel)
        print(f"    motif anchors : {len(motif_anchors)}")

        chain_anchors = find_chain_anchors(vel, mp)
        print(f"    chain anchors : {len(chain_anchors)}")

        cac, regime_idx = find_regime_change(mp, m_len, baseline_end, swim_end)

        PAN, M, fs = find_pmp(t, vel_masked)

        for r, (cycles, color, dash, label) in enumerate((
            (trough_cycles,  _C_TROUGH, "dash",    "trough"),
            (motif_anchors,  _C_MOTIF,  "dot",     "motif"),
            (chain_anchors,  _C_CHAIN,  "dashdot", "chain"),
        ), start=1):
            _add_segmentation(fig, row=r, col=col, t=t, vel=vel, cycles=cycles,
                              color=color, dash=dash, label=label,
                              baseline_end=baseline_end, swim_end=swim_end,
                              show_legend=show_legend)
        _add_matrix_profile(fig, row=4, col=col, t=t, mp_distance=mp_distance,
                            show_legend=show_legend)
        _add_arc_curve(fig, row=5, col=col, t=t, cac=cac, baseline_end=baseline_end,
                       regime_idx=regime_idx, show_legend=show_legend)
        _add_motif_heatmap(fig, row=6, col=col, t=t, PAN=PAN, M=M, fs=fs,
                           baseline_end=baseline_end, swim_end=swim_end,
                           m_len=m_len, show_legend=show_legend)
        n_loaded += 1

    if n_loaded == 0:
        print("No data to plot.", file=sys.stderr)
        sys.exit(1)

    fig.update_layout(
        title=dict(
            text=("Same velocity trace, one segmentation method's boundary "
                  "lines per row — trough (grey, dashed) / motif-match (red, "
                  "dotted) / chain (green, dash-dot) — shaded band = "
                  "baseline/tail masked out of matching; matrix-profile "
                  "distance and corrected arc curve (orange dotted = "
                  "candidate regime change) beneath; bottom row = pan-matrix-"
                  "profile motif-heatmap (dark = well-conserved at that "
                  "window-length/time — dotted line = today's single m_len — "
                  "do other, darker bands appear off that line?)"),
            font=dict(size=13),
        ),
        width=max(720, COL_W * n + 120),
        height=2040,
        template="plotly_white",
        legend=dict(orientation="h", y=-0.04, x=0.0, font=dict(size=10)),
        font=dict(size=10),
    )

    fig.update_yaxes(title_text="Velocity (m/s)", col=1, row=1)
    fig.update_yaxes(title_text="Velocity (m/s)", col=1, row=2)
    fig.update_yaxes(title_text="Velocity (m/s)", col=1, row=3)
    fig.update_yaxes(title_text="MP distance", col=1, row=4)
    fig.update_yaxes(title_text="Arc curve", col=1, row=5)
    fig.update_yaxes(title_text="Window length (s)", col=1, row=6)
    fig.update_xaxes(title_text="Time (s)", row=6)

    out = Path(tempfile.gettempdir()) / "segment_motif_spike.html"
    fig.write_html(str(out))
    webbrowser.open(str(out))
    print(f"\nOpened -> {out}")


if __name__ == "__main__":
    main()
