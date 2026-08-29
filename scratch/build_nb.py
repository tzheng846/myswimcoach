"""Assemble + execute the Phase 80 freestyle segmentation notebook."""
import nbformat as nbf
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell
from nbconvert.preprocessors import ExecutePreprocessor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".paul" / "phases" / "80-stroke-cycle-segmentation" / "freestyle_segmentation.ipynb"

cells = []
md = lambda s: cells.append(new_markdown_cell(s))
co = lambda s: cells.append(new_code_cell(s))

md("""# Phase 80 — Freestyle Stroke-Cycle Segmentation

Pull every **annotated freestyle** session, plot velocity + human arm-entry marks +
the annotated vs production swim windows, then apply every prior segmenter attempt
(the `tools/segmenter_candidates.py` set + the production paired-k2 wavelet + the shipped
learned detector) and score **count / cadence / F1 / offset**.

Ground-truth rule: one mark = **hand touches water** (arm entry); freestyle = **2 marks / cycle**.
The Phase-80 success metric is COUNT + CADENCE, not tight boundary placement — see `CONTEXT.md`.""")

co("""%matplotlib inline
import os, sys
from pathlib import Path

def _find_root(start):
    # Walk up until we hit the repo root (holds metrics.py + annotations.py), so the
    # notebook runs whether the kernel launches from the repo root or its own folder.
    p = Path(start).resolve()
    for cand in [p, *p.parents]:
        if (cand / "metrics.py").exists() and (cand / "annotations.py").exists():
            return cand
    raise RuntimeError("repo root not found from " + str(p))

ROOT = _find_root(Path.cwd())
# local supabase/ SQL dir shadows the installed supabase-py package: purge bare + root
# path entries, import supabase, then restore root + tools for the local modules.
sys.path = [p for p in sys.path if p not in ("", ".", str(ROOT))]
from dotenv import load_dotenv
from supabase import create_client
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

import metrics as m
import annotations as annot
import segmenter_eval as se
import segmenter_candidates as sc

load_dotenv(ROOT / ".env")
TOL = 0.15
print("marks/cycle for freestyle:", annot.marks_per_cycle("freestyle"))""")

md("## 1. Load annotated freestyle sessions (velocity profile + marks + phase boundaries)")

co('''def load_freestyle():
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
        out.append(dict(id=s["id"], when=(s.get("created_at") or "")[:19], fs=fs, vel=vel,
                        t=np.arange(vel.size) / fs, marks=marks,
                        ss=ph.get("stroke_start_s"), fin=ph.get("finish_s")))
    out.sort(key=lambda d: d["when"])
    return out

data = load_freestyle()
print(f"loaded {len(data)} annotated freestyle sessions")
for d in data:
    print(f"  {d['when'][5:]:<15} fs={d['fs']:.1f}  n_marks={len(d['marks']):>2}  "
          f"ss={d['ss']}  fin={d['fin']}")''')

md("""## 2. Overview — every session

Red = human arm-entry marks. Green band/lines = **annotated** swim window `[stroke_start_s, finish_s]`.
Blue dashed = **production** `detect_swim_window()` output (what actually ships).""")

co('''def plot_overview(data):
    n, ncol = len(data), 3
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
    fig.tight_layout()
    plt.show()

plot_overview(data)''')

md("""## 3. The candidate segmenters — the "attempts we tried before"

- **wavelet (unpaired)** — `segment_cycles_wavelet`, ~1 boundary / arm entry (Phase-59 headline framing).
- **PRODUCTION wavelet paired-k2** — what ships for freestyle: `_pair_boundaries(wavelet, 2)`, ~1 boundary / cycle.
- **peakpick** — `find_peaks` on 3s-detrended velocity.
- **R1/R2 snap** — wavelet boundaries snapped to nearest velocity-min / steepest-rise.
- **C1 matched filter**, **C3 autocorr grid** — non-CWT classical baselines.
- **learned (shipped weights)** — `_learned_boundaries` (logistic over 5 shape features).""")

co('''def _peakpick(t, v, fs):
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
    if not cycles:
        return []
    idx = [c["start_idx"] for c in cycles] + [cycles[-1]["end_idx"]]
    return [(a + i) / fs for i in idx]

def apply_candidate(name, d, a, b):
    va, tb = d["vel"][a:b], np.arange(b - a) / d["fs"]
    try:
        if name.startswith("C2"):
            cyc = sc.cand_trough_untrimmed(tb, va, d["fs"], full=d["vel"], offset=a)
        else:
            cyc = CANDS[name](tb, va, d["fs"])
    except Exception:
        cyc = None
    bt = cyc_bounds_time(cyc, a, d["fs"])
    return bt, len(bt)''')

