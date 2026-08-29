"""
Phase 80 — visualize the freestyle stroke-cycle segmentation problem.

WHAT'S WRONG (this script shows it):
  The production freestyle segmenter (CWT-ridge wavelet, paired k=2) gets the CADENCE
  about right (~4% stroke-rate error) but the CYCLE COUNT wrong on ~70% of sessions
  (typically +/-1), and it fails hardest on the fast swimmer (Max) it was never tuned
  on -- the ridge's low-band bias locks onto a subharmonic and DROPS cycles.

Pulls every annotated freestyle session from Supabase (service key, via the repo .env),
labels each by swimmer, and renders three figures + a count/cadence table.

RUN (in your conda env):
    conda activate mySwimCoach
    python .paul/phases/80-stroke-cycle-segmentation/visualize_freestyle_seg.py

    # or without activating:
    C:/Users/TonyZheng/miniconda3/envs/mySwimCoach/python.exe \
        .paul/phases/80-stroke-cycle-segmentation/visualize_freestyle_seg.py

Options:
    --no-show     save PNGs only, don't open windows (headless)
    --candidates  also draw the full prior-attempts overlay on the worst session

Dependencies: numpy scipy pandas matplotlib PyWavelets supabase python-dotenv
(all present in mySwimCoach; no scikit-learn needed).
"""
import argparse
import os
import sys
from pathlib import Path


# ── locate repo root (holds metrics.py) so this runs from any cwd ──────────────
def _find_root(start):
    p = Path(start).resolve()
    for cand in [p, *p.parents]:
        if (cand / "metrics.py").exists() and (cand / "annotations.py").exists():
            return cand
    raise RuntimeError("repo root (with metrics.py) not found from " + str(p))


ROOT = _find_root(Path(__file__).parent)
HERE = Path(__file__).resolve().parent
FIGS = HERE / "figs"
FIGS.mkdir(exist_ok=True)

# Windows consoles default to cp1252 and choke on the chars below; force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# The local supabase/ SQL dir shadows the installed supabase-py package: purge bare +
# root path entries, import supabase, then restore root + tools for the local modules.
sys.path = [p for p in sys.path if p not in ("", ".", str(ROOT))]
from dotenv import load_dotenv          # noqa: E402
from supabase import create_client      # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import numpy as np                       # noqa: E402
import matplotlib.pyplot as plt          # noqa: E402
from scipy.signal import find_peaks      # noqa: E402

import metrics as m                      # noqa: E402
import annotations as annot              # noqa: E402
import segmenter_eval as se              # noqa: E402
import segmenter_candidates as sc        # noqa: E402  (no sklearn at import time)

load_dotenv(ROOT / ".env")
TOL = 0.15
SWIMMER_COLOR = {"Tony": "tab:green", "Leo": "tab:orange", "Max": "tab:red"}


# ── data ───────────────────────────────────────────────────────────────────────
def load_freestyle():
    url, key = os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not found in .env at " + str(ROOT / ".env"))
    sb = create_client(url, key)
    anns = (sb.table("session_annotations")
            .select("session_id, phases, stroke_marks_s").execute().data) or []
    ids = [a["session_id"] for a in anns]
    rows = (sb.table("sessions")
            .select("id, stroke_type, created_at, sample_rate_hz, athlete_id, velocity_profile")
            .in_("id", ids).execute().data) or []
    by = {r["id"]: r for r in rows}
    aids = sorted({r.get("athlete_id") for r in rows if r.get("athlete_id")})
    ath = (sb.table("athletes").select("id, name").in_("id", aids).execute().data) or []
    name_of = {a["id"]: a.get("name") for a in ath}
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
            id=s["id"], when=(s.get("created_at") or "")[:19],
            swimmer=name_of.get(s.get("athlete_id"), "?"),
            fs=fs, vel=vel, t=np.arange(vel.size) / fs, marks=marks,
            ss=ph.get("stroke_start_s"), fin=ph.get("finish_s")))
    out.sort(key=lambda d: (d["swimmer"], d["when"]))
    return out


# ── segmenters ──────────────────────────────────────────────────────────────────
def _peakpick(t, v, fs):
    det = np.nan_to_num(m._detrend_for_cwt(v, fs))
    per = m._estimate_period(t, v) or 1.0
    pk, _ = find_peaks(det, distance=max(1, int(0.45 * per * fs)),
                       prominence=0.25 * float(np.percentile(np.abs(det), 95)))
    return sc._cycles_from_bounds(v, pk)


