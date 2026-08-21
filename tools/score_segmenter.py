"""Score segmenters and phase detection against the human annotation ground truth (Phase 59).

Runs three candidate segmenters over every annotated session and reports how well each
agrees with the coach's marks, per stroke. Also scores `detect_phases` +
`detect_initial_phase` against the four human phase markers — neither has ever been
measured against ground truth either.

Two framings, because they answer different questions and the wavelet scores very
differently on each:
  * CYCLES     — predicted boundaries vs the human CYCLE boundaries
                 (`annotations.annotation_to_overrides`, i.e. every k-th mark).
  * ENTRIES    — predicted boundaries vs EVERY human mark (one mark = one arm entry).

Two windows, because the gap between them is the share of the error that belongs to
phase detection rather than segmentation — never separated before:
  * ANNOTATED  — vel[stroke_start_s : finish_s], isolating the segmenter.
  * PRODUCTION — vel[ip_end : swim_end], exactly as compute_session_metrics slices it.

Usage:
    python tools/score_segmenter.py                          # fetch from Supabase
    python tools/score_segmenter.py --save-input raw.json    # fetch and cache
    python tools/score_segmenter.py --export raw.json        # offline, from cache
    python tools/score_segmenter.py --tol 0.15 --out report.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# The local supabase/ directory (SQL migrations) is a namespace package that shadows the
# installed supabase-py whenever the repo root is importable — the same trap
# fetch_annotations.py:22 works around. Import the real package FIRST, while the root is
# off sys.path, then put the root back for metrics/annotations/segmenter_eval.
# THE ORDER OF THESE TWO BLOCKS IS LOAD-BEARING. Swapping them re-creates the bug, and it
# surfaces as "cannot import name 'create_client'", which reads like a missing dependency.
sys.path = [p for p in sys.path if p not in ("", ".", str(_ROOT))]
try:
    from supabase import create_client
except Exception:  # pragma: no cover - only when supabase-py is absent
    create_client = None
sys.path.insert(0, str(_ROOT))

import numpy as np
from scipy.signal import find_peaks

import annotations as annot
import metrics as m
import segmenter_eval as se

# Partially labeled sessions: a correct detection on one of these looks like a false
# positive, so precision is meaningless. CONFIRMED by the annotator at the 59-01
# checkpoint on 2026-08-09, against the coverage column this tool prints (CONTEXT D4).
# These are still scored and printed, and still counted in recall_all — only precision
# and F1 drop them. Override with --exclude.
#
# TWO criteria, deliberately, and they disagree on ranking: coverage AND the
# ISI-vs-trace-period mismatch. That is why 08-05 20:06 (coverage 0.86) is here while
# 08-05 20:10 (coverage 0.84) is not. A single coverage<0.85 rule was offered at the
# checkpoint and declined — do not "tidy" this into one threshold.
EXCLUDE_IDS = (
    "e20cd07d-ab8d-4e15-988c-e9f72103ead8",  # 06-23 16:46 freestyle — 3 marks, coverage 0.71
    "8a51ece7-a182-475f-b529-46cea7dd76fe",  # 08-05 19:50 freestyle — 3 marks, coverage 0.50
    "149f6520-d3a4-4949-849f-fccf0ab812e1",  # 08-05 20:06 freestyle — ISI 1.32x the trace's own period
    "6b206400-4747-4289-a8cb-ba3f07987c2a",  # 08-05 20:57 butterfly — finish_s null, no window
)

DEFAULT_SWEEP = (0.05, 0.10, 0.15, 0.20, 0.30)
WINDOWS = ("annotated", "production")
FRAMINGS = ("cycles", "entries")
CANDIDATES = ("wavelet", "trough", "peakpick")


# ── data acquisition ─────────────────────────────────────────────────────────

def _fetch_from_supabase():
    if create_client is None:
        sys.exit("Error: supabase-py is not importable. Use --export to run offline.")
    try:
        from dotenv import load_dotenv
        load_dotenv(str(_ROOT / ".env"))
    except ImportError:
        pass
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        sys.exit("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    sb = create_client(url, key)

    anns = (sb.table("session_annotations")
              .select("session_id, phases, stroke_marks_s, source")
              .execute().data) or []
    if not anns:
        sys.exit("No annotated sessions found.")
    ids = [a["session_id"] for a in anns]
    rows = (sb.table("sessions")
              .select("id, stroke_type, created_at, sample_rate_hz, velocity_profile, "
                      "metrics_json, metrics_json_auto")
              .in_("id", ids).execute().data) or []
    by_id = {r["id"]: r for r in rows}

    out = []
    for a in anns:
        row = by_id.get(a["session_id"])
        if row:
            out.append({"annotation": a, "session": row})
    return out


# ── helpers ──────────────────────────────────────────────────────────────────

def _fs_of(session):
    """The session's own rate; NULL means pre-Phase-52 and falls back to annotations.FS_HZ.

    Do NOT substitute ~89.9 here: the two June sessions genuinely ran at ~100 Hz
    (2033 samples / 20.3 s lap = 100.1), so the fallback is accurate for them.
    """
    fs = session.get("sample_rate_hz")
    try:
        fs = float(fs)
    except (TypeError, ValueError):
        return float(annot.FS_HZ)
    return fs if fs > 0 else float(annot.FS_HZ)


def _auto_metrics(session):
    """The PRISTINE auto metrics_json, or (None, reason).

    ⚠⚠ CIRCULARITY GUARD — the single most important function in this file.
    For every annotated session api.py has already OVERWRITTEN `metrics_json` with metrics
    recomputed FROM the human annotation, backing the original up to `metrics_json_auto`
    once. Seeding phase predictions from `metrics_json` and then scoring them against that
    same annotation compares the annotation with itself and manufactures a near-perfect
    score that means nothing.
    """
    auto = session.get("metrics_json_auto")
    if auto:
        return auto, None
    mj = session.get("metrics_json") or {}
    if not mj:
        return None, "no metrics_json"
    if ((mj.get("data_quality") or {}).get("recomputed_from_annotation")):
        return None, "metrics_json recomputed from annotation, no metrics_json_auto backup"
    return mj, None


def _cycle_boundaries(cycles, fs, offset_s):
    """Cycle dicts -> absolute boundary times: every start, plus the final end."""
    if not cycles:
        return []
    out = [offset_s + c["start_idx"] / fs for c in cycles]
    out.append(offset_s + cycles[-1]["end_idx"] / fs)
    return out


def _predict(candidate, vel_seg, fs, offset_s):
    """Run one candidate on a slice. Returns (times, note).

    All three segmenters legitimately return None on short or flat input. None is ZERO
    predictions and is counted — never a crash, never a silently dropped session.
    """
    if vel_seg.size < 8:
        return [], "slice too short"
    t = np.arange(vel_seg.size) / fs
    try:
        if candidate == "wavelet":
            cyc = m.segment_cycles_wavelet(t, vel_seg)
            return _cycle_boundaries(cyc, fs, offset_s), (None if cyc else "returned None")
        if candidate == "trough":
            cyc = m.segment_cycles_trough(t, vel_seg, m._estimate_period(t, vel_seg))
            return _cycle_boundaries(cyc, fs, offset_s), (None if cyc else "returned None")
        if candidate == "peakpick":
            # Baseline comparator only. Deliberately lives here and NOT in metrics.py —
            # this plan does not add an algorithm to the production pipeline.
            d = m._detrend_for_cwt(vel_seg, fs)
            finite = d[np.isfinite(d)]
            if finite.size == 0:
                return [], "detrend produced no finite samples"
            p95 = float(np.percentile(np.abs(finite), 95))
            period = m._estimate_period(t, vel_seg) or 1.0
            peaks, _ = find_peaks(
                np.nan_to_num(d),
                prominence=max(1e-6, 0.25 * p95),
                distance=max(1, int(0.45 * period * fs)),
            )
            return [offset_s + int(i) / fs for i in peaks], (None if len(peaks) else "no peaks")
    except Exception as e:  # a candidate blowing up must not end the run
        return [], f"raised {type(e).__name__}: {e}"
    return [], "unknown candidate"


def _windows(vel, fs, phases):
    """(name -> (i0, i1)) for the annotated and production windows."""
    out = {}
    ss, fin = phases.get("stroke_start_s"), phases.get("finish_s")
    if ss is not None and fin is not None:
        i0 = min(max(int(round(float(ss) * fs)), 0), vel.size - 1)
        i1 = min(max(int(round(float(fin) * fs)), i0 + 1), vel.size)
        out["annotated"] = (i0, i1)
    try:
        # Mirror compute_session_metrics EXACTLY (Phase 59-03): the rhythm window decides
        # both boundaries, and when it declines to answer the old motion-based pair stands.
        # ⚠ Before 59-04 this called detect_phases/detect_initial_phase only, so the
        # "production" column had silently stopped measuring what production slices.
        t = np.arange(vel.size) / fs
        ph = m.detect_phases(t, vel)
        b_end = ph["baseline_end"]
        ip = m.detect_initial_phase(t, vel, b_end)["initial_phase_end_idx"]
        swim_end = ph["swim_end"]
        win = m.detect_swim_window(t, vel)
        if win is not None:
            swim_end = min(max(int(win[1]), b_end + 1), vel.size)
            ip = min(max(int(win[0]), b_end), swim_end - 1)
        i0 = min(max(int(ip), 0), vel.size - 1)
        i1 = min(max(int(swim_end), i0 + 1), vel.size)
        out["production"] = (i0, i1)
    except Exception:
        pass
    return out


def _truth_cycles(annotation, n_samples, fs, stroke_type):
    """Human CYCLE boundaries, derived through the shipped contract rather than re-derived.

    Calling annotation_to_overrides means the pairing rule (k marks per cycle, and the
    k==1-only finish append) has exactly ONE definition in the codebase.
    """
    ov = annot.annotation_to_overrides(annotation, int(n_samples), fs, stroke_type)
    bounds = ov.get("cycle_bounds") or []
    if not bounds:
        return []
    out = [b[0] / fs for b in bounds]
    out.append(bounds[-1][1] / fs)
    return out


# ── per-session scoring ──────────────────────────────────────────────────────

def score_session(record, tol, sweep_tols):
    ann = record["annotation"]
    sess = record["session"]
    fs = _fs_of(sess)
    vel = np.asarray(sess.get("velocity_profile") or [], dtype=float)
    phases = ann.get("phases") or {}
    marks = sorted(float(x) for x in (ann.get("stroke_marks_s") or []))
    stroke = sess.get("stroke_type")

    out = {
        "session_id": sess["id"],
        "stroke_type": stroke,
        "created_at": sess.get("created_at"),
        "fs_hz": fs,
        "fs_source": "row" if sess.get("sample_rate_hz") else "fallback",
        "n_samples": int(vel.size),
        "n_marks": len(marks),
        "marks_per_cycle": annot.marks_per_cycle(stroke),
        "notes": [],
        "cycles": {},
        "phases": {},
    }
    if vel.size < 8:
        out["notes"].append("no usable velocity_profile")
        return out

    out["coverage"] = se.coverage(marks, phases.get("stroke_start_s"), phases.get("finish_s"))

    truth = {
        "cycles": _truth_cycles(ann, vel.size, fs, stroke),
        "entries": marks,
    }
    out["n_truth_cycles"] = len(truth["cycles"])

    # Human cycle rate straight from the labels — independent of whether the session was
    # ever recomputed, so it is comparable across the whole corpus.
    tc = truth["cycles"]
    human_spm = 60.0 / float(np.mean(np.diff(tc))) if len(tc) >= 2 else None
    auto_mj, _ = _auto_metrics(sess)
    auto_spm = ((auto_mj or {}).get("session") or {}).get("stroke_rate_spm")
    out["rate"] = {
        "auto_spm": auto_spm,
        "human_spm": human_spm,
        "ratio": (auto_spm / human_spm) if (auto_spm and human_spm) else None,
    }

    for wname, span in _windows(vel, fs, phases).items():
        i0, i1 = span
        seg = vel[i0:i1]
        out["cycles"][wname] = {"window_s": [i0 / fs, i1 / fs]}
        for cand in CANDIDATES:
            pred, note = _predict(cand, seg, fs, i0 / fs)
            if note:
                out["notes"].append(f"{wname}/{cand}: {note}")
            entry = {"n_pred": len(pred)}
            for framing in FRAMINGS:
                entry[framing] = se.score_series(pred, truth[framing], tol)
            if wname == "annotated":
                entry["sweep_entries"] = se.sweep(pred, truth["entries"], sweep_tols)
            out["cycles"][wname][cand] = entry

    # ── phase markers ────────────────────────────────────────────────────────
    auto_mj, reason = _auto_metrics(sess)
    if auto_mj is None:
        out["phases"] = {"unscorable": reason}
        out["notes"].append(f"phases unscorable: {reason}")
    else:
        seeded = (annot.build_seed(auto_mj, fs) or {}).get("phases") or {}
        for key in annot.PHASE_KEYS:
            p, t_ = seeded.get(key), phases.get(key)
            out["phases"][key] = {
                "pred_s": p,
                "truth_s": t_,
                "error_s": (float(p) - float(t_)) if (p is not None and t_ is not None) else None,
            }
    return out


# ── reporting ────────────────────────────────────────────────────────────────

def _fmt(v, nd=3):
    return "-" if v is None else f"{v:.{nd}f}"


def print_report(rows, tol, exclude):
    n_ex = sum(1 for r in rows if r["session_id"] in exclude)
    print("=" * 100)
    print(f"SEGMENTER SCORING - {len(rows)} annotated sessions, primary tolerance +/-{tol:.2f} s")
    print("!! SCORED on 4 annotated swimmers (Tony/Leo/Chantee/Dane) of 9 athlete rows;")
    print("  55/92 DB sessions unlabeled - Titus/AlexGroup/Jenna/Michael unscored, back n=0 (Phase 78).")
    print("  A change-detector, not a definition of correctness.")
    print(f"Excluded from precision/F1 (partial labels): {n_ex}")
    print("=" * 100)

    print("\nPER SESSION")
    print(f"{'created':<18}{'stroke':<13}{'marks':>6}{'cyc':>5}{'cov':>7}"
          f"{'auto_spm':>9}{'hum_spm':>8}{'ratio':>7}  excl")
    for r in sorted(rows, key=lambda r: r.get("created_at") or ""):
        cov = (r.get("coverage") or {}).get("ratio")
        rate = r.get("rate") or {}
        print(f"{(r.get('created_at') or '')[5:19]:<18}{(r.get('stroke_type') or '?'):<13}"
              f"{r['n_marks']:>6}{r.get('n_truth_cycles', 0):>5}{_fmt(cov, 2):>7}"
              f"{_fmt(rate.get('auto_spm'), 1):>9}{_fmt(rate.get('human_spm'), 1):>8}"
              f"{_fmt(rate.get('ratio'), 2):>7}  "
              f"{'YES' if r['session_id'] in exclude else ''}")

    for wname in WINDOWS:
        for framing in FRAMINGS:
            print(f"\n{'=' * 100}\nCYCLE SCORING - window={wname.upper()}  "
                  f"framing={framing.upper()}  tol=+/-{tol:.2f}s")
            print(f"{'candidate':<11}{'stroke':<13}{'sess':>5}{'excl':>5}{'pred':>6}"
                  f"{'truth':>6}{'hit':>5}{'prec':>7}{'rec':>7}{'F1':>7}{'MAE':>7}{'rec_all':>8}")
            for cand in CANDIDATES:
                agg = se.aggregate(
                    [{"session_id": r["session_id"], "stroke_type": r["stroke_type"],
                      "score": r["cycles"].get(wname, {}).get(cand, {}).get(framing, {})}
                     for r in rows if wname in r["cycles"]],
                    exclude_ids=exclude,
                )
                for stroke in sorted(agg):
                    a = agg[stroke]
                    print(f"{cand:<11}{stroke:<13}{a['n_sessions']:>5}{a['n_excluded']:>5}"
                          f"{a['n_pred']:>6}{a['n_truth']:>6}{a['matched']:>5}"
                          f"{a['precision']:>7.2f}{a['recall']:>7.2f}{a['f1']:>7.2f}"
                          f"{_fmt(a['mae_s']):>7}{a['recall_all']:>8.2f}")

    print(f"\n{'=' * 100}\nPHASE MARKER SCORING - build_seed(metrics_json_auto) vs human marks")
    print("(predictions come from the PRISTINE auto result; scoring the recomputed")
    print(" metrics_json against its own annotation would be circular)")
    unscorable = [r for r in rows if "unscorable" in (r.get("phases") or {})]
    print(f"{'marker':<22}{'n':>4}{'MAE':>8}{'bias':>9}{'p50':>8}{'worst':>8}")
    for key in annot.PHASE_KEYS:
        errs = [r["phases"][key]["error_s"] for r in rows
                if key in (r.get("phases") or {}) and r["phases"][key].get("error_s") is not None]
        if not errs:
            print(f"{key:<22}{0:>4}{'-':>8}{'-':>9}{'-':>8}{'-':>8}")
            continue
        a = np.abs(errs)
        print(f"{key:<22}{len(errs):>4}{a.mean():>8.3f}{np.mean(errs):>9.3f}"
              f"{np.median(a):>8.3f}{a.max():>8.3f}")
    print(f"unscorable for phases: {len(unscorable)}")

    notes = [(r.get("created_at", "")[5:19], n) for r in rows for n in r.get("notes", [])]
    if notes:
        print(f"\nNOTES ({len(notes)})")
        for when, n in sorted(notes):
            print(f"  {when}  {n}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", help="read cached input JSON instead of Supabase")
    ap.add_argument("--save-input", help="write the fetched input JSON here (for offline reruns)")
    ap.add_argument("--out", default="segmenter_report.json", help="write the full report JSON here")
    ap.add_argument("--tol", type=float, default=0.15, help="primary matching tolerance, seconds")
    ap.add_argument("--sweep", default=",".join(str(t) for t in DEFAULT_SWEEP))
    ap.add_argument("--exclude", default=None,
                    help="comma-separated session ids to drop from precision/F1 "
                         "(default: the confirmed partial-label list)")
    args = ap.parse_args()

    records = (json.load(open(args.export, encoding="utf-8"))["records"]
               if args.export else _fetch_from_supabase())
    if args.save_input:
        with open(args.save_input, "w", encoding="utf-8") as f:
            json.dump({"records": records}, f)
        print(f"Cached input -> {args.save_input}")

    sweep_tols = [float(x) for x in args.sweep.split(",") if x.strip()]
    exclude = set(args.exclude.split(",")) if args.exclude else set(EXCLUDE_IDS)

    rows = [score_session(r, args.tol, sweep_tols) for r in records]
    print_report(rows, args.tol, exclude)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"tol_s": args.tol, "excluded": sorted(exclude), "sessions": rows}, f, indent=1)
    print(f"\nReport -> {args.out}")


if __name__ == "__main__":
    main()