md("### 3a. Candidate overlays on three sessions (few-marks / mid / rich)")

co('''def plot_candidates_for(d, tag):
    names = list(CANDS.keys())
    fig, axes = plt.subplots(len(names), 1, figsize=(11, 1.5 * len(names)), squeeze=False, sharex=True)
    i0, i1 = int(round(d["ss"] * d["fs"])), int(round(d["fin"] * d["fs"]))
    for r, name in enumerate(names):
        ax = axes[r][0]
        ax.plot(d["t"], d["vel"], lw=0.6, color="#999")
        ax.axvspan(d["ss"], d["fin"], color="tab:green", alpha=0.07)
        for mk in d["marks"]:
            ax.axvline(mk, color="tab:red", lw=0.8, alpha=0.6)
        bt, npred = apply_candidate(name, d, i0, i1)
        for x in bt:
            ax.axvline(x, color="tab:blue", lw=1.0, ls="--", alpha=0.9)
        s = se.score_series(bt, d["marks"], TOL)
        ax.set_ylabel(name, fontsize=7, rotation=0, ha="right", va="center")
        ax.set_title(f"n_pred={npred}  F1={s['f1']:.2f}  MAE={s['mae_s'] or float('nan'):.3f}"
                     f"  bias={s['bias_s'] or float('nan'):+.3f}s", fontsize=7, loc="right")
        ax.tick_params(labelsize=6)
    fig.suptitle(f"{tag}: {d['when'][5:]}  n_marks={len(d['marks'])}   "
                 f"red=human entry, blue--=predicted", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.99])
    plt.show()

ranked = sorted([d for d in data if d["ss"] is not None], key=lambda d: len(d["marks"]))
for tag, d in [("few-marks", ranked[0]), ("mid", ranked[len(ranked)//2]), ("rich", ranked[-1])]:
    plot_candidates_for(d, tag)''')

md("""## 4. Scoring

`F1`/`MAE`/`bias` at ±0.15 s vs arm-entry marks; `bnd/arm` = predicted boundaries per human arm entry
(≈1.0 = arm-entry rate, ≈0.5 = cycle rate). Compared on the **annotated** window and the
**production** window.""")

co('''def score_table(data, window="annotated"):
    rows = {}
    for d in data:
        if window == "annotated":
            if d["ss"] is None or d["fin"] is None:
                continue
            a, b = int(round(d["ss"] * d["fs"])), int(round(d["fin"] * d["fs"]))
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
            rows.setdefault(name, []).append(dict(f1=s["f1"], mae=s["mae_s"], bias=s["bias_s"],
                                                  ratio_arm=npred / n_arm if n_arm else np.nan))
    return rows

def print_table(rows, title):
    print(f"=== {title} (median over sessions) ===")
    print(f"{'candidate':<30}{'F1':>7}{'MAE':>8}{'bias':>9}{'bnd/arm':>9}{'n':>4}")
    for name, rs in rows.items():
        f1 = np.median([r["f1"] for r in rs])
        maes = [r["mae"] for r in rs if r["mae"] is not None]
        biases = [r["bias"] for r in rs if r["bias"] is not None]
        print(f"{name:<30}{f1:>7.3f}{(np.median(maes) if maes else float('nan')):>8.3f}"
              f"{(np.median(biases) if biases else float('nan')):>+9.3f}"
              f"{np.median([r['ratio_arm'] for r in rs]):>9.2f}{len(rs):>4}")

print_table(score_table(data, "annotated"), "ANNOTATED window")
print()
print_table(score_table(data, "production"), "PRODUCTION window")''')

md("### 4a. Tolerance sweep — *right events misplaced* vs *wrong events*")

co('''SWEEP = (0.05, 0.10, 0.15, 0.20, 0.30)
names = ["wavelet (unpaired, headline)", "peakpick", "R2 snap->steep rise", "PRODUCTION wavelet paired-k2"]
print(f"{'candidate':<30}" + "".join(f"{f'+/-{x}':>8}" for x in SWEEP))
for name in names:
    vals = []
    for tol in SWEEP:
        per = []
        for d in data:
            if d["ss"] is None or d["fin"] is None or len(d["marks"]) < 4:
                continue
            a, b = int(round(d["ss"] * d["fs"])), int(round(d["fin"] * d["fs"]))
            bt, _ = apply_candidate(name, d, a, b)
            marks_win = [mk for mk in d["marks"] if a / d["fs"] <= mk <= b / d["fs"]]
            per.append(se.score_series(bt, marks_win, tol)["f1"])
        vals.append(np.median(per) if per else float("nan"))
    print(f"{name:<30}" + "".join(f"{v:>8.3f}" for v in vals))''')

