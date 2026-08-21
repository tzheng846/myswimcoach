"""score_boundaries_by_swimmer.py — the 4 phase boundaries, scored PER SWIMMER (Phase 78).

The per-stroke scorers (score_segmenter / score_underwater / breakout_band_probe) answer
"how good is each boundary on average?" This answers the confidence question Phase 78 exists
for: does each boundary hold PER SWIMMER, or is one swimmer carrying the average? It scores
the SHIPPED detectors for all four markers against the human marks, attributes every session
to its swimmer, and prints a swimmer x boundary matrix.

No detector is reimplemented — each prediction calls the same metrics.py / annotations.py
the production pipeline runs:
  dive_start_s       build_seed(metrics_json_auto)   (= baseline_end motion-onset; the P79 target)
  underwater_start_s metrics.detect_underwater_start (75-02)
  stroke_start_s     detect_breakout_kickband (free/back, 76) / detect_breakout_fly (fly, 77)
                     / incumbent ip_end (breast, untuned) — swim_end-bounded + collapse-guarded,
                       EXACTLY as breakout_band_probe resolves the shipped answer
  finish_s           build_seed(metrics_json_auto)   (= detect_swim_window/swim_end, inherited)

Circularity guard copied from score_segmenter._auto_metrics: predictions seed from the
PRISTINE metrics_json_auto, never the annotation-recomputed metrics_json.

Read-only Supabase (service-role key from .env); no write/update/delete. Identity is printed
(first name) — this is the swimmer-attribution tool, like tools/annotated_roster.py.

    python tools/score_boundaries_by_swimmer.py
    python tools/score_boundaries_by_swimmer.py --tol 0.5   # change the within-tolerance band
"""
import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path = [p for p in sys.path if p not in ("", ".")]

import numpy as np                      # noqa: E402
from dotenv import load_dotenv          # noqa: E402
from supabase import create_client      # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
import annotations as annot             # noqa: E402
import metrics                          # noqa: E402

BOUNDS = ("dive_start_s", "underwater_start_s", "stroke_start_s", "finish_s")
_KICKBAND_STROKES = ("freestyle", "backstroke")


