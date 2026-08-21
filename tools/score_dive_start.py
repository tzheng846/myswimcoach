"""score_dive_start.py — Phase 79 accuracy harness for detect_dive_start.

Scores the coach's "dive_start is the FOOT of the first surge that clears X m/s" rule
against the hand-marked `dive_start_s` values in session_annotations, sweeping X, and
scores the rule it REPLACES — baseline_end (motion onset) — on the same sessions. Where
the detector refuses (no >=X surge) production falls back to baseline_end, so the sweep
reports the PRODUCTION-EFFECTIVE marker (detector where it fires, baseline_end elsewhere)
— which is exactly what ships — alongside the detector-only accuracy on the fired subset.

Committed so the chosen X and its MAE are reproducible, not a one-off chat measurement
(same precedent as tools/score_underwater.py / tools/score_segmenter.py).

    python tools/score_dive_start.py                 # full X sweep
    python tools/score_dive_start.py --x 2.0         # one X, with a per-session table

Read-only Supabase (service-role key from .env), same discipline as tools/score_underwater.py:
no write/update/delete, and no athlete PII printed — session id prefix and stroke type only.
"""
import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

# The local supabase/ folder shadows the installed supabase-py package — drop bare-path
# entries before importing, exactly as tools/score_underwater.py does.
sys.path = [p for p in sys.path if p not in ("", ".")]

import numpy as np                      # noqa: E402
from dotenv import load_dotenv          # noqa: E402
from supabase import create_client      # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))      # ...but DO let us import the project's own modules
import annotations as annot             # noqa: E402
import metrics                          # noqa: E402

SWEEP = (1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)
PROM_SWEEP = (0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30)   # foot-trough prominence, fraction of X
REF_X = 2.0


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
    """The PRISTINE auto metrics_json (the incumbent baseline_end lives here).

    ⚠ CIRCULARITY GUARD, same as score_segmenter._auto_metrics: once an annotation with
    >=2 cycle bounds is saved, the API recomputes metrics_json FROM that annotation and
    backs the original up to metrics_json_auto. Read baseline_end_s from the pristine auto
    result, never from a metrics_json that may itself have been recomputed.
    """
    auto = session.get("metrics_json_auto")
    if auto:
        return auto
    return session.get("metrics_json") or {}


def _load(sb):
    """Every annotated session that carries a hand-marked dive_start_s."""
    ann = {
        a["session_id"]: (a.get("phases") or {})
        for a in sb.table("session_annotations").select("session_id, phases").execute().data
    }
    ids = [k for k, v in ann.items() if v.get("dive_start_s") is not None]
    if not ids:
        sys.exit("No annotations with dive_start_s — nothing to score against.")
    rows = (
        sb.table("sessions")
        .select("id, stroke_type, sample_rate_hz, velocity_profile, "
                "metrics_json, metrics_json_auto")
        .in_("id", ids)
        .execute()
        .data
    )
    out = []
    for r in rows:
        # velocity_profile is stored once at /process and is NOT recomputed by the
        # annotation path, so reading it directly is non-circular.
        vel = _arr(r.get("velocity_profile"))
        if vel.size < 10:
            continue
        fs = float(r.get("sample_rate_hz") or annot.FS_HZ)
        sess = _auto_metrics(r).get("session") or {}
        baseline = sess.get("baseline_end_s")   # the incumbent motion-onset rule
        out.append({
            "id": r["id"],
            "stroke": r.get("stroke_type") or "none",
            "fs": fs,
            "vel": vel,
            "t": np.arange(vel.size) / fs,
            "truth": float(ann[r["id"]]["dive_start_s"]),
            "baseline": float(baseline) if baseline is not None else None,
        })
    return out


def _effective(s, x, prom=metrics._DIVE_FOOT_PROM_FRAC):
    """The PRODUCTION dive_start at threshold x / prominence prom: detector foot, else
    baseline_end. Returns (value_s, flag) where flag is det / fb / miss."""
    idx = metrics.detect_dive_start(s["t"], s["vel"], threshold=x, prom_frac=prom)
    if idx is not None:
        return idx / s["fs"], "det"
    if s["baseline"] is not None:
        return s["baseline"], "fb"
    return None, "miss"


def _run(sessions, x, prom):
    """Score every session at (x, prom); return (score_dict, per_session_rows)."""
    errs, misses, rows = [], 0, []
    for s in sessions:
        val, flag = _effective(s, x, prom)
        if val is None:
            misses += 1
            rows.append((s["stroke"], s["id"][:8], s["truth"], None, None, flag))
            continue
        errs.append(val - s["truth"])
        rows.append((s["stroke"], s["id"][:8], s["truth"], val, val - s["truth"], flag))
    return _score(errs, len(sessions), misses), rows


def _score(errs, n_total, misses):
    e = np.array(errs) if errs else np.array([0.0])
    return {
        "n": n_total,
        "scored": len(errs),
        "median": float(np.median(e)) if errs else float("nan"),
        "mean_abs": float(np.mean(np.abs(e))) if errs else float("nan"),
        "w05": int((np.abs(e) < 0.5).sum()) if errs else 0,
        "w10": int((np.abs(e) < 1.0).sum()) if errs else 0,
        "missed": misses,
    }


