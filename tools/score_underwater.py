"""score_underwater.py — Phase 75-02 accuracy harness for detect_underwater_start.

Scores the coach's "the underwater phase begins at the first big velocity dip" rule
against the hand-marked `underwater_start_s` values in session_annotations, and scores
the rule it REPLACES — `baseline_end_s + dive_duration_s`, the top of the dive surge —
on the same sessions for comparison.

This is the harness that produced the numbers in 75-02-PLAN.md. Committed so the claim
is reproducible rather than a one-off measurement in a chat log (same precedent as
tools/score_segmenter.py).

    python tools/score_underwater.py                 # full prominence sweep
    python tools/score_underwater.py --prom 0.40     # one value, with a per-session table

Read-only Supabase (service-role key from .env), same discipline as
tools/underwater_probe.py and tools/dataflow_probe.py: no write/update/delete, and no
athlete PII printed — session id prefix and stroke type only.
"""
import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

# The local supabase/ folder shadows the installed supabase-py package — drop bare-path
# entries before importing, exactly as fetch_sessions.py:19 does.
sys.path = [p for p in sys.path if p not in ("", ".")]

import numpy as np                      # noqa: E402
from dotenv import load_dotenv          # noqa: E402
from scipy.signal import find_peaks     # noqa: E402
from supabase import create_client      # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))      # ...but DO let us import the project's own modules
import annotations as annot             # noqa: E402
import metrics                          # noqa: E402

SWEEP = (0.25, 0.30, 0.35, 0.40, 0.50, 0.60)


