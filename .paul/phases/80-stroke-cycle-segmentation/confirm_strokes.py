"""
Phase 80 — CONFIRM the winning stroke detector on EVERY freestyle session.

The doc reports the bias=0.0 wavelet ridge as the best-scoring stroke detector
(exact-count 38%, median |dN| 1.0, rate err 3.2%). Aggregate numbers can hide
per-session garbage that averages out, so this script renders ALL sessions and
color-codes where the detector agrees / drops / adds a stroke.

D5 is enforced by construction: every panel is clamped to the HUMAN annotated
window [stroke_start_s, finish_s] (via vz._win), so the upstream swim-window
detector cannot contaminate this interior-segmenter test.

Detector under test  : wavelet ridge, low_band_bias = 0.0   ("the method")
Reference (faint)    : shipped ridge, low_band_bias = 0.5   (to see the change)
Ground truth         : human arm-entry marks (red)

Matching is the same optimal assignment used for scoring (segmenter_eval.match_series,
tol=0.15 s):
    green tick under a detection  = matched a human mark
    magenta v under a detection   = EXTRA (false positive, detector over-counts)
    red o above a mark            = MISSED (detector dropped that stroke)

RUN:
    C:/Users/TonyZheng/miniconda3/envs/mySwimCoach/python.exe \
        .paul/phases/80-stroke-cycle-segmentation/confirm_strokes.py --no-show
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))          # so we can import the sibling visualize module

import numpy as np                      # noqa: E402
import matplotlib.pyplot as plt         # noqa: E402

import visualize_freestyle_seg as vz    # noqa: E402  (sets up sys.path, loads .env, imports metrics/annotations/segmenter_eval)
import segmenter_eval as se             # noqa: E402

FIGS = HERE / "figs"
FIGS.mkdir(exist_ok=True)
TOL = vz.TOL                            # 0.15 s
BIAS = 0.0                              # the detector under test
SWIMMER_COLOR = vz.SWIMMER_COLOR


def analyze(d):
    """Detected strokes (bias 0.0 + shipped 0.5) vs human marks, on the annotated window."""
    if d["ss"] is None or d["fin"] is None:
        return None
    a, b = vz._win(d)
    lo, hi = a / d["fs"], b / d["fs"]
    marks = [mk for mk in d["marks"] if lo <= mk <= hi]
    if len(marks) < 4:
        return None
    det0 = sorted(vz.strokes_wavelet(d, BIAS))      # the method
    det5 = sorted(vz.strokes_wavelet(d, 0.5))       # shipped, for reference
    pairs, extra, missed = se.match_series(det0, marks, TOL)
    matched = [p for p, _, _ in pairs]
    cov = se.coverage(marks, lo, hi)["ratio"]
    true_rate = 60.0 / np.mean(np.diff(marks)) if len(marks) >= 2 else float("nan")
    det_rate = 60.0 / np.mean(np.diff(det0)) if len(det0) >= 2 else float("nan")
    return dict(
        lo=lo, hi=hi, marks=marks, det0=det0, det5=det5,
        matched=matched, extra=extra, missed=missed,
        true_n=len(marks), det_n=len(det0), dcount=len(det0) - len(marks),
        true_rate=true_rate, det_rate=det_rate,
        rate_err=100 * (det_rate - true_rate) / true_rate if np.isfinite(det_rate) else float("nan"),
        cov=cov, well=bool(cov and 0.7 <= cov <= 1.4),
    )


def _title_color(r):
    if not r["well"]:
        return "#999"
    return {0: "tab:green", 1: "tab:orange"}.get(abs(r["dcount"]), "tab:red")


def fig_all(data):
    rows = [(d, analyze(d)) for d in data]
    rows = [(d, r) for d, r in rows if r]
    ncol = 3
    nrow = (len(rows) + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(6.0 * ncol, 2.7 * nrow),
                             squeeze=False, constrained_layout=True)
    for k, (d, r) in enumerate(rows):
        ax = axes[k // ncol][k % ncol]
        ax.plot(d["t"], d["vel"], lw=0.6, color="#555")
        ax.axvspan(r["lo"], r["hi"], color=SWIMMER_COLOR.get(d["swimmer"], "gray"), alpha=0.06)
        ymin, ymax = float(np.nanmin(d["vel"])), float(np.nanmax(d["vel"]))
        span = ymax - ymin or 1.0
        # human marks (red) + shipped ridge (faint gray dotted, reference only)
        for x in r["det5"]:
            ax.axvline(x, color="#bbb", lw=0.8, ls=":", alpha=0.9)
        for mk in r["marks"]:
            ax.axvline(mk, color="tab:red", lw=0.9, alpha=0.65)
        # the detector under test (bias 0.0): blue dashed
        for x in r["det0"]:
            ax.axvline(x, color="tab:blue", lw=0.9, ls="--", alpha=0.85)
        # agreement markers
        y_match = ymin - 0.06 * span
        y_extra = ymin - 0.14 * span
        y_miss = ymax + 0.08 * span
        ax.plot(r["matched"], [y_match] * len(r["matched"]), "o", ms=3.5,
                color="tab:green", clip_on=False)
        ax.plot(r["extra"], [y_extra] * len(r["extra"]), "v", ms=5,
                color="magenta", clip_on=False)
        ax.plot(r["missed"], [y_miss] * len(r["missed"]), "o", ms=6, mfc="none",
                mec="tab:red", mew=1.4, clip_on=False)
        ax.set_xlim(max(0, r["lo"] - 0.8), r["hi"] + 0.8)
        ax.set_ylim(ymin - 0.2 * span, ymax + 0.2 * span)
        tag = "" if r["well"] else "  (partial-label)"
        ax.set_title(
            f"{d['swimmer']} {d['when'][5:16]}   T={r['true_n']} D={r['det_n']} "
            f"({r['dcount']:+d})   miss={len(r['missed'])} extra={len(r['extra'])}   "
            f"err={r['rate_err']:+.0f}%{tag}",
            fontsize=8, color=_title_color(r))
        ax.tick_params(labelsize=6)
    for k in range(len(rows), nrow * ncol):
        axes[k // ncol][k % ncol].axis("off")

    # aggregate over well-labeled, to reconcile against the doc's 38% / 1.0 / 3.2%
    well = [r for _, r in rows if r["well"]]
    exact = sum(1 for r in well if r["dcount"] == 0)
    med_dn = np.median([abs(r["dcount"]) for r in well]) if well else float("nan")
    med_err = np.median([abs(r["rate_err"]) for r in well if np.isfinite(r["rate_err"])]) if well else float("nan")
    fig.suptitle(
        "CONFIRM — bias=0.0 ridge (blue dashed) vs human marks (red), clamped to the human window.\n"
        "green dot = matched   magenta v = extra/over-count   red o = missed/dropped   "
        "gray dotted = shipped bias=0.5 (reference).   "
        f"Well-labeled: exact-count {exact}/{len(well)} = {exact/max(len(well),1):.0%}, "
        f"median |dN| {med_dn:.1f}, median |rate err| {med_err:.1f}%.",
        fontsize=10)
    p = FIGS / "06_confirm_all_strokes.png"
    fig.savefig(p, dpi=115)
    print("  wrote", p)
    return fig


def print_table(data):
    print("\nPER-SESSION — bias=0.0 stroke detector vs human marks (annotated window, tol=0.15s)")
    print(f"{'swimmer':<7}{'when':<12}{'cov':>6}{'true':>6}{'det':>5}{'dN':>5}"
          f"{'miss':>6}{'extra':>6}{'trueSPM':>9}{'detSPM':>8}{'err%':>7}")
    well = []
    for d in data:
        r = analyze(d)
        if not r:
            continue
        flag = "" if r["well"] else "  (partial, excl)"
        print(f"{d['swimmer']:<7}{d['when'][5:16]:<12}{(r['cov'] or 0):>6.2f}"
              f"{r['true_n']:>6}{r['det_n']:>5}{r['dcount']:>+5}"
              f"{len(r['missed']):>6}{len(r['extra']):>6}"
              f"{r['true_rate']:>9.1f}{r['det_rate']:>8.1f}{r['rate_err']:>+7.1f}{flag}")
        if r["well"]:
            well.append(r)
    if well:
        exact = sum(1 for r in well if r["dcount"] == 0)
        within1 = sum(1 for r in well if abs(r["dcount"]) <= 1)
        med_dn = np.median([abs(r["dcount"]) for r in well])
        med_err = np.median([abs(r["rate_err"]) for r in well if np.isfinite(r["rate_err"])])
        print(f"\n  well-labeled = {len(well)}   exact-count = {exact}/{len(well)} = {exact/len(well):.0%}"
              f"   within +-1 = {within1}/{len(well)} = {within1/len(well):.0%}"
              f"   median |dN| = {med_dn:.1f}   median |rate err| = {med_err:.1f}%")
        # per-swimmer count-bias tell
        print("\n  count error (det - true) by swimmer:")
        by = {}
        for d in data:
            r = analyze(d)
            if r and r["well"]:
                by.setdefault(d["swimmer"], []).append(r["dcount"])
        for sw, xs in sorted(by.items()):
            print(f"    {sw:<6} n={len(xs):>2}  dcounts={sorted(xs)}  mean={np.mean(xs):+.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-show", action="store_true")
    args = ap.parse_args()
    print("loading annotated freestyle from Supabase ...")
    data = vz.load_freestyle()
    from collections import Counter
    print(f"loaded {len(data)} sessions: {dict(Counter(d['swimmer'] for d in data))}")
    fig_all(data)
    print_table(data)
    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
