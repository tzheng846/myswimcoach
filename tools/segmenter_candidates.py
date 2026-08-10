"""Candidate stroke-cycle segmenters, scored leave-one-session-out (Phase 59-04).

RESEARCH ONLY. Nothing here is imported by metrics.py. Candidates live in tools/ so a dead
end costs nothing; 59-05 ships whatever wins by editing SEGMENTER_BY_STROKE.

WHAT THIS IS FOR
----------------
`segment_cycles_wavelet` is the piece the annotation effort exists to fix, and it is the one
part of the pipeline Phase 59 has not touched. Measured against ground truth on the
ANNOTATED window (entries framing, F1 @±0.15 s): freestyle 0.46, butterfly 0.31,
breaststroke 0.23. Through the production window it is worse still. Roughly one boundary in
four lands within 150 ms of a human mark.

WHY LEAVE-ONE-SESSION-OUT IS NOT OPTIONAL
-----------------------------------------
Phase 59-03 tuned a window detector against 12 annotated sessions, passed its gate on those
same 12, and then collapsed on 13 of 36 real ones. Any candidate here with a fitted or
hand-tuned constant can repeat that exactly. So every such candidate is scored LOSO — fit on
N-1 sessions, score the held-out one, rotate — and the in-sample number is printed beside it.
A large gap between them IS the finding.

THE FOUR FAMILIES
-----------------
  refinement  R1 R2   keep a coarse rate estimate, fix WHERE the boundary lands. The
                      F1-vs-tolerance curve climbs 0.19 -> 0.74 from ±0.05 to ±0.30, which
                      says the events are right and only the placement is wrong.
  classical   C1 C2 C3 genuinely different machinery, not the CWT ridge re-read.
  learned     L1      supervised, and expected to struggle at n=236 marks from one swimmer.
  routing     --      not a candidate; it is how the final table is READ.

Usage:
    python tools/segmenter_candidates.py --export raw_input.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

sys.path = [p for p in sys.path if p not in ("", ".", str(_ROOT))]
try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None
sys.path.insert(0, str(_ROOT))

import numpy as np
from scipy.signal import find_peaks

import annotations as annot
import metrics as m
import segmenter_eval as se

TOL = 0.15


# ── helpers ──────────────────────────────────────────────────────────────────

def _cycles_from_bounds(vel, bounds):
    """Boundary indices → the cycle-dict shape the 59-02 registry contract requires."""
    out = []
    b = sorted(set(int(x) for x in bounds if 0 <= int(x) <= len(vel)))
    for i in range(len(b) - 1):
        a, c = b[i], b[i + 1]
        if c - a < 2:
            continue
        out.append({"cycle_num": len(out), "start_idx": a, "end_idx": c,
                    "peak_idx": a + int(np.argmax(vel[a:c]))})
    return out or None


def _wavelet_bounds(t, vel):
    cyc = m.segment_cycles_wavelet(t, vel)
    if not cyc:
        return None
    return [c["start_idx"] for c in cyc] + [cyc[-1]["end_idx"]]


def _period(t, vel, fs):
    p = m._estimate_period(t, vel)
    return p if (p and p > 0) else 1.0


# ── R: refinement (snap an existing boundary to a local feature) ─────────────

def _snap(vel, bounds, radius, target):
    """Move each boundary to the best `target` sample within ±radius."""
    out, n = [], len(vel)
    for b in bounds:
        lo, hi = max(0, int(b - radius)), min(n, int(b + radius) + 1)
        if hi - lo < 3:
            out.append(int(b)); continue
        seg = vel[lo:hi]
        out.append(lo + int(np.argmin(seg) if target == "min" else np.argmax(np.gradient(seg))))
    return out


def make_snap(target, radius_frac=0.25):
    """R1/R2: wavelet boundaries snapped to the nearest velocity MIN / steepest RISE.

    radius_frac is the tunable — the search radius as a fraction of a cycle. Snapping
    cannot invent or remove a boundary, only relocate one, so recall is capped by the
    wavelet's; the upside is entirely in precision and timing MAE.
    """
    def cand(t, vel, fs):
        b = _wavelet_bounds(t, vel)
        if not b:
            return None
        radius = max(2, int(radius_frac * _period(t, vel, fs) * fs))
        return _cycles_from_bounds(vel, _snap(vel, b, radius, target))
    return cand


# ── C: non-CWT classical ─────────────────────────────────────────────────────

def make_matched_filter(prom_frac=0.3):
    """C1: per-swimmer matched filter.

    Build a template by averaging the velocity between coarse autocorrelation-spaced
    boundaries, cross-correlate it back over the swim, and take the correlation peaks.
    Adapts to the individual's stroke shape, which no fixed-basis method does.
    """
    def cand(t, vel, fs):
        T = _period(t, vel, fs)
        w = max(4, int(T * fs))
        if len(vel) < 3 * w:
            return None
        v = np.nan_to_num(vel - np.nanmean(vel))
        n_seg = len(v) // w
        if n_seg < 2:
            return None
        template = np.mean(v[:n_seg * w].reshape(n_seg, w), axis=0)
        if float(np.max(np.abs(template))) < 1e-9:
            return None
        corr = np.correlate(v, template, mode="same")
        pk, _ = find_peaks(corr, distance=max(1, int(0.6 * T * fs)),
                           prominence=prom_frac * float(np.std(corr)))
        return _cycles_from_bounds(vel, pk) if len(pk) >= 2 else None
    return cand


def cand_trough_untrimmed(t, vel, fs, full=None, offset=0):
    """C2: the trough segmenter, re-fed the UNTRIMMED trace (CONTEXT D13).

    59-01 scored this 0.00 and the reason was a MISFEED, not a failure: it keys on velocity
    dropping below 0.20 x v95, and Phase 57 made the swim window authoritative, deleting the
    dead tail those deep troughs lived in. Here it runs on the FULL trace and the boundaries
    are filtered back to the scoring window afterwards.

    ⚠ IF THIS WINS, IT CANNOT SHIP AS A REGISTRY VALUE AS-IS. The 59-02 contract hands a
    segmenter the already-sliced vel[ip_end:swim_end]; this one needs what was cut away.
    """
    src = full if full is not None else vel
    ts = np.arange(len(src)) / fs
    cyc = m.segment_cycles_trough(ts, src, m._estimate_period(ts, src))
    if not cyc:
        return None
    b = [c["start_idx"] for c in cyc] + [cyc[-1]["end_idx"]]
    b = [x - offset for x in b if 0 <= x - offset <= len(vel)]
    return _cycles_from_bounds(vel, b) if len(b) >= 2 else None


def make_autocorr(phase_frac=0.0):
    """C3: autocorrelation period + constant-phase placement. No wavelet anywhere.

    A deliberately simple baseline: one global period, boundaries laid down at a fixed
    offset. If a uniform grid competes with the ridge, the ridge is not earning its cost.
    """
    def cand(t, vel, fs):
        T = _period(t, vel, fs)
        step = T * fs
        if step < 2 or len(vel) < 2 * step:
            return None
        start = int(phase_frac * step)
        return _cycles_from_bounds(vel, np.arange(start, len(vel), step))
    return cand


# ── L: learned ───────────────────────────────────────────────────────────────

def _features(vel, fs):
    """Windowed feature stack, one row per sample."""
    v = np.nan_to_num(vel)
    d1 = np.gradient(v)
    d2 = np.gradient(d1)
    w = max(3, int(0.15 * fs))
    import pandas as pd
    roll = pd.Series(v)
    loc_mean = roll.rolling(w, center=True, min_periods=1).mean().values
    loc_std = roll.rolling(w, center=True, min_periods=1).std().fillna(0).values
    return np.column_stack([v, d1, d2, v - loc_mean, loc_std])


class LearnedBoundary:
    """L1: logistic regression predicting 'is this sample an arm entry'.

    ⚠ 236 marks from ONE swimmer. The LOSO-vs-in-sample gap is the point of running it.
    A negative result here is a real deliverable — it closes the question with a number.
    """
    def __init__(self, half_width_s=0.075):
        self.half_width_s = half_width_s
        self.clf = None

    def fit(self, sessions):
        from sklearn.linear_model import LogisticRegression
        X, y = [], []
        for s in sessions:
            f = _features(s["vel_win"], s["fs"])
            lab = np.zeros(len(f))
            for mk in s["marks_win"]:
                i = int(round(mk * s["fs"]))
                half = max(1, int(self.half_width_s * s["fs"]))
                lab[max(0, i - half):min(len(lab), i + half + 1)] = 1
            X.append(f); y.append(lab)
        if not X:
            return self
        X = np.vstack(X); y = np.concatenate(y)
        if len(np.unique(y)) < 2:
            return self
        self.clf = LogisticRegression(max_iter=400, class_weight="balanced").fit(X, y)
        return self

    def predict(self, t, vel, fs):
        if self.clf is None:
            return None
        p = self.clf.predict_proba(_features(vel, fs))[:, 1]
        T = _period(t, vel, fs)
        pk, _ = find_peaks(p, distance=max(1, int(0.6 * T * fs)), height=0.5)
        return _cycles_from_bounds(vel, pk) if len(pk) >= 2 else None


# ── data ─────────────────────────────────────────────────────────────────────

def _load(export):
    if export:
        return json.load(open(export, encoding="utf-8"))["records"]
    if create_client is None:
        sys.exit("supabase-py not importable; use --export")
    try:
        from dotenv import load_dotenv
        load_dotenv(str(_ROOT / ".env"))
    except ImportError:
        pass
    sb = create_client(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    anns = (sb.table("session_annotations")
            .select("session_id, phases, stroke_marks_s").execute().data) or []
    rows = (sb.table("sessions")
            .select("id, stroke_type, created_at, sample_rate_hz, velocity_profile")
            .in_("id", [a["session_id"] for a in anns]).execute().data) or []
    by_id = {r["id"]: r for r in rows}
    return [{"annotation": a, "session": by_id[a["session_id"]]}
            for a in anns if a["session_id"] in by_id]


def _prep(recs):
    """One record per scorable session, pre-sliced to the ANNOTATED window.

    Primary framing is the annotated window ON PURPOSE: the swim window is out of scope for
    59-04, and 59-03's detector is freestyle-tuned (it regressed butterfly 0.320->0.222 and
    breaststroke 0.473->0.167). Scoring candidates through it would penalise a butterfly
    candidate for a defect it did not cause.
    """
    out = []
    for r in recs:
        s, a = r["session"], r["annotation"]
        fs = float(s.get("sample_rate_hz") or annot.FS_HZ)
        vel = np.asarray(s.get("velocity_profile") or [], float)
        ph = a.get("phases") or {}
        marks = sorted(a.get("stroke_marks_s") or [])
        if vel.size < 200 or len(marks) < 4:
            continue
        ss, fin = ph.get("stroke_start_s"), ph.get("finish_s")
        if ss is None or fin is None:
            continue
        i0 = min(max(int(round(ss * fs)), 0), vel.size - 1)
        i1 = min(max(int(round(fin * fs)), i0 + 1), vel.size)
        if i1 - i0 < 100:
            continue
        out.append({
            "id": s["id"], "when": (s.get("created_at") or "")[5:19],
            "stroke": s.get("stroke_type") or "?", "fs": fs,
            "vel_full": vel, "offset": i0,
            "vel_win": vel[i0:i1], "t_win": np.arange(i1 - i0) / fs,
            "marks_win": [mk - i0 / fs for mk in marks],
            "n_truth_cycles": max(1, len(marks[0::annot.marks_per_cycle(s.get("stroke_type"))])),
        })
    return out


def _score(sess, cycles):
    if not cycles:
        return {"f1": 0.0, "mae_s": None, "n_pred": 0}, 0
    pred = [c["start_idx"] / sess["fs"] for c in cycles] + [cycles[-1]["end_idx"] / sess["fs"]]
    sc = se.score_series(pred, sess["marks_win"], TOL)
    return sc, len(pred)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export")
    args = ap.parse_args()
    data = _prep(_load(args.export))
    print(f"{len(data)} scorable sessions "
          f"({', '.join(sorted({d['stroke'] for d in data}))})\n")

    fixed = {
        "wavelet (incumbent)": lambda t, v, fs: m.segment_cycles_wavelet(t, v),
        "peakpick (incumbent)": lambda t, v, fs: _cycles_from_bounds(
            v, find_peaks(np.nan_to_num(m._detrend_for_cwt(v, fs)),
                          distance=max(1, int(0.45 * _period(t, v, fs) * fs)),
                          prominence=0.25 * float(np.percentile(
                              np.abs(np.nan_to_num(m._detrend_for_cwt(v, fs))), 95)))[0]),
        "R1 snap->vel min": make_snap("min"),
        "R2 snap->steep rise": make_snap("rise"),
        "C1 matched filter": make_matched_filter(),
        "C2 trough untrimmed": lambda t, v, fs, s=None: None,   # needs the full trace
        "C3 autocorr grid": make_autocorr(),
    }

    results = {}
    for name, fn in fixed.items():
        for d in data:
            try:
                if name.startswith("C2"):
                    cyc = cand_trough_untrimmed(d["t_win"], d["vel_win"], d["fs"],
                                                full=d["vel_full"], offset=d["offset"])
                else:
                    cyc = fn(d["t_win"], d["vel_win"], d["fs"])
            except Exception:
                cyc = None
            sc, npred = _score(d, cyc)
            results.setdefault((name, d["stroke"]), []).append(
                (sc["f1"], sc["mae_s"], npred / d["n_truth_cycles"]))

    # ── L1, leave-one-session-out AND in-sample ──────────────────────────────
    loso, insample = {}, {}
    for held in data:
        train = [d for d in data if d["id"] != held["id"]]
        mdl = LearnedBoundary().fit(train)
        try:
            cyc = mdl.predict(held["t_win"], held["vel_win"], held["fs"])
        except Exception:
            cyc = None
        sc, npred = _score(held, cyc)
        loso.setdefault(held["stroke"], []).append(
            (sc["f1"], sc["mae_s"], npred / held["n_truth_cycles"]))
    full = LearnedBoundary().fit(data)
    for d in data:
        try:
            cyc = full.predict(d["t_win"], d["vel_win"], d["fs"])
        except Exception:
            cyc = None
        sc, npred = _score(d, cyc)
        insample.setdefault(d["stroke"], []).append(
            (sc["f1"], sc["mae_s"], npred / d["n_truth_cycles"]))

    strokes = ["freestyle", "butterfly", "breaststroke"]
    print(f'{"candidate":<22}' + "".join(f'{s[:9]:>11}' for s in strokes)
          + "     (median F1 @+/-0.15s, annotated window)")
    for name in fixed:
        row = f'{name:<22}'
        for s in strokes:
            v = results.get((name, s))
            row += f'{np.median([x[0] for x in v]):>11.3f}' if v else f'{"-":>11}'
        print(row)
    row = f'{"L1 learned (LOSO)":<22}'
    for s in strokes:
        v = loso.get(s)
        row += f'{np.median([x[0] for x in v]):>11.3f}' if v else f'{"-":>11}'
    print(row)
    row = f'{"L1 learned (in-samp)":<22}'
    for s in strokes:
        v = insample.get(s)
        row += f'{np.median([x[0] for x in v]):>11.3f}' if v else f'{"-":>11}'
    print(row)

    print(f'\n{"candidate":<22}{"stroke":<14}{"F1":>7}{"MAE":>8}{"bound/cycle":>13}')
    for name in fixed:
        for s in strokes:
            v = results.get((name, s))
            if not v:
                continue
            mae = [x[1] for x in v if x[1] is not None]
            print(f'{name:<22}{s:<14}{np.median([x[0] for x in v]):>7.3f}'
                  f'{(np.median(mae) if mae else float("nan")):>8.3f}'
                  f'{np.median([x[2] for x in v]):>13.2f}')
    for label, src in (("L1 learned (LOSO)", loso), ("L1 learned (in-samp)", insample)):
        for s in strokes:
            v = src.get(s)
            if not v:
                continue
            mae = [x[1] for x in v if x[1] is not None]
            print(f'{label:<22}{s:<14}{np.median([x[0] for x in v]):>7.3f}'
                  f'{(np.median(mae) if mae else float("nan")):>8.3f}'
                  f'{np.median([x[2] for x in v]):>13.2f}')

    # ── tolerance sweep: distinguishes "wrong events" from "right events, misplaced" ──
    SWEEP = (0.05, 0.10, 0.15, 0.20, 0.30)
    sweep_of = ["wavelet (incumbent)", "peakpick (incumbent)", "R2 snap->steep rise",
                "C2 trough untrimmed"]
    print(f'\nTOLERANCE SWEEP (median F1)   ' + "".join(f'{f"±{x}":>8}' for x in SWEEP))
    for name in sweep_of:
        for s in strokes:
            vals = []
            for tol in SWEEP:
                per = []
                for d in data:
                    if d["stroke"] != s:
                        continue
                    try:
                        cyc = (cand_trough_untrimmed(d["t_win"], d["vel_win"], d["fs"],
                                                     full=d["vel_full"], offset=d["offset"])
                               if name.startswith("C2") else fixed[name](d["t_win"], d["vel_win"], d["fs"]))
                    except Exception:
                        cyc = None
                    if not cyc:
                        per.append(0.0); continue
                    pred = ([c["start_idx"] / d["fs"] for c in cyc]
                            + [cyc[-1]["end_idx"] / d["fs"]])
                    per.append(se.score_series(pred, d["marks_win"], tol)["f1"])
                vals.append(np.median(per) if per else float("nan"))
            print(f'  {name:<22}{s:<14}' + "".join(f'{v:>8.3f}' for v in vals))

    print("\nRECOMMENDATION (per stroke, best median F1; incumbent must be BEATEN to win)")
    for s in strokes:
        scores = {n: np.median([x[0] for x in results[(n, s)]])
                  for n in fixed if (n, s) in results}
        if loso.get(s):
            scores["L1 learned (LOSO)"] = np.median([x[0] for x in loso[s]])
        if not scores:
            continue
        best = max(scores, key=scores.get)
        inc = scores.get("wavelet (incumbent)", 0.0)
        verdict = (f"SHIP {best} ({scores[best]:.3f} vs wavelet {inc:.3f})"
                   if scores[best] > inc + 0.01 else
                   f"NONE - keep the wavelet ({inc:.3f}); best challenger "
                   f"{best} {scores[best]:.3f}")
        print(f"  {s:<14}{verdict}")


if __name__ == "__main__":
    main()
