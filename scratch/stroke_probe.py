"""Prototype: detect individual STROKES (arm entries), not cycles. Score vs marks directly."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:] = [p for p in sys.path if p not in ("", ".", str(ROOT))]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".paul" / "phases" / "80-stroke-cycle-segmentation"))
import numpy as np
from scipy.signal import find_peaks
import metrics as m, segmenter_eval as se
import visualize_freestyle_seg as vz


def strokes_peakpick(vel, t, fs):
    det = np.nan_to_num(m._detrend_for_cwt(vel, fs))
    per = m._estimate_period(t, vel) or 1.0
    pk, _ = find_peaks(det, distance=max(1, int(0.45 * per * fs)),
                       prominence=0.25 * float(np.percentile(np.abs(det), 95)))
    return pk / fs


def strokes_wavelet(vel, t, fs, bias):
    rf, _ = m._cwt_ridge(vel, fs, low_band_bias=bias)
    if rf is None:
        return np.array([])
    phase = np.concatenate(([0.0], np.cumsum(rf[:-1] * np.diff(t))))
    out, n = [], 1
    for i in range(1, len(phase)):
        if phase[i - 1] < n <= phase[i]:
            out.append(i); n += 1
    return np.array(out) / fs


DET = {
    "wavelet bias=0.5 (shipped ridge)": lambda v, t, fs: strokes_wavelet(v, t, fs, 0.5),
    "wavelet bias=0.0 (no low-band)":   lambda v, t, fs: strokes_wavelet(v, t, fs, 0.0),
    "peakpick":                         strokes_peakpick,
}

data = vz.load_freestyle()
print(f"{len(data)} sessions\n")
agg = {k: dict(dc=[], err=[], exact=0, n=0, f1=[]) for k in DET}
hdr = f"{'swimmer':<7}{'when':<12}{'true':>5}" + "".join(f"{k.split()[0][:8]:>10}" for k in DET)
print(hdr)
for d in data:
    a, b = int(round(d["ss"] * d["fs"])), int(round(d["fin"] * d["fs"]))
    marks = [mk for mk in d["marks"] if a / d["fs"] <= mk <= b / d["fs"]]
    cov = se.coverage(marks, a / d["fs"], b / d["fs"])["ratio"]
    if not (cov and 0.7 <= cov <= 1.4) or len(marks) < 4:
        continue
    true_n = len(marks)
    va, tb = d["vel"][a:b], np.arange(b - a) / d["fs"]
    row = f"{d['swimmer']:<7}{d['when'][5:16]:<12}{true_n:>5}"
    for k, fn in DET.items():
        st = fn(va, tb, d["fs"]) + a / d["fs"]
        n = len(st)
        row += f"{n:>10}"
        sc = se.score_series(list(st), marks, 0.15)
        agg[k]["dc"].append(abs(n - true_n)); agg[k]["n"] += 1
        agg[k]["exact"] += int(n == true_n); agg[k]["f1"].append(sc["f1"])
        if n >= 2 and true_n >= 2:
            tr = 60.0 / np.mean(np.diff(marks)); pr = 60.0 / np.mean(np.diff(sorted(st)))
            agg[k]["err"].append(abs(100 * (pr - tr) / tr))
    print(row)

print(f"\n{'detector':<34}{'exact%':>8}{'med|dN|':>9}{'medErr%':>9}{'medF1':>8}")
for k, s in agg.items():
    print(f"{k:<34}{s['exact']/max(s['n'],1):>7.0%}{np.median(s['dc']):>9.1f}"
          f"{np.median(s['err']):>9.1f}{np.median(s['f1']):>8.2f}")