def _client():
    load_dotenv(REPO_ROOT / ".env")
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        sys.exit("Need SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
    return create_client(url, key)


def _arr(x):
    return np.array([np.nan if v is None else float(v) for v in (x or [])], dtype=float)


def _auto_metrics(session):
    """The PRISTINE auto metrics_json (score_segmenter._auto_metrics), else None."""
    auto = session.get("metrics_json_auto")
    if auto:
        return auto
    mj = session.get("metrics_json") or {}
    if not mj or ((mj.get("data_quality") or {}).get("recomputed_from_annotation")):
        return None
    return mj


def _current_ip(t, vel, fs):
    """Production incumbent breakout (ip_end), exactly as compute_session_metrics resolves it."""
    ph = metrics.detect_phases(t, vel)
    b_end = ph["baseline_end"]
    win = metrics.detect_swim_window(t, vel)
    if win is not None:
        return min(max(int(win[0]), b_end), int(win[1]) - 1) / fs
    return metrics.detect_initial_phase(t, vel, b_end)["initial_phase_end_idx"] / fs


def _shipped_breakout_s(t, vel, fs, stroke, uw_truth_s):
    """The shipped stroke_start_s in seconds — mirrors breakout_band_probe's ship resolution
    (swim_end-bounded, collapse-guarded, incumbent fallback)."""
    phs = metrics.detect_phases(t, vel)
    swim_end = phs["swim_end"]
    win = metrics.detect_swim_window(t, vel, stroke)
    if win is not None:
        swim_end = min(max(int(win[1]), phs["baseline_end"] + 1), vel.size)
    if uw_truth_s is not None:
        uw_idx = int(round(float(uw_truth_s) * fs))
    else:
        di = metrics.detect_underwater_start(t, vel, phs["baseline_end"])
        uw_idx = int(di) if di is not None else phs["baseline_end"]
    cur_ip = _current_ip(t, vel, fs)
    if stroke in _KICKBAND_STROKES:
        idx = metrics.detect_breakout_kickband(t, vel, uw_idx, swim_end)
    elif stroke == "butterfly":
        idx = metrics.detect_breakout_fly(t, vel, uw_idx, swim_end)
    else:
        return cur_ip                    # breaststroke: incumbent, untuned
    if idx is None or not metrics._breakout_leaves_swim(t, vel, idx, swim_end):
        return cur_ip                    # refused/vetoed -> incumbent, scored as such
    return idx / fs


def _predict(session, ann_phases):
    """{boundary: (pred_s, truth_s)} for one session, shipped detectors. None where unavailable."""
    fs = float(session.get("sample_rate_hz") or annot.FS_HZ)
    vel = _arr(session.get("velocity_profile"))
    if vel.size < 10:
        return {}
    t = np.arange(vel.size) / fs
    auto = _auto_metrics(session)
    seed = (annot.build_seed(auto, fs) or {}).get("phases") or {} if auto else {}
    stroke = session.get("stroke_type") or "none"

    out = {}
    out["dive_start_s"] = (seed.get("dive_start_s"), ann_phases.get("dive_start_s"))
    out["finish_s"] = (seed.get("finish_s"), ann_phases.get("finish_s"))

    dive_idx = int(round((seed.get("dive_start_s") or 0.0) * fs))
    uw_idx = metrics.detect_underwater_start(t, vel, dive_idx)
    out["underwater_start_s"] = (None if uw_idx is None else uw_idx / fs,
                                 ann_phases.get("underwater_start_s"))

    ss_truth = ann_phases.get("stroke_start_s")
    out["stroke_start_s"] = (
        (_shipped_breakout_s(t, vel, fs, stroke, ann_phases.get("underwater_start_s"))
         if ss_truth is not None else None),
        ss_truth,
    )
    return out


def _load(sb):
    anns = (sb.table("session_annotations").select("session_id, phases").execute().data) or []
    ann_by_id = {a["session_id"]: (a.get("phases") or {}) for a in anns}
    rows = (sb.table("sessions")
              .select("id, stroke_type, athlete_id, sample_rate_hz, velocity_profile, "
                      "metrics_json, metrics_json_auto")
              .in_("id", list(ann_by_id)).execute().data) or []
    names = {}
    aids = list({r["athlete_id"] for r in rows if r.get("athlete_id")})
    if aids:
        try:
            names = {a["id"]: (a.get("name") or "")
                     for a in (sb.table("athletes").select("id, name")
                               .in_("id", aids).execute().data or [])}
        except Exception:
            pass
    out = []
    for r in rows:
        aid = r.get("athlete_id")
        out.append({"session": r, "phases": ann_by_id.get(r["id"], {}),
                    "swimmer": names.get(aid) or (aid[:8] if aid else "?"),
                    "stroke": r.get("stroke_type") or "?"})
    return out


def _cell(errs, tol):
    if not errs:
        return f"{'-':>18}"
    a = np.abs(errs)
    return f"{np.median(a):.2f}s ({len(a)},{int((a <= tol).sum())})".rjust(18)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tol", type=float, default=0.5, help="within-tolerance band, seconds")
    args = ap.parse_args()

    recs = _load(_client())
    # errs[boundary][swimmer] and errs[boundary]["ALL"]; also per-stroke breakout for validation
    errs = {b: defaultdict(list) for b in BOUNDS}
    bk_by_stroke = defaultdict(list)
    swimmers = set()
    for r in recs:
        swimmers.add(r["swimmer"])
        preds = _predict(r["session"], r["phases"])
        for b in BOUNDS:
            p, tr = preds.get(b, (None, None))
            if p is None or tr is None:
                continue
            e = float(p) - float(tr)
            errs[b][r["swimmer"]].append(e)
            errs[b]["ALL"].append(e)
            if b == "stroke_start_s":
                bk_by_stroke[r["stroke"]].append(e)

    order = sorted(swimmers, key=lambda s: -len(errs["dive_start_s"].get(s, [])
                                                + errs["stroke_start_s"].get(s, [])))
    print("=" * (22 + 18 * (len(order) + 1)))
    print(f"BOUNDARY TEST BY SWIMMER — shipped detectors vs human marks (annotated corpus)")
    print(f"cell = median|err| (n, #within {args.tol:.1f}s).  Lower is better.")
    print("=" * (22 + 18 * (len(order) + 1)))
    hdr = f"{'boundary':<22}" + "".join(f"{s[:16]:>18}" for s in order) + f"{'ALL':>18}"
    print(hdr)
    print("-" * len(hdr))
    for b in BOUNDS:
        line = f"{b:<22}" + "".join(_cell(errs[b].get(s, []), args.tol) for s in order)
        line += _cell(errs[b]["ALL"], args.tol)
        print(line)

    # signed bias, ALL, to keep the dive_start early-fire visible
    print(f"\nsigned bias (mean err, ALL):")
    for b in BOUNDS:
        e = errs[b]["ALL"]
        if e:
            print(f"  {b:<22}{np.mean(e):+.2f}s   worst|err| {np.max(np.abs(e)):.2f}s   n={len(e)}")

    # validation: breakout per-stroke must match breakout_band_probe (free 0.42, fly 0.38)
    print(f"\nvalidation — stroke_start_s (breakout) per stroke, must match breakout_band_probe:")
    for stroke in sorted(bk_by_stroke):
        a = np.abs(bk_by_stroke[stroke])
        print(f"  {stroke:<12} median {np.median(a):.2f}s  n={len(a)}  (probe: free 0.42 / fly 0.38)")


if __name__ == "__main__":
    main()
