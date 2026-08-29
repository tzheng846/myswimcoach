"""Phase 80 — freestyle stroke-cycle segmentation exploration (dev scratch).

Pulls every annotated FREESTYLE session, plots velocity + human arm-entry marks +
the annotated vs production swim windows, then applies every prior segmenter attempt
(the tools/segmenter_candidates.py set + the production paired-k2 wavelet + the shipped
learned detector) and scores count / F1 / offset. Figures -> phase figs/ dir.

Run:  python scratch/phase80_freestyle.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The local supabase/ SQL dir shadows the installed supabase-py package; purge bare +
# root path entries, import supabase, then restore root + tools for local modules.
sys.path = [p for p in sys.path if p not in ("", ".", str(ROOT))]
from dotenv import load_dotenv          # noqa: E402
from supabase import create_client      # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import numpy as np                       # noqa: E402
import matplotlib                        # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
from scipy.signal import find_peaks      # noqa: E402

import metrics as m                      # noqa: E402
import annotations as annot              # noqa: E402
import segmenter_eval as se              # noqa: E402
import segmenter_candidates as sc        # noqa: E402

load_dotenv(str(ROOT / ".env"))
FIGS = ROOT / ".paul" / "phases" / "80-stroke-cycle-segmentation" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)
TOL = 0.15


# ── load ──────────────────────────────────────────────────────────────────────
def load_freestyle():
    sb = create_client(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    anns = (sb.table("session_annotations")
            .select("session_id, phases, stroke_marks_s").execute().data) or []
    ids = [a["session_id"] for a in anns]
    rows = (sb.table("sessions")
            .select("id, stroke_type, created_at, sample_rate_hz, velocity_profile")
            .in_("id", ids).execute().data) or []
    by = {r["id"]: r for r in rows}
    out = []
    for a in anns:
        s = by.get(a["session_id"])
        if not s or (s.get("stroke_type") or "") != "freestyle":
            continue
        vel = np.asarray(s.get("velocity_profile") or [], float)
        if vel.size < 200:
            continue
        fs = float(s.get("sample_rate_hz") or annot.FS_HZ)
        ph = a.get("phases") or {}
        marks = sorted(float(x) for x in (a.get("stroke_marks_s") or []))
        out.append(dict(
            id=s["id"], when=(s.get("created_at") or "")[:19], fs=fs, vel=vel,
            t=np.arange(vel.size) / fs, marks=marks,
            ss=ph.get("stroke_start_s"), fin=ph.get("finish_s"),
        ))
    out.sort(key=lambda d: d["when"])
    return out


# ── candidate segmenters (the "attempts we tried before") ──────────────────────
def _peakpick(t, v, fs):
    det = np.nan_to_num(m._detrend_for_cwt(v, fs))
    per = m._estimate_period(t, v) or 1.0
    pk, _ = find_peaks(det, distance=max(1, int(0.45 * per * fs)),
                       prominence=0.25 * float(np.percentile(np.abs(det), 95)))
    return sc._cycles_from_bounds(v, pk)


CANDS = {
    "wavelet (unpaired, headline)": lambda t, v, fs: m.segment_cycles_wavelet(t, v),
    "PRODUCTION wavelet paired-k2": lambda t, v, fs: m._pair_boundaries(m.segment_cycles_wavelet, 2)(t, v),
    "peakpick": _peakpick,
    "R1 snap->vel min": sc.make_snap("min"),
    "R2 snap->steep rise": sc.make_snap("rise"),
    "C1 matched filter": sc.make_matched_filter(),
    "C3 autocorr grid": sc.make_autocorr(),
    "learned (shipped weights)": lambda t, v, fs: m._learned_boundaries(t, v),
}


def cyc_bounds_time(cycles, a, fs):
    """cycle dicts (slice-relative) -> absolute boundary times (s)."""
    if not cycles:
        return []
    idx = [c["start_idx"] for c in cycles] + [cycles[-1]["end_idx"]]
    return [(a + i) / fs for i in idx]


def apply_candidate(name, d, a, b):
    """Run one candidate on window [a,b). Returns (boundary_times_abs, n_pred)."""
    va, tb = d["vel"][a:b], np.arange(b - a) / d["fs"]
    try:
        if name.startswith("C2"):
            cyc = sc.cand_trough_untrimmed(tb, va, d["fs"], full=d["vel"], offset=a)
        else:
            cyc = CANDS[name](tb, va, d["fs"])
    except Exception:
        cyc = None
    bt = cyc_bounds_time(cyc, a, d["fs"])
    return bt, len(bt)


# ── plotting ───────────────────────────────────────────────────────────────────
def plot_overview(data):
    n = len(data)
    ncol = 3
    nrow = (n + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(5.2 * ncol, 2.4 * nrow), squeeze=False)
    for k, d in enumerate(data):
        ax = axes[k // ncol][k % ncol]
        ax.plot(d["t"], d["vel"], lw=0.6, color="#333")
        for mk in d["marks"]:
            ax.axvline(mk, color="tab:red", lw=0.7, alpha=0.7)
        if d["ss"] is not None and d["fin"] is not None:
            ax.axvspan(d["ss"], d["fin"], color="tab:green", alpha=0.10)
            ax.axvline(d["ss"], color="tab:green", lw=1.2)
            ax.axvline(d["fin"], color="tab:green", lw=1.2)
        dw = m.detect_swim_window(d["t"], d["vel"], "freestyle")
        if dw:
            ip, sw = dw
            ax.axvline(ip / d["fs"], color="tab:blue", lw=1.2, ls="--")
            ax.axvline(min(sw, len(d["vel"]) - 1) / d["fs"], color="tab:blue", lw=1.2, ls="--")
        ax.set_title(f"{d['when'][5:]}  n_marks={len(d['marks'])}", fontsize=8)
        ax.tick_params(labelsize=6)
    for k in range(n, nrow * ncol):
        axes[k // ncol][k % ncol].axis("off")
    fig.suptitle("Freestyle — velocity, human arm-entry marks (red), "
                 "annotated window (green), production window (blue --)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    p = FIGS / "01_overview_all_freestyle.png"
    fig.savefig(p, dpi=110)
    plt.close(fig)
    return p


def plot_candidates_for(d, tag):
    names = list(CANDS.keys())
    fig, axes = plt.subplots(len(names), 1, figsize=(11, 1.5 * len(names)), squeeze=False, sharex=True)
    i0 = int(round(d["ss"] * d["fs"]))
    i1 = int(round(d["fin"] * d["fs"]))
    for r, name in enumerate(names):
        ax = axes[r][0]
        ax.plot(d["t"], d["vel"], lw=0.6, color="#999")
        ax.axvspan(d["ss"], d["fin"], color="tab:green", alpha=0.07)
        for mk in d["marks"]:
            ax.axvline(mk, color="tab:red", lw=0.8, alpha=0.6)
        bt, npred = apply_candidate(name, d, i0, i1)
        for x in bt:
            ax.axvline(x, color="tab:blue", lw=1.0, ls="--", alpha=0.9)
        sc_ = se.score_series(bt, d["marks"], TOL)
        ax.set_ylabel(name, fontsize=7, rotation=0, ha="right", va="center")
        ax.set_title(f"n_pred={npred}  F1={sc_['f1']:.2f}  MAE={sc_['mae_s'] or float('nan'):.3f}"
                     f"  bias={sc_['bias_s'] or float('nan'):+.3f}s", fontsize=7, loc="right")
        ax.tick_params(labelsize=6)
    fig.suptitle(f"Candidates on annotated window — {tag}  ({d['when'][5:]}, "
                 f"n_marks={len(d['marks'])})   red=human entry, blue--=predicted", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    p = FIGS / f"02_candidates_{tag}.png"
    fig.savefig(p, dpi=115)
    plt.close(fig)
    return p


# ── scoring ──────────────────────────────────────────────────────────────────
def score_table(data, window="annotated"):
    rows = {}
    for d in data:
        if window == "annotated":
            if d["ss"] is None or d["fin"] is None:
                continue
            a = int(round(d["ss"] * d["fs"]))
            b = int(round(d["fin"] * d["fs"]))
        else:
            dw = m.detect_swim_window(d["t"], d["vel"], "freestyle")
            if not dw:
                continue
            a, b = dw
        if b - a < 100 or len(d["marks"]) < 4:
            continue
        n_arm = len(d["marks"])
        marks_win = [mk for mk in d["marks"] if a / d["fs"] <= mk <= b / d["fs"]]
        for name in CANDS:
            bt, npred = apply_candidate(name, d, a, b)
            s = se.score_series(bt, marks_win, TOL)
            rows.setdefault(name, []).append(dict(
                f1=s["f1"], mae=s["mae_s"], bias=s["bias_s"],
                ratio_arm=npred / n_arm if n_arm else np.nan, npred=npred))
    return rows


def print_table(rows, title):
    print(f"\n=== {title} (freestyle, median over sessions) ===")
    print(f"{'candidate':<30}{'F1':>7}{'MAE':>8}{'bias':>9}{'bnd/arm':>9}{'n':>4}")
    for name, rs in rows.items():
        f1 = np.median([r["f1"] for r in rs])
        maes = [r["mae"] for r in rs if r["mae"] is not None]
        biases = [r["bias"] for r in rs if r["bias"] is not None]
        ratio = np.median([r["ratio_arm"] for r in rs])
        mae = np.median(maes) if maes else float("nan")
        bias = np.median(biases) if biases else float("nan")
        print(f"{name:<30}{f1:>7.3f}{mae:>8.3f}{bias:>+9.3f}{ratio:>9.2f}{len(rs):>4}")


def tolerance_sweep(data):
    SWEEP = (0.05, 0.10, 0.15, 0.20, 0.30)
    names = ["wavelet (unpaired, headline)", "peakpick", "R2 snap->steep rise",
             "PRODUCTION wavelet paired-k2"]
    print("\n=== tolerance sweep (median F1, annotated window) ===")
    print(f"{'candidate':<30}" + "".join(f"{f'±{x}':>8}" for x in SWEEP))
    for name in names:
        vals = []
        for tol in SWEEP:
            per = []
            for d in data:
                if d["ss"] is None or d["fin"] is None or len(d["marks"]) < 4:
                    continue
                a = int(round(d["ss"] * d["fs"]))
                b = int(round(d["fin"] * d["fs"]))
                bt, _ = apply_candidate(name, d, a, b)
                marks_win = [mk for mk in d["marks"] if a / d["fs"] <= mk <= b / d["fs"]]
                per.append(se.score_series(bt, marks_win, tol)["f1"])
            vals.append(np.median(per) if per else float("nan"))
        print(f"{name:<30}" + "".join(f"{v:>8.3f}" for v in vals))


def count_cadence_crux(data):
    """The coach-facing numbers: production paired-k2 cycle count + stroke-rate vs human."""
    print("\n=== COUNT + CADENCE crux: PRODUCTION paired-k2 vs human (annotated window) ===")
    print(f"{'when':<15}{'true_cyc':>9}{'pred_cyc':>9}{'dcount':>8}"
          f"{'hum_spm':>9}{'pred_spm':>9}{'spm_err%':>9}")
    dcs, spm_errs, exact = [], [], 0
    for d in data:
        if d["ss"] is None or d["fin"] is None or len(d["marks"]) < 4:
            continue
        a = int(round(d["ss"] * d["fs"]))
        b = int(round(d["fin"] * d["fs"]))
        marks_win = [mk for mk in d["marks"] if a / d["fs"] <= mk <= b / d["fs"]]
        cyc_bounds = marks_win[0::annot.marks_per_cycle("freestyle")]
        if len(cyc_bounds) < 2:
            continue
        true_cyc = len(cyc_bounds) - 1
        hum_spm = 60.0 / np.mean(np.diff(cyc_bounds))
        bt, _ = apply_candidate("PRODUCTION wavelet paired-k2", d, a, b)
        pred_cyc = max(len(bt) - 1, 0)
        pred_spm = 60.0 / np.mean(np.diff(bt)) if len(bt) >= 2 else float("nan")
        dcount = pred_cyc - true_cyc
        spm_err = 100.0 * (pred_spm - hum_spm) / hum_spm if np.isfinite(pred_spm) else float("nan")
        dcs.append(abs(dcount))
        if np.isfinite(spm_err):
            spm_errs.append(abs(spm_err))
        exact += int(dcount == 0)
        print(f"{d['when'][5:]:<15}{true_cyc:>9}{pred_cyc:>9}{dcount:>+8}"
              f"{hum_spm:>9.1f}{pred_spm:>9.1f}{spm_err:>+9.1f}")
    n = len(dcs)
    print(f"\n  sessions={n}  exact-count rate={exact}/{n}={exact/max(n,1):.0%}  "
          f"median|Δcount|={np.median(dcs):.1f}  median|SPM err|={np.median(spm_errs):.1f}%")


def main():
    data = load_freestyle()
    print(f"loaded {len(data)} annotated freestyle sessions")
    p1 = plot_overview(data)
    print("wrote", p1)

    # pick clean / medium / hard by n_marks spread
    ranked = sorted(data, key=lambda d: len(d["marks"]))
    picks = {"hard_fewmarks": ranked[0], "medium": ranked[len(ranked) // 2], "rich": ranked[-1]}
    for tag, d in picks.items():
        p = plot_candidates_for(d, tag)
        print("wrote", p)

    print_table(score_table(data, "annotated"), "ANNOTATED window")
    print_table(score_table(data, "production"), "PRODUCTION window")
    tolerance_sweep(data)
    count_cadence_crux(data)


if __name__ == "__main__":
    main()
