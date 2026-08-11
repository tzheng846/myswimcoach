"""Measure what removing the steady/ramp_up cycle split does. WRITES NOTHING.

Phase 61-01 (D5) removes the `steady` / `ramp_up` tagging from metrics.py, so every
session metric summarizes ALL cycles instead of the steady subset. This tool measures
that change against real stored sessions, so "old -> new" in the SUMMARY is a
measurement rather than a reconstruction. Run it BEFORE the change for the baseline and
AFTER for the comparison.

⚠ THE FILTER IS MISNAMED, AND THIS TOOL IS THE EVIDENCE. `ramp_up` is a velocity gate
(arm_peak < 0.50 x p75), not a positional one. Measured 2026-08-11, it does not mark
acceleration from rest — it overwhelmingly marks the swimmer DECELERATING INTO THE WALL.
The `--positions` report exists to keep that reproducible: if the median normalized
position of excluded cycles is near 1.0, they are at the FINISH, not the start.

⚠ READ-ONLY BY CONSTRUCTION. No insert/update/upsert/delete call appears in this file.

⚠ Reads each row's own sample_rate_hz and never assumes 100 Hz. This repo has a
documented history of exactly that bug (Phase 52, Phase 60-01), and fetch_sessions.py:30
still carries it.

Usage:
    python tools/rampup_impact.py
    python tools/rampup_impact.py --stroke freestyle
    python tools/rampup_impact.py --json before.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# Import the real supabase package before the repo root joins sys.path — the local
# supabase/ SQL directory shadows it. Order is load-bearing; see score_segmenter.py.
sys.path = [p for p in sys.path if p not in ("", ".", str(_ROOT))]
try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None
sys.path.insert(0, str(_ROOT))

import numpy as np

# The metrics this plan moves. Mirrors metrics.py's session-summary block exactly.
METRICS = [
    "stroke_count",
    "stroke_rate_spm",
    "mean_arm_peak_vel_ms",
    "cv_arm_peak_vel",
    "mean_isi_s",
    "cv_isi",
    "mean_dps_m",
    "fatigue_index_pct",
]

# ratings.py band drivers, and the two D15 re-anchors. Both are "lower is better".
BAND_DRIVERS = ("cv_arm_peak_vel", "fatigue_index_pct")


def _fetch(limit):
    if create_client is None:
        sys.exit("Error: supabase-py is not importable.")
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
    return (sb.table("sessions")
            .select("id, stroke_type, created_at, sample_rate_hz, metrics_json")
            .order("created_at", desc=True)
            .limit(limit)
            .execute().data) or []


def summarize(cycles):
    """Recompute the session summary from a cycle list, mirroring metrics.py.

    Kept deliberately in step with metrics.py's block: mean over the selected cycles,
    CV as std/mean, fatigue as (q1 - q4) / q1 with q = max(1, n // 4).
    """
    sel = [c for c in cycles if c.get("arm_peak_vel") is not None
           and c.get("duration_s") is not None]
    if len(sel) < 2:
        return None
    arm = np.asarray([c["arm_peak_vel"] for c in sel], dtype=float)
    dur = np.asarray([c["duration_s"] for c in sel], dtype=float)
    dps = np.asarray([c.get("dist_m") or np.nan for c in sel], dtype=float)
    if arm.mean() == 0 or dur.mean() == 0:
        return None
    q = max(1, len(sel) // 4)
    q1, q4 = float(arm[:q].mean()), float(arm[-q:].mean())
    return {
        "stroke_count": float(len(sel)),
        "stroke_rate_spm": 60.0 / float(dur.mean()),
        "mean_arm_peak_vel_ms": float(arm.mean()),
        "cv_arm_peak_vel": float(arm.std() / arm.mean()),
        "mean_isi_s": float(dur.mean()),
        "cv_isi": float(dur.std() / dur.mean()),
        "mean_dps_m": float(np.nanmean(dps)) if not np.all(np.isnan(dps)) else None,
        "fatigue_index_pct": ((q1 - q4) / q1 * 100.0) if q1 else None,
    }


def _band(value, thr):
    """ratings.py _band, lower-is-better branch. Duplicated deliberately: importing
    ratings.py would make this tool's BEFORE run depend on the table D15 rewrites."""
    if value is None:
        return "unknown"
    if value <= thr["good"]:
        return "good"
    if value <= thr["ok"]:
        return "ok"
    return "needs_work"


CURRENT_THR = {
    "cv_arm_peak_vel": {"worst": 0.30, "ok": 0.20, "good": 0.10, "best": 0.03},
    "fatigue_index_pct": {"worst": 40.0, "ok": 20.0, "good": 8.0, "best": 0.0},
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stroke", help="filter to one stroke_type")
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--json", help="dump per-session results for before/after diffing")
    args = ap.parse_args()

    rows = _fetch(args.limit)
    if args.stroke:
        rows = [r for r in rows if r.get("stroke_type") == args.stroke]
    print(f"fetched {len(rows)} sessions"
          + (f" (stroke={args.stroke})" if args.stroke else ""))

    results = []
    positions = []
    n_tagged = 0
    for r in rows:
        cycles = ((r.get("metrics_json") or {}).get("cycles")) or []
        if len(cycles) < 2:
            continue
        # A stored row written BEFORE D5 carries "phase"; one written after does not.
        # Absence means the split is already gone, so both populations are identical —
        # which is exactly what the AFTER run should show.
        excluded = [i for i, c in enumerate(cycles) if c.get("phase") not in (None, "steady")]
        if excluded:
            n_tagged += 1
            positions += [i / max(1, len(cycles) - 1) for i in excluded]
        steady = [c for c in cycles if c.get("phase") in (None, "steady")]
        old, new = summarize(steady), summarize(cycles)
        if not old or not new:
            continue
        results.append({
            "id": r.get("id"),
            "stroke_type": r.get("stroke_type"),
            "created_at": r.get("created_at"),
            "sample_rate_hz": r.get("sample_rate_hz"),
            "n_cycles": len(cycles),
            "n_excluded": len(excluded),
            "old": old,
            "new": new,
        })

    n = len(results)
    if n == 0:
        sys.exit("No sessions with >=2 usable cycles.")

    print(f"sessions with >=2 usable cycles: {n}")
    print(f"sessions with >=1 excluded cycle: {n_tagged} ({100.0 * n_tagged / n:.0f}%)")
    if positions:
        p = np.asarray(positions)
        print(f"excluded-cycle position (0=first, 1=last): median {np.median(p):.2f}, "
              f"share in final 20% of swim: {100.0 * (p >= 0.8).mean():.0f}%")
        print("  -> near 1.0 means this filter marks the FINISH, not a ramp-up.")
    else:
        print("no excluded cycles found — the split is already gone (expected AFTER the change)")

    # ⚠ The per-session delta is reported over AFFECTED sessions only. Taking the median
    # across the whole corpus reports +0.0% for everything, because the ~60% of sessions
    # with no excluded cycle have a delta of exactly zero and dominate the median. That
    # is arithmetically true and completely misleading about the size of the change.
    affected = [r for r in results if r["n_excluded"] > 0]
    print(f"\ncorpus-wide percentiles (all {len(results)}), "
          f"delta over the {len(affected)} AFFECTED sessions only")
    print(f"{'metric':<24}{'old median':>13}{'new median':>13}{'old p90':>11}{'new p90':>11}"
          f"{'affected d%':>13}")
    print("-" * 86)
    for k in METRICS:
        o = np.asarray([r["old"][k] for r in results if r["old"].get(k) is not None], dtype=float)
        nw = np.asarray([r["new"][k] for r in results if r["new"].get(k) is not None], dtype=float)
        if o.size == 0 or nw.size == 0:
            continue
        pair = [(r["old"][k], r["new"][k]) for r in affected
                if r["old"].get(k) not in (None, 0) and r["new"].get(k) is not None]
        d = np.median([(b - a) / abs(a) * 100.0 for a, b in pair]) if pair else float("nan")
        print(f"{k:<24}{np.median(o):>13.3f}{np.median(nw):>13.3f}"
              f"{np.percentile(o, 90):>11.3f}{np.percentile(nw, 90):>11.3f}{d:>+12.1f}%")

    # Band distribution under the CURRENT anchors — the AC-3 discrimination check.
    print("\n=== band distribution under CURRENT anchors (AC-3 check) ===")
    for k in BAND_DRIVERS:
        for label, key in (("before", "old"), ("after ", "new")):
            bands = [_band(r[key].get(k), CURRENT_THR[k]) for r in results]
            counts = {b: bands.count(b) for b in ("good", "ok", "needs_work", "unknown")}
            total = max(1, len(bands))
            worst = max(counts.values()) / total
            flag = "  <-- NOT DISCRIMINATING (>60% one band)" if worst > 0.60 else ""
            print(f"  {k:<20} {label}  " +
                  "  ".join(f"{b} {c:>3} ({100.0*c/total:>3.0f}%)" for b, c in counts.items())
                  + flag)

    # Suggested re-anchors from the post-change distribution (D15).
    print("\n=== suggested anchors from the NEW distribution (D15) ===")
    for k in BAND_DRIVERS:
        v = np.asarray([r["new"][k] for r in results if r["new"].get(k) is not None], dtype=float)
        if v.size == 0:
            continue
        print(f"  {k:<20} worst {np.percentile(v, 90):>8.3f}  ok {np.percentile(v, 60):>8.3f}"
              f"  good {np.percentile(v, 30):>8.3f}  best {np.percentile(v, 10):>8.3f}")
    print("  (corpus percentiles, NOT coaching judgement — round away from test fixture values)")

    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