def _sweep_table(title, header, sweep, run):
    """Print one sweep table. run(k) -> (score, rows); header labels the swept column."""
    print(title)
    print(f"{header:>8} {'fired':>8} {'median':>9} {'mean|err|':>10} "
          f"{'<0.5s':>9} {'<1.0s':>9} {'missed':>7}")
    out = {}
    for k in sweep:
        r, rows = run(k)
        out[k] = (r, rows)
        fired = sum(1 for row in rows if row[5] == "det")
        print(f"{k:>8.2f} {fired:>5}/{r['n']:<2} {r['median']:>+8.2f}s {r['mean_abs']:>9.2f}s "
              f"{r['w05']:>5}/{r['n']:<3} {r['w10']:>5}/{r['n']:<3} {r['missed']:>7}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--x", type=float, default=None,
                    help="score a single threshold X and list per-session errors")
    ap.add_argument("--prom", type=float, default=None,
                    help="override the foot-trough prominence fraction (default: module constant)")
    args = ap.parse_args()

    sessions = _load(_client())
    n = len(sessions)
    prom0 = args.prom if args.prom is not None else metrics._DIVE_FOOT_PROM_FRAC
    print(f"Scoring detect_dive_start against {n} hand-marked dive_start_s values.\n")

    # ── X sweep at the reference prominence ───────────────────────────────────
    xs = (args.x,) if args.x is not None else SWEEP
    x_res = _sweep_table(
        f"PRODUCTION-EFFECTIVE X sweep at prom_frac={prom0:.2f} "
        f"(detector foot where a >=X surge fires, else baseline_end):",
        "X (m/s)", xs, lambda x: _run(sessions, x, prom0))

    # ── Prominence sweep at the reference X (rejects rising-edge ripples) ──────
    if args.x is None and args.prom is None:
        print()
        _sweep_table(
            f"PROMINENCE sweep at X={REF_X:.2f} (foot-trough min depth, fraction of X):",
            "prom", PROM_SWEEP, lambda p: _run(sessions, REF_X, p))

    # ── The incumbent this replaces: baseline_end everywhere ──────────────────
    base = [s for s in sessions if s["baseline"] is not None]
    be = np.array([s["baseline"] - s["truth"] for s in base])
    print(f"\nINCUMBENT (baseline_end_s — motion onset, today's dive_start):")
    if be.size:
        print(f"  scored {be.size}/{n}   median {np.median(be):+.2f}s   "
              f"mean|err| {np.mean(np.abs(be)):.2f}s   "
              f"within 0.5s {(np.abs(be) < 0.5).sum()}/{be.size}   "
              f"within 1.0s {(np.abs(be) < 1.0).sum()}/{be.size}")
    else:
        print(f"  no baseline_end_s available on any of the {n} sessions")

    # ── Detail at the reference X ─────────────────────────────────────────────
    ref = args.x if args.x is not None else (REF_X if REF_X in x_res else xs[0])
    results = {k: v[0] for k, v in x_res.items()}
    rows = x_res[ref][1]

    fired_errs = [r[4] for r in rows if r[5] == "det" and r[4] is not None]
    if fired_errs:
        fe = np.array(fired_errs)
        print(f"\nDETECTOR-ONLY at X={ref:.2f} (the {len(fe)} sessions with a real >=X surge):")
        print(f"  median {np.median(fe):+.2f}s   mean|err| {np.mean(np.abs(fe)):.2f}s   "
              f"within 0.5s {(np.abs(fe) < 0.5).sum()}/{len(fe)}")

    by = defaultdict(list)
    for stroke, _sid, _truth, _det, err, _flag in rows:
        if err is not None:
            by[stroke].append(err)
    print(f"\nPER-STROKE at X={ref:.2f} (production-effective):")
    for stroke in sorted(by):
        e = np.array(by[stroke])
        print(f"  {stroke:<12} n={len(e):<3} median {np.median(e):+.2f}s  "
              f"mean|err| {np.mean(np.abs(e)):.2f}s  within 0.5s {(np.abs(e) < 0.5).sum()}/{len(e)}")

    print(f"\nPER-SESSION at X={ref:.2f}  (flag: det=detector foot, fb=baseline_end fallback):")
    for stroke, sid, truth, det, err, flag in sorted(rows, key=lambda r: -abs(r[4] or 0)):
        d = f"{det:8.2f}" if det is not None else "    None"
        e = f"{err:+7.2f}" if err is not None else "  MISSED"
        print(f"  {stroke:<12}{sid:<10} human {truth:6.2f}  marker {d}  err {e}  [{flag}]")

    # ── AC-3 verdict ──────────────────────────────────────────────────────────
    if be.size and ref in results:
        eff = results[ref]["mean_abs"]
        inc = float(np.mean(np.abs(be)))
        print(f"\nAC-3 at X={ref:.2f}:  effective mean|err| {eff:.2f}s  vs  "
              f"incumbent baseline_end {inc:.2f}s   "
              f"{'PASS' if eff <= inc else 'FAIL'} (chosen-X MAE <= baseline_end MAE)")


if __name__ == "__main__":
    main()