CANDS = {
    "wavelet (unpaired)": lambda t, v, fs: m.segment_cycles_wavelet(t, v),
    "PRODUCTION wavelet paired-k2": lambda t, v, fs: m._pair_boundaries(m.segment_cycles_wavelet, 2)(t, v),
    "peakpick": _peakpick,
    "R1 snap->vel min": sc.make_snap("min"),
    "R2 snap->steep rise": sc.make_snap("rise"),
    "C1 matched filter": sc.make_matched_filter(),
    "C3 autocorr grid": sc.make_autocorr(),
    "learned (shipped weights)": lambda t, v, fs: m._learned_boundaries(t, v),
}


def _win(d):
    return int(round(d["ss"] * d["fs"])), int(round(d["fin"] * d["fs"]))


def boundaries_time(name, d):
    """Absolute boundary times (s) for a candidate on the annotated window."""
    a, b = _win(d)
    va, tb = d["vel"][a:b], np.arange(b - a) / d["fs"]
    try:
        cyc = CANDS[name](tb, va, d["fs"])
    except Exception:
        cyc = None
    if not cyc:
        return []
    idx = [c["start_idx"] for c in cyc] + [cyc[-1]["end_idx"]]
    return [(a + i) / d["fs"] for i in idx]


def stats(d):
    """Per-session truth vs production paired-k2: cycle count + stroke rate + coverage."""
    a, b = _win(d)
    marks_win = [mk for mk in d["marks"] if a / d["fs"] <= mk <= b / d["fs"]]
    cov = se.coverage(marks_win, a / d["fs"], b / d["fs"])["ratio"]
    cyc_bounds = marks_win[0::annot.marks_per_cycle("freestyle")]
    if len(cyc_bounds) < 2:
        return None
    true_cyc = len(cyc_bounds) - 1
    hum_spm = 60.0 / np.mean(np.diff(cyc_bounds))
    bt = boundaries_time("PRODUCTION wavelet paired-k2", d)
    pred_cyc = max(len(bt) - 1, 0)
    pred_spm = 60.0 / np.mean(np.diff(bt)) if len(bt) >= 2 else float("nan")
    return dict(cov=cov, human_bounds=cyc_bounds, prod_bounds=bt,
                true_cyc=true_cyc, pred_cyc=pred_cyc, dcount=pred_cyc - true_cyc,
                hum_spm=hum_spm, pred_spm=pred_spm,
                spm_err=100.0 * (pred_spm - hum_spm) / hum_spm if np.isfinite(pred_spm) else float("nan"),
                well_labeled=bool(cov and 0.7 <= cov <= 1.4), n_marks=len(marks_win))


# ── STROKE detection (the marks ARE strokes; a cycle = 2 strokes) ────────────────
# Detect individual arm entries directly instead of cycles, so pairing (which halves
# the count and compounds the fast-tempo undercount) is never in the loop. The winning
# detector is the wavelet ridge with the low-band bias turned OFF.
def strokes_wavelet(d, bias):
    a, b = _win(d)
    vel, t = d["vel"][a:b], np.arange(b - a) / d["fs"]
    rf, _ = m._cwt_ridge(vel, d["fs"], low_band_bias=bias)
    if rf is None:
        return []
    phase = np.concatenate(([0.0], np.cumsum(rf[:-1] * np.diff(t))))
    out, n = [], 1
    for i in range(1, len(phase)):
        if phase[i - 1] < n <= phase[i]:
            out.append(i)
            n += 1
    return [(a + i) / d["fs"] for i in out]


def strokes_peakpick(d):
    a, b = _win(d)
    vel, t = d["vel"][a:b], np.arange(b - a) / d["fs"]
    det = np.nan_to_num(m._detrend_for_cwt(vel, d["fs"]))
    per = m._estimate_period(t, vel) or 1.0
    pk, _ = find_peaks(det, distance=max(1, int(0.45 * per * d["fs"])),
                       prominence=0.25 * float(np.percentile(np.abs(det), 95)))
    return [(a + i) / d["fs"] for i in pk]


STROKE_DET = {
    "shipped ridge (bias 0.5)": lambda d: strokes_wavelet(d, 0.5),
    "no low-band (bias 0.0)":   lambda d: strokes_wavelet(d, 0.0),
    "peakpick":                 strokes_peakpick,
}