def _client():
    load_dotenv(REPO_ROOT / ".env")
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        sys.exit("Need SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
    return create_client(url, key)


def _arr(x):
    return np.array([np.nan if v is None else float(v) for v in (x or [])], dtype=float)


def _detect_at(vel, fs, start_idx, prom_frac):
    """detect_underwater_start with an overridable prominence, for the sweep.

    Mirrors metrics.detect_underwater_start exactly; the only difference is that the
    prominence fraction is a parameter instead of the module constant. Kept in sync by
    the AC-1 check below, which asserts the two agree at the shipped constant.
    """
    seg = vel[start_idx:]
    if len(seg) < int(fs):
        return None
    v95 = float(np.nanpercentile(np.abs(seg), 95))
    if not np.isfinite(v95) or v95 <= 0:
        return None
    lim = int(metrics._UW_SURGE_WINDOW_S * fs)
    head = seg[:lim] if len(seg) > lim else seg
    if not np.any(np.isfinite(head)):
        return None
    pk = int(np.nanargmax(head))
    tail = seg[pk:]
    if len(tail) < 3:
        return None
    troughs, _ = find_peaks(-tail, prominence=prom_frac * v95)
    if len(troughs) == 0:
        return None
    return start_idx + pk + int(troughs[0])


def _load(sb):
    """Every annotated session that carries a hand-marked underwater_start_s."""
    ann = {
        a["session_id"]: (a.get("phases") or {})
        for a in sb.table("session_annotations").select("session_id, phases").execute().data
    }
    ids = [k for k, v in ann.items() if v.get("underwater_start_s") is not None]
    if not ids:
        sys.exit("No annotations with underwater_start_s — nothing to score against.")
    rows = (
        sb.table("sessions")
        .select("id, stroke_type, sample_rate_hz, velocity_profile, metrics_json")
        .in_("id", ids)
        .execute()
        .data
    )
    out = []
    for r in rows:
        vel = _arr(r.get("velocity_profile"))
        if vel.size < 10:
            continue
        fs = float(r.get("sample_rate_hz") or annot.FS_HZ)
        mj = r.get("metrics_json") or {}
        seed = annot.build_seed(mj, fs)["phases"]
        dive_s = seed.get("dive_start_s")
        # The INCUMBENT rule, read straight off the stored metrics rather than the seed,
        # so build_seed's ordering-walk can't mask a null. This is what it always was:
        # the first prominent PEAK after motion starts = the top of the dive.
        ip = mj.get("initial_phase") or {}
        legacy = None
        sess = mj.get("session") or {}
        if ip.get("dive_detected") and sess.get("baseline_end_s") is not None \
                and ip.get("dive_duration_s") is not None:
            legacy = float(sess["baseline_end_s"]) + float(ip["dive_duration_s"])
        out.append({
            "id": r["id"],
            "stroke": r.get("stroke_type") or "none",
            "fs": fs,
            "vel": vel,
            "truth": float(ann[r["id"]]["underwater_start_s"]),
            "dive_idx": int(round((dive_s or 0.0) * fs)),
            "legacy": legacy,
        })
    return out


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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prom", type=float, default=None,
                    help="score a single prominence fraction and list per-session errors")
    args = ap.parse_args()

    sessions = _load(_client())
    n = len(sessions)
    print(f"Scoring detect_underwater_start against {n} hand-marked underwater_start_s values.\n")

    fracs = (args.prom,) if args.prom is not None else SWEEP
    results = {}
    per_session = {}
    for pf in fracs:
        errs, misses, rows = [], 0, []
        for s in sessions:
            idx = _detect_at(s["vel"], s["fs"], s["dive_idx"], pf)
            if idx is None:
                misses += 1
                rows.append((s["stroke"], s["id"][:8], s["truth"], None, None))
                continue
            det = idx / s["fs"]
            errs.append(det - s["truth"])
            rows.append((s["stroke"], s["id"][:8], s["truth"], det, det - s["truth"]))
        results[pf] = _score(errs, n, misses)
        per_session[pf] = rows

    print(f"{'prom_frac':>10} {'median err':>11} {'mean|err|':>10} {'within 0.5s':>12} "
          f"{'within 1.0s':>12} {'missed':>7}")
    for pf, r in results.items():
        print(f"{pf:>10.2f} {r['median']:>10.2f}s {r['mean_abs']:>9.2f}s "
              f"{r['w05']:>7}/{r['n']:<4} {r['w10']:>7}/{r['n']:<4} {r['missed']:>7}")

    # ── The rule this replaces ────────────────────────────────────────────────
    leg = [s for s in sessions if s["legacy"] is not None]
    le = [s["legacy"] - s["truth"] for s in leg]
    print(f"\nINCUMBENT (baseline_end_s + dive_duration_s — the top of the dive surge):")
    if le:
        le = np.array(le)
        print(f"  fires on {len(leg)} of {n} annotated sessions "
              f"(null on the rest: detect_initial_phase needs TWO peaks to set dive_detected)")
        print(f"  median err {np.median(le):+.2f}s   mean|err| {np.mean(np.abs(le)):.2f}s   "
              f"within 0.5s {(np.abs(le) < 0.5).sum()}/{len(leg)}   "
              f"within 1.0s {(np.abs(le) < 1.0).sum()}/{len(leg)}")
    else:
        print(f"  fires on 0 of {n} annotated sessions")

    # ── Per-stroke + outliers at the shipped constant ─────────────────────────
    shipped = metrics._UW_START_PROM_FRAC
    ref = shipped if shipped in per_session else fracs[0]
    by = defaultdict(list)
    for stroke, _sid, _truth, _det, err in per_session[ref]:
        if err is not None:
            by[stroke].append(err)
    print(f"\nPER-STROKE at prom {ref:.2f}:")
    for stroke in sorted(by):
        e = np.array(by[stroke])
        print(f"  {stroke:<12} n={len(e):<3} median {np.median(e):+.2f}s  "
              f"mean|err| {np.mean(np.abs(e)):.2f}s  within 0.5s {(np.abs(e) < 0.5).sum()}/{len(e)}")

    print(f"\nSESSIONS OFF BY MORE THAN 0.5 s at prom {ref:.2f}:")
    bad = [r for r in per_session[ref] if r[4] is None or abs(r[4]) > 0.5]
    if not bad:
        print("  none")
    for stroke, sid, truth, det, err in sorted(bad, key=lambda r: -abs(r[4] or 99)):
        d = f"{det:8.2f}" if det is not None else "    None"
        e = f"{err:+7.2f}" if err is not None else "  MISSED"
        print(f"  {stroke:<12}{sid:<10} human {truth:6.2f}  detected {d}  err {e}")

    # ── AC-1 ──────────────────────────────────────────────────────────────────
    if shipped in results:
        r = results[shipped]
        agree = sum(
            1 for s in sessions
            if _detect_at(s["vel"], s["fs"], s["dive_idx"], shipped)
            == metrics.detect_underwater_start(
                np.arange(s["vel"].size) / s["fs"], s["vel"], s["dive_idx"])
        )
        print(f"\nAC-1 at the shipped constant _UW_START_PROM_FRAC = {shipped}:")
        print(f"  mean |err| {r['mean_abs']:.2f}s <= 0.30       {'PASS' if r['mean_abs'] <= 0.30 else 'FAIL'}")
        print(f"  within 0.5 s {r['w05']}/{r['n']} >= 30            "
              f"{'PASS' if r['w05'] >= 30 else 'FAIL'}")
        print(f"  no-detects {r['missed']} == 0                 "
              f"{'PASS' if r['missed'] == 0 else 'FAIL'}")
        print(f"  harness agrees with metrics.py on {agree}/{n}  "
              f"{'PASS' if agree == n else 'FAIL'}")


if __name__ == "__main__":
    main()