md("""## 5. The crux — COUNT + CADENCE (production paired-k2 vs human)

The coach-facing numbers: does the production segmenter get the **cycle count** and **stroke rate** right?
`coverage.ratio` (`segmenter_eval.coverage`) flags partially-labeled sessions — those are excluded from the
count/cadence aggregate because a half-labeled window makes a correct detection look like an error.""")

co('''print(f"{'when':<15}{'cov':>6}{'true_cyc':>9}{'pred_cyc':>9}{'dcount':>8}"
      f"{'hum_spm':>9}{'pred_spm':>9}{'spm_err%':>9}")
dcs, spm_errs, exact, used = [], [], 0, 0
for d in data:
    if d["ss"] is None or d["fin"] is None or len(d["marks"]) < 4:
        continue
    a, b = int(round(d["ss"] * d["fs"])), int(round(d["fin"] * d["fs"]))
    marks_win = [mk for mk in d["marks"] if a / d["fs"] <= mk <= b / d["fs"]]
    cov = se.coverage(marks_win, a / d["fs"], b / d["fs"])["ratio"]
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
    flag = "" if (cov and 0.7 <= cov <= 1.4) else "  <- partial-label, excluded"
    print(f"{d['when'][5:]:<15}{(cov or 0):>6.2f}{true_cyc:>9}{pred_cyc:>9}{dcount:>+8}"
          f"{hum_spm:>9.1f}{pred_spm:>9.1f}{spm_err:>+9.1f}{flag}")
    if cov and 0.7 <= cov <= 1.4:
        used += 1
        dcs.append(abs(dcount))
        if np.isfinite(spm_err):
            spm_errs.append(abs(spm_err))
        exact += int(dcount == 0)
print(f"\\n  well-labeled sessions used = {used}")
print(f"  exact-count rate = {exact}/{used} = {exact/max(used,1):.0%}")
print(f"  median |dcount|  = {np.median(dcs):.1f} cycles")
print(f"  median |SPM err| = {np.median(spm_errs):.1f} %")''')

md("""## Findings (2026-08-23)

1. **Cadence is already good, count is the weak spot.** Production paired-k2 gets the exact cycle count on
   only ~30% of sessions (typically ±1), yet median stroke-rate error is only ~4%. Matched-boundary **bias ≈ 0**
   — there is *no* systematic offset, so CONTEXT-D1's "constant offset is a success" case does not arise here;
   the error is missing/extra boundaries.
2. **The wavelet undercounts fast tempo.** The 08-22 sessions are a distinct high-cadence, high-amplitude
   regime; the ridge tracker's low-band bias locks onto a subharmonic and drops cycles (worst: −4). `peakpick`
   on detrended velocity beats the wavelet badly there (F1 0.19 → 0.81 on one).
3. **The production swim WINDOW is a large end-to-end error source.** `detect_swim_window` disagrees with the
   annotated window on many sessions (some spanning from t≈0 across the whole dive); annotated→production window
   halves cycle F1. Part of "improve cycle segmentation" is really gated by window detection (STATE items 11/12).
4. **Partial labels contaminate the corpus.** Several sessions have 3–8 marks over 6+ cycles; `coverage.ratio`
   must gate them out before any count/F1 aggregate.
5. **Tolerance sweep climbs steeply** (wavelet 0.09→0.82 across ±0.05→±0.30) with MAE≈0.07 on matched pairs —
   the events are roughly right, the misses are count, not gross misplacement.""")

nb = new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"display_name": "Python (swimnetics)", "language": "python", "name": "swimnetics"}
ep = ExecutePreprocessor(timeout=600, kernel_name="swimnetics")
# Execute from the notebook's OWN directory (the phase dir) to prove the root-finder +
# .env load work the way Jupyter will actually launch it, not just from the repo root.
ep.preprocess(nb, {"metadata": {"path": str(OUT.parent)}})
nbf.write(nb, str(OUT))
print("WROTE", OUT)