def stroke_stats(d):
    """True stroke marks + each detector's stroke count / rate, on the annotated window."""
    a, b = _win(d)
    marks = [mk for mk in d["marks"] if a / d["fs"] <= mk <= b / d["fs"]]
    cov = se.coverage(marks, a / d["fs"], b / d["fs"])["ratio"]
    if len(marks) < 4:
        return None
    true_rate = 60.0 / np.mean(np.diff(marks)) if len(marks) >= 2 else float("nan")
    out = dict(marks=marks, true_n=len(marks), true_rate=true_rate,
               cov=cov, well_labeled=bool(cov and 0.7 <= cov <= 1.4), det={})
    for name, fn in STROKE_DET.items():
        st = sorted(fn(d))
        rate = 60.0 / np.mean(np.diff(st)) if len(st) >= 2 else float("nan")
        out["det"][name] = dict(times=st, n=len(st), rate=rate)
    return out


# ── figures ──────────────────────────────────────────────────────────────────────
def fig_overview(data):
    n, ncol = len(data), 3
    nrow = (n + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(5.2 * ncol, 2.3 * nrow), squeeze=False)
    for k, d in enumerate(data):
        ax = axes[k // ncol][k % ncol]
        ax.plot(d["t"], d["vel"], lw=0.6, color="#333")
        for mk in d["marks"]:
            ax.axvline(mk, color="tab:red", lw=0.7, alpha=0.6)
        if d["ss"] is not None and d["fin"] is not None:
            ax.axvspan(d["ss"], d["fin"], color=SWIMMER_COLOR.get(d["swimmer"], "gray"), alpha=0.12)
        ax.set_title(f"{d['swimmer']}  {d['when'][5:16]}  marks={len(d['marks'])}", fontsize=8)
        ax.tick_params(labelsize=6)
    for k in range(n, nrow * ncol):
        axes[k // ncol][k % ncol].axis("off")
    fig.suptitle("All annotated freestyle — velocity + human arm-entry marks (red); band tint = swimmer",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    return _finish(fig, "01_overview.png")


def fig_problem(data):
    """One example per swimmer: human cycle boundaries vs the production segmenter's."""
    ex = []
    for name in ["Tony", "Leo", "Max"]:
        cands = [d for d in data if d["swimmer"] == name and (st := stats(d)) and st["well_labeled"]]
        if not cands:
            continue
        # pick the median-cadence session for Tony/Leo, the WORST-miscount for Max
        if name == "Max":
            ex.append(max(cands, key=lambda d: abs(stats(d)["dcount"])))
        else:
            ex.append(sorted(cands, key=lambda d: stats(d)["hum_spm"])[len(cands) // 2])
    fig, axes = plt.subplots(len(ex), 1, figsize=(11, 2.6 * len(ex)), squeeze=False)
    for r, d in enumerate(ex):
        ax = axes[r][0]
        st = stats(d)
        a, b = _win(d)
        ax.plot(d["t"], d["vel"], lw=0.7, color="#666")
        ax.axvspan(d["ss"], d["fin"], color="#eee", alpha=0.6)
        for x in st["human_bounds"]:
            ax.axvline(x, color="tab:green", lw=1.6)
        for x in st["prod_bounds"]:
            ax.axvline(x, color="tab:blue", lw=1.4, ls="--")
        ax.set_xlim(max(0, d["ss"] - 1.5), d["fin"] + 1.5)
        col = SWIMMER_COLOR.get(d["swimmer"], "k")
        ax.set_title(f"{d['swimmer']} — human {st['true_cyc']} cycles ({st['hum_spm']:.0f} spm)  vs  "
                     f"production {st['pred_cyc']} cycles ({st['pred_spm']:.0f} spm)   "
                     f"Δcount={st['dcount']:+d}, rate err={st['spm_err']:+.0f}%",
                     fontsize=10, color=col)
        ax.tick_params(labelsize=7)
        ax.set_ylabel("vel (m/s)", fontsize=8)
    axes[-1][0].set_xlabel("time (s)", fontsize=9)
    fig.suptitle("THE PROBLEM — green = human cycle boundaries, blue dashed = production segmenter.\n"
                 "Cadence tracks; the COUNT drifts, worst on the fast swimmer (Max).", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return _finish(fig, "02_the_problem.png")


def fig_summary(data):
    rows = [(d, stats(d)) for d in data]
    rows = [(d, s) for d, s in rows if s and s["well_labeled"]]
    rows.sort(key=lambda r: (r[0]["swimmer"], r[1]["hum_spm"]))
    labels = [f"{d['swimmer'][0]}·{s['hum_spm']:.0f}" for d, s in rows]
    colors = [SWIMMER_COLOR.get(d["swimmer"], "gray") for d, s in rows]
    x = np.arange(len(rows))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    ax1.bar(x, [s["dcount"] for d, s in rows], color=colors)
    ax1.axhline(0, color="k", lw=0.8)
    ax1.set_ylabel("cycle-count error\n(pred − true)")
    ax1.set_title("Count error and stroke-rate error per session, ordered by swimmer then cadence")
    ax2.bar(x, [abs(s["spm_err"]) for d, s in rows], color=colors)
    ax2.set_ylabel("|stroke-rate err| (%)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=90, fontsize=7)
    ax2.set_xlabel("session  (swimmer · human spm)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in SWIMMER_COLOR.values()]
    ax1.legend(handles, SWIMMER_COLOR.keys(), fontsize=8, loc="upper left")
    fig.tight_layout()
    return _finish(fig, "03_summary_by_swimmer.png")


def fig_candidates(d):
    names = list(CANDS.keys())
    fig, axes = plt.subplots(len(names), 1, figsize=(11, 1.5 * len(names)), squeeze=False, sharex=True)
    for r, name in enumerate(names):
        ax = axes[r][0]
        ax.plot(d["t"], d["vel"], lw=0.6, color="#999")
        ax.axvspan(d["ss"], d["fin"], color="tab:green", alpha=0.07)
        for mk in d["marks"]:
            ax.axvline(mk, color="tab:red", lw=0.8, alpha=0.6)
        bt = boundaries_time(name, d)
        for x in bt:
            ax.axvline(x, color="tab:blue", lw=1.0, ls="--", alpha=0.9)
        s = se.score_series(bt, d["marks"], TOL)
        ax.set_ylabel(name, fontsize=7, rotation=0, ha="right", va="center")
        ax.set_title(f"n_pred={len(bt)}  F1={s['f1']:.2f}  MAE={s['mae_s'] or float('nan'):.3f}"
                     f"  bias={s['bias_s'] or float('nan'):+.3f}s", fontsize=7, loc="right")
        ax.tick_params(labelsize=6)
    fig.suptitle(f"Prior attempts on {d['swimmer']} {d['when'][5:16]} — red=human entry, blue--=predicted",
                 fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    return _finish(fig, "04_candidates_worst.png")


def _example_per_swimmer(data):
    """One session each: Tony/Leo at median cadence, Max at worst stroke-miscount."""
    ex = []
    for name in ["Tony", "Leo", "Max"]:
        cs = [d for d in data if d["swimmer"] == name
              and (s := stroke_stats(d)) and s["well_labeled"]]
        if not cs:
            continue
        if name == "Max":
            ex.append(max(cs, key=lambda d: abs(stroke_stats(d)["det"]["shipped ridge (bias 0.5)"]["n"]
                                               - stroke_stats(d)["true_n"])))
        else:
            ex.append(sorted(cs, key=lambda d: stroke_stats(d)["true_rate"])[len(cs) // 2])
    return ex


def fig_strokes(data):
    """The fix: human strokes vs the shipped ridge vs the no-low-band ridge."""
    ex = _example_per_swimmer(data)
    fig, axes = plt.subplots(len(ex), 1, figsize=(11, 2.7 * len(ex)), squeeze=False)
    for r, d in enumerate(ex):
        ax = axes[r][0]
        s = stroke_stats(d)
        ax.plot(d["t"], d["vel"], lw=0.7, color="#666")
        ax.axvspan(d["ss"], d["fin"], color="#f2f2f2")
        for mk in s["marks"]:
            ax.axvline(mk, color="tab:red", lw=1.5)
        for x in s["det"]["shipped ridge (bias 0.5)"]["times"]:
            ax.axvline(x, color="tab:blue", lw=1.2, ls=":")
        for x in s["det"]["no low-band (bias 0.0)"]["times"]:
            ax.axvline(x, color="tab:green", lw=1.2, ls="--")
        ax.set_xlim(max(0, d["ss"] - 1.0), d["fin"] + 1.0)
        sh = s["det"]["shipped ridge (bias 0.5)"]["n"]
        nb = s["det"]["no low-band (bias 0.0)"]["n"]
        ax.set_title(f"{d['swimmer']} — human {s['true_n']} strokes ({s['true_rate']:.0f} spm)   "
                     f"shipped ridge {sh}   no-low-band {nb}",
                     fontsize=10, color=SWIMMER_COLOR.get(d["swimmer"], "k"))
        ax.set_ylabel("vel (m/s)", fontsize=8)
        ax.tick_params(labelsize=7)
    axes[-1][0].set_xlabel("time (s)", fontsize=9)
    fig.suptitle("DETECTING STROKES — red = human arm entries, blue dotted = shipped ridge (bias 0.5), "
                 "green dashed = no low-band (bias 0.0).\nDropping the low-band bias recovers Max's "
                 "missing strokes.", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return _finish(fig, "05_detecting_strokes.png")


def _finish(fig, fname):
    p = FIGS / fname
    fig.savefig(p, dpi=115)
    print("  wrote", p.relative_to(ROOT))
    return fig


# ── text summary ─────────────────────────────────────────────────────────────────
def print_table(data):
    print("\nCOUNT + CADENCE — production wavelet paired-k2 vs human (annotated window)")
    print(f"{'swimmer':<8}{'when':<14}{'cov':>6}{'true':>6}{'pred':>6}{'dcnt':>6}"
          f"{'hum_spm':>9}{'prd_spm':>9}{'err%':>7}")
    dcs, errs, exact, used = [], [], 0, 0
    for d in data:
        s = stats(d)
        if not s:
            continue
        flag = "" if s["well_labeled"] else "  (partial-label, excluded)"
        print(f"{d['swimmer']:<8}{d['when'][5:16]:<14}{(s['cov'] or 0):>6.2f}"
              f"{s['true_cyc']:>6}{s['pred_cyc']:>6}{s['dcount']:>+6}"
              f"{s['hum_spm']:>9.1f}{s['pred_spm']:>9.1f}{s['spm_err']:>+7.1f}{flag}")
        if s["well_labeled"]:
            used += 1
            dcs.append(abs(s["dcount"]))
            exact += int(s["dcount"] == 0)
            if np.isfinite(s["spm_err"]):
                errs.append(abs(s["spm_err"]))
    print(f"\n  well-labeled sessions = {used}"
          f"   exact-count = {exact}/{used} = {exact/max(used,1):.0%}"
          f"   median |dcount| = {np.median(dcs):.1f}"
          f"   median |rate err| = {np.median(errs):.1f}%")
    print("  => cadence is fine (~4%); the COUNT is the failure, concentrated on Max (fast).")


def print_stroke_table(data):
    print("\nSTROKE detection — count vs human (marks ARE strokes; annotated window)")
    names = list(STROKE_DET)
    print(f"{'swimmer':<7}{'when':<12}{'true':>5}" + "".join(f"{n.split(' (')[0][:12]:>14}" for n in names))
    agg = {n: dict(dc=[], err=[], exact=0, tot=0) for n in names}
    for d in data:
        s = stroke_stats(d)
        if not s or not s["well_labeled"]:
            continue
        row = f"{d['swimmer']:<7}{d['when'][5:16]:<12}{s['true_n']:>5}"
        for n in names:
            dn = s["det"][n]
            row += f"{dn['n']:>14}"
            agg[n]["dc"].append(abs(dn["n"] - s["true_n"]))
            agg[n]["exact"] += int(dn["n"] == s["true_n"])
            agg[n]["tot"] += 1
            if np.isfinite(dn["rate"]) and np.isfinite(s["true_rate"]):
                agg[n]["err"].append(abs(100 * (dn["rate"] - s["true_rate"]) / s["true_rate"]))
        print(row)
    print(f"\n{'detector':<26}{'exact%':>8}{'med|dN|':>9}{'med rate err%':>15}")
    for n in names:
        a = agg[n]
        print(f"{n:<26}{a['exact']/max(a['tot'],1):>7.0%}"
              f"{np.median(a['dc']):>9.1f}{np.median(a['err']):>15.1f}")
    print("  => detecting strokes with the low-band bias OFF gives the best count; a cycle = 2 strokes.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--no-show", action="store_true", help="save PNGs only, no windows")
    ap.add_argument("--candidates", action="store_true", help="also draw prior-attempts overlay")
    args = ap.parse_args()

    print("loading annotated freestyle from Supabase ...")
    data = load_freestyle()
    from collections import Counter
    print(f"loaded {len(data)} sessions: {dict(Counter(d['swimmer'] for d in data))}")

    fig_overview(data)
    fig_problem(data)
    fig_summary(data)
    fig_strokes(data)
    if args.candidates:
        worst = max((d for d in data if stats(d) and stats(d)["well_labeled"]),
                    key=lambda d: abs(stats(d)["dcount"]))
        fig_candidates(worst)

    print_table(data)
    print_stroke_table(data)
    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
