"""
Phase 80 — 3-column HUMAN vs SHIPPED vs FIX stroke-segmentation viewer (interactive).

Diagnosis of freestyle auto STROKE segmentation (arm entries, NOT cycles), scored inside
the human-annotated swim window [stroke_start_s, finish_s] (D5). One row per annotated
freestyle session; three columns, same velocity trace + same y/x range across the row:

    col 1  Human (arm entries)          red    — ground-truth stroke_marks_s in the window
    col 2  Shipped ridge (bias 0.5)     blue   — segment_cycles_wavelet's ridge, UN-paired
    col 3  No low-band (bias 0.0)       green  — the Phase-80 candidate (low-band bias off)

"stroke" = one arm entry; a freestyle cycle = 2 strokes. Both detectors are the wavelet
ridge integer-phase-crossing stroke detector (metrics._cwt_ridge → cumulative phase),
differing ONLY in low_band_bias. Neither is the production k=2-paired cycle output — the
point is to compare at STROKE granularity.

Reuses visualize_freestyle_seg (DB load, window, strokes_wavelet) — no re-implementation.

RUN:
    C:/Users/TonyZheng/miniconda3/envs/mySwimCoach/python.exe \
        .paul/phases/80-stroke-cycle-segmentation/human_vs_seg_3col.py [out.html]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np                          # noqa: E402
import plotly.graph_objects as go           # noqa: E402
from plotly.subplots import make_subplots   # noqa: E402

import visualize_freestyle_seg as vz        # noqa: E402  (DB load + strokes_wavelet + _win + se)
import segmenter_eval as se                 # noqa: E402
import metrics as m                         # noqa: E402  (ridge + period, for the adaptive guard)

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "figs" / "human_vs_seg_4col.html"
PAD_S = 0.8                                  # x-margin around the window
C_VEL   = "#8a8a8a"
C_HUMAN = "#d62728"                          # red
C_SHIP  = "#1f77b4"                          # blue
C_FIX   = "#2ca02c"                          # green
C_ADAPT = "#9467bd"                          # purple
COL_TITLES = ("Human (arm entries)", "Shipped ridge · bias 0.5",
              "No low-band · bias 0.0", "Adaptive bias · guard")

# Adaptive guard (prototype — mirrors Phase 65-02's low-rail guard in detect_swim_window):
# keep the shipped bias 0.5 by default; flip to 0.0 ONLY when the shipped ridge is
# subharmonic-locked — its median frequency sits below SUBHARM_FRAC × the INDEPENDENT
# autocorrelation stroke frequency (_estimate_period). Anchoring on the autocorr estimate,
# not on the bias-0.0 ridge, is what stops it firing on Leo (where bias 0.0 just overcounts).
SUBHARM_FRAC = 0.70


def _rate(times):
    return 60.0 / np.mean(np.diff(times)) if len(times) >= 2 else float("nan")


def _rate_err(pred, true):
    return 100.0 * (pred - true) / true if (np.isfinite(pred) and np.isfinite(true) and true) else float("nan")


def strokes_adaptive(d, subharm_frac=SUBHARM_FRAC):
    """Adaptive low-band bias. Returns (stroke_times, bias_used, guard_info).

    Guard = subharmonic-lock detector: compare the SHIPPED ridge's median frequency to an
    INDEPENDENT autocorr stroke frequency. If the shipped ridge sits below subharm_frac× it,
    the low-band bias has dragged the ridge onto a subharmonic (Max's failure) → use bias 0.0;
    otherwise keep the shipped 0.5. Never worse than shipped unless the guard fires.
    """
    a, b = vz._win(d)
    vel = d["vel"][a:b]
    t = np.arange(b - a) / d["fs"]
    per = m._estimate_period(t, vel)
    f_auto = (1.0 / per) if per else float("nan")
    rf_ship, _ = m._cwt_ridge(vel, d["fs"], low_band_bias=0.5)
    f_ship = float(np.median(rf_ship)) if rf_ship is not None else float("nan")
    railed = bool(np.isfinite(f_auto) and np.isfinite(f_ship) and f_ship < subharm_frac * f_auto)
    bias = 0.0 if railed else 0.5
    ratio = (f_ship / f_auto) if (np.isfinite(f_auto) and f_auto) else float("nan")
    return vz.strokes_wavelet(d, bias), bias, dict(f_auto=f_auto, f_ship=f_ship, ratio=ratio, railed=railed)


def analyze(d):
    """Everything one row needs. None if the session has no annotated swim window."""
    if d["ss"] is None or d["fin"] is None:
        return None
    a, b = vz._win(d)
    fs = d["fs"]
    lo, hi = a / fs, b / fs
    marks = [mk for mk in d["marks"] if lo <= mk <= hi]
    ship  = sorted(vz.strokes_wavelet(d, 0.5))
    fix   = sorted(vz.strokes_wavelet(d, 0.0))
    adap_t, adap_bias, guard = strokes_adaptive(d)
    adap = sorted(adap_t)
    cov   = se.coverage(marks, lo, hi)["ratio"]
    true_rate = _rate(marks)
    return dict(
        a=a, b=b, lo=lo, hi=hi, marks=marks, ship=ship, fix=fix, adap=adap, cov=cov,
        well=bool(cov and 0.7 <= cov <= 1.4),
        true_n=len(marks), ship_n=len(ship), fix_n=len(fix), adap_n=len(adap),
        true_rate=true_rate, ship_rate=_rate(ship), fix_rate=_rate(fix), adap_rate=_rate(adap),
        d_ship=len(ship) - len(marks), d_fix=len(fix) - len(marks), d_adap=len(adap) - len(marks),
        err_ship=_rate_err(_rate(ship), true_rate), err_fix=_rate_err(_rate(fix), true_rate),
        err_adap=_rate_err(_rate(adap), true_rate),
        adap_bias=adap_bias, guard=guard,
    )


def _vlines(xs, y0, y1, color, name, width=1.4):
    """One scatter carrying all vertical marks (None-separated) — cheap + hoverable."""
    X, Y = [], []
    for x in xs:
        X += [x, x, None]
        Y += [y0, y1, None]
    return go.Scatter(x=X, y=Y, mode="lines", line=dict(color=color, width=width),
                      name=name, hovertemplate=name + " %{x:.2f}s<extra></extra>",
                      showlegend=False)


def build(data):
    rows = [(d, a) for d in data if (a := analyze(d)) is not None]
    n = len(rows)
    titles = []
    for d, r in rows:
        who = f"{d['swimmer']} {d['when'][5:16].replace('T', ' ')}"
        part = "" if r["well"] else " ⚠partial"
        gtag = f"→0.0 guard✓" if r["adap_bias"] == 0.0 else "→0.5"
        titles += [
            f"{who} · human {r['true_n']} ({r['true_rate']:.0f} spm) cov {r['cov'] or 0:.2f}{part}",
            f"shipped {r['ship_n']} ({r['d_ship']:+d}) · {r['err_ship']:+.0f}%",
            f"fix {r['fix_n']} ({r['d_fix']:+d}) · {r['err_fix']:+.0f}%",
            f"adaptive {r['adap_n']} ({r['d_adap']:+d}) · {r['err_adap']:+.0f}% · {gtag}",
        ]

    fig = make_subplots(rows=n, cols=4, subplot_titles=titles,
                        vertical_spacing=min(0.010, 0.9 / max(n - 1, 1)),
                        horizontal_spacing=0.028)

    for i, (d, r) in enumerate(rows, start=1):
        t, vel, fs = d["t"], d["vel"], d["fs"]
        pad = PAD_S
        xlo, xhi = max(0.0, r["lo"] - pad), r["hi"] + pad
        wmask = (t >= xlo) & (t <= xhi)
        seg_v = vel[(t >= r["lo"]) & (t <= r["hi"])]
        vmax = float(np.nanmax(seg_v)) if seg_v.size else float(np.nanmax(vel))
        vmin = min(0.0, float(np.nanmin(seg_v)) if seg_v.size else 0.0)
        y0, y1 = vmin, vmax * 1.10
        cols = [(1, r["marks"], C_HUMAN, "human"),
                (2, r["ship"], C_SHIP, "shipped 0.5"),
                (3, r["fix"], C_FIX, "fix 0.0"),
                (4, r["adap"], C_ADAPT, f"adaptive {r['adap_bias']:.1f}")]
        for col, xs, color, nm in cols:
            # shaded human window
            fig.add_vrect(x0=r["lo"], x1=r["hi"], fillcolor="#000", opacity=0.05,
                          line_width=0, row=i, col=col)
            fig.add_trace(go.Scatter(x=t[wmask], y=vel[wmask], mode="lines",
                                     line=dict(color=C_VEL, width=1.0), showlegend=False,
                                     hoverinfo="skip"), row=i, col=col)
            fig.add_trace(_vlines(xs, y0, y1, color, nm), row=i, col=col)
            fig.update_xaxes(range=[xlo, xhi], row=i, col=col,
                             tickfont=dict(size=8), title=None)
            fig.update_yaxes(range=[y0, y1], row=i, col=col, tickfont=dict(size=8))

    # column banner
    ncol = len(COL_TITLES)
    for c, tt in enumerate(COL_TITLES):
        fig.add_annotation(text=f"<b>{tt}</b>", xref="paper", yref="paper",
                           x=(c + 0.5) / ncol, y=1.0, yshift=26, showarrow=False,
                           font=dict(size=12))
    for ann in fig.layout.annotations:
        if ann.text not in [f"<b>{t}</b>" for t in COL_TITLES]:
            ann.font.size = 8.5

    fig.update_layout(
        height=max(320, 165 * n + 90), width=1850,
        template="plotly_white", margin=dict(t=70, l=48, r=20, b=40),
        title=dict(text="Freestyle auto STROKE segmentation — human vs shipped (0.5) vs "
                        "no-low-band (0.0) vs adaptive-bias guard, inside the human swim window",
                   font=dict(size=15)),
    )
    return fig, rows


def _block(well, key_n, key_e, tol=1):
    ex   = sum(1 for r in well if r[key_n] == 0)          # exact count
    w1   = sum(1 for r in well if abs(r[key_n]) <= tol)   # within +/- tol strokes
    md   = np.median([abs(r[key_n]) for r in well]) if well else float("nan")
    me   = np.median([abs(r[key_e]) for r in well if np.isfinite(r[key_e])]) if well else float("nan")
    return ex, w1, md, me


_DETS = [("shipped (0.5)", "d_ship", "err_ship"),
         ("fix (0.0)", "d_fix", "err_fix"),
         ("adaptive", "d_adap", "err_adap")]


def summary(rows):
    well = [r for _, r in rows if r["well"]]
    print(f"\nrows plotted = {len(rows)}   well-labeled = {len(well)}")
    print("OVERALL (well-labeled):")
    for tag, kn, ke in _DETS:
        ex, w1, md, me = _block(well, kn, ke)
        print(f"  {tag:<14} exact {ex}/{len(well)}={ex/max(len(well),1):.0%}"
              f"   within±1 {w1}/{len(well)}={w1/max(len(well),1):.0%}"
              f"   median|ΔN| {md:.1f}   median|rate err| {me:.1f}%")
    print("PER SWIMMER (well-labeled), within±1 stroke  (exact in parens):")
    print(f"  {'swimmer':<7}{'n':>3}   {'shipped 0.5':>20}{'fix 0.0':>20}{'adaptive':>20}")
    for sw in ("Tony", "Leo", "Max"):
        w = [r for d, r in rows if r["well"] and d["swimmer"] == sw]
        if not w:
            continue
        cells = ""
        for _, kn, ke in _DETS:
            ex, w1, _, _ = _block(w, kn, ke)
            cells += f"{f'{w1}/{len(w)}={w1/len(w):.0%} (ex {ex})':>20}"
        print(f"  {sw:<7}{len(w):>3}   {cells}")

    print("\nGUARD DIAGNOSTIC — which sessions the subharmonic guard flipped to bias 0.0"
          f"  (SUBHARM_FRAC={SUBHARM_FRAC})")
    print(f"  {'swimmer':<7}{'when':<12}{'f_auto':>8}{'f_ship':>8}{'ratio':>7}{'flip':>6}"
          f"{'true':>6}{'ship':>6}{'adap':>6}")
    fired = 0
    for d, r in sorted(rows, key=lambda x: (x[0]['swimmer'], x[0]['when'])):
        g = r["guard"]
        flip = r["adap_bias"] == 0.0
        fired += int(flip and r["well"])
        print(f"  {d['swimmer']:<7}{d['when'][5:16]:<12}{g['f_auto']:>8.2f}{g['f_ship']:>8.2f}"
              f"{g['ratio']:>7.2f}{'  ✓' if flip else '  ·':>6}"
              f"{r['true_n']:>6}{r['ship_n']:>6}{r['adap_n']:>6}"
              f"{'' if r['well'] else '  ⚠partial'}")
    print(f"  guard fired on {fired}/{len(well)} well-labeled sessions")


def main():
    print("loading annotated freestyle from Supabase ...")
    data = vz.load_freestyle()
    from collections import Counter
    print(f"loaded {len(data)} sessions: {dict(Counter(d['swimmer'] for d in data))}")
    fig, rows = build(data)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(OUT), include_plotlyjs=True, full_html=True)
    print("wrote", OUT)
    summary(rows)


if __name__ == "__main__":
    main()
