"""underwater_probe.py — Phase 65-01 diagnosis (measurement ONLY, no product code changed).

Why does the auto pipeline place `ip_end` (the start of cyclic stroking) INSIDE the underwater
dolphin-kick phase for free/back/fly, so the dive + kicks get segmented as stroke cycles?

This probe reconstructs each session from its STORED profiles (no raw-CSV download — the stored
velocity_profile IS run_pipeline's output that compute_session_metrics consumed), runs the real
metrics.py detectors WITHOUT editing them, and logs, per session:
  - detect_phases         → baseline_end, swim_end
  - detect_swim_window    → None, or (ip_end, swim_end)              [PRIMARY ip_end source]
  - detect_initial_phase  → initial_phase_end_idx                    [FALLBACK ip_end source]
  - compute_session_metrics(stroke_type=...) → the FINAL ip_end + cycle count
  - the CWT ridge: steady f_ref vs the underwater-span ridge frequency (the D8 2x-harmonic test)
  - ground truth: the coach's annotation stroke_start_s (the true breakout), when present
  - THREE candidate discriminating signals at the true breakout: frequency step-down, mean-velocity
    step, and the arm-pull SURGE in acceleration (Phase 66's new signal) vs the underwater kicks

    python tools/underwater_probe.py

Read-only Supabase (service-role key from .env), same discipline as tools/dataflow_probe.py: no
write/update/delete, no athlete PII printed (session id / generated name only).
"""
import argparse
import os
import sys
from pathlib import Path

# The local supabase/ folder shadows the installed supabase-py package — drop bare-path entries
# before importing, exactly as fetch_sessions.py:19 does.
sys.path = [p for p in sys.path if p not in ("", ".")]

import numpy as np                      # noqa: E402
from dotenv import load_dotenv          # noqa: E402
from supabase import create_client      # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))      # ...but DO let us import the project's own modules
import metrics                          # noqa: E402
import annotations as annot             # noqa: E402

STROKES = ("freestyle", "backstroke", "butterfly")
INDIGO = "indigo ray"


def _client():
    load_dotenv(REPO_ROOT / ".env")
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        sys.exit("Need SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
    return create_client(url, key)


def _arr(x):
    return np.array([np.nan if v is None else float(v) for v in (x or [])], dtype=float)


_COLS = "id, name, stroke_type, sample_rate_hz, velocity_profile, distance_profile, acceleration_profile"


def _fetch(sb, ids=None):
    # Targeted mode: measure specific session id(s). Generated display names (e.g. "indigo ray") are
    # NOT stored in sessions.name (Phase 61-05 derives them at render), so a session can only be
    # reached by uuid — the reason the name sweep below missed the reported bug's own session.
    if ids:
        rows = sb.table("sessions").select(_COLS).in_("id", ids).execute().data or []
        return [r for r in rows if r.get("velocity_profile")]
    rows = (sb.table("sessions").select(_COLS).in_("stroke_type", list(STROKES))
            .order("recorded_at", desc=True).limit(80).execute().data or [])
    have = {r["id"] for r in rows}
    named = sb.table("sessions").select(_COLS).eq("name", INDIGO).limit(3).execute().data or []
    rows += [r for r in named if r["id"] not in have]
    return [r for r in rows if r.get("velocity_profile")]


def _annotations(sb, ids):
    """session_id -> true breakout (phases.stroke_start_s), for annotated sessions only."""
    out = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        data = (sb.table("session_annotations").select("session_id, phases")
                .in_("session_id", chunk).execute().data or [])
        for r in data:
            ph = r.get("phases") or {}
            ss = ph.get("stroke_start_s")
            if ss is not None:
                out[r["session_id"]] = float(ss)
    return out


def _median(a):
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    return float(np.median(a)) if a.size else float("nan")


def analyze(row, breakout_s):
    stroke = row.get("stroke_type")
    vel = _arr(row.get("velocity_profile"))
    dist = _arr(row.get("distance_profile"))
    accel = _arr(row.get("acceleration_profile"))
    fs_raw = row.get("sample_rate_hz")
    fs = float(fs_raw) if fs_raw else annot.FS_HZ
    n = vel.size
    t = np.arange(n) / fs
    r = {"name": row.get("name") or row["id"][:8], "stroke": stroke, "fs": fs, "n": n,
         "fs_null": fs_raw is None, "breakout_s": breakout_s}

    # ── the three detectors, called exactly as compute_session_metrics does (:763-793) ──
    ph = metrics.detect_phases(t, vel)
    b_end = ph["baseline_end"]
    win = metrics.detect_swim_window(t, vel)                       # PRIMARY (None or (ip,end))
    ipf = metrics.detect_initial_phase(t, vel, b_end)["initial_phase_end_idx"]  # FALLBACK
    swim_end = ph["swim_end"]
    if win is not None:
        swim_end = min(max(int(win[1]), b_end + 1), n)
        final_ip = min(max(int(win[0]), b_end), swim_end - 1)
        source = "swim_window"
    else:
        final_ip = ipf
        source = "trough_fallback"

    res = metrics.compute_session_metrics(t, vel, dist, stroke_type=stroke)
    cycles = res.get("cycles") or []
    r.update({
        "b_end_s": b_end / fs,
        "win": None if win is None else (round(win[0] / fs, 2), round(win[1] / fs, 2)),
        "fallback_ip_s": ipf / fs,
        "final_ip_s": final_ip / fs,
        "source": source,
        "n_cycles": len(cycles),
    })

    # ── ridge: steady stroke frequency vs the underwater-span frequency (D8 harmonic test) ──
    ridge_freq, _ = metrics._cwt_ridge(vel, fs)
    if ridge_freq is not None:
        rf = np.asarray(ridge_freq, dtype=float)
        m = min(len(rf), n)
        # steady f_ref = back 60% of [final_ip, swim_end]; underwater = [b_end, final_ip]
        lo = final_ip + int(0.4 * max(swim_end - final_ip, 0))
        r["f_ref_hz"] = _median(rf[min(lo, m):min(swim_end, m)])
        r["uw_freq_hz"] = _median(rf[min(b_end, m):min(final_ip, m)]) if final_ip > b_end else float("nan")
        r["uw_over_ref"] = (r["uw_freq_hz"] / r["f_ref_hz"]) if r["f_ref_hz"] else float("nan")
    else:
        r["f_ref_hz"] = r["uw_freq_hz"] = r["uw_over_ref"] = float("nan")

    # ── ground-truth-anchored measurements (annotated sessions only) ──
    if breakout_s is not None:
        bk = int(round(breakout_s * fs))
        r["ip_err_s"] = final_ip / fs - breakout_s
        r["cycles_before_breakout"] = sum(1 for c in cycles if c.get("start_idx", 0) / fs < breakout_s - 1e-6)
        uw = slice(max(b_end, 0), max(bk, b_end + 1))                 # true underwater
        sf = slice(bk, min(bk + int(3 * fs), n))                      # first ~3 s of surface stroking
        # discriminating signals at the breakout:
        r["meanvel_uw"] = _median(np.abs(vel[uw]))
        r["meanvel_surf"] = _median(np.abs(vel[sf]))
        # arm-pull surge = peak POSITIVE acceleration (the catch). Kicks oscillate ~symmetrically;
        # an arm pull is a sustained positive surge. Compare surface peak to underwater peak.
        if accel.size == n:
            r["accel_surge_uw"] = float(np.nanmax(accel[uw])) if uw.stop > uw.start else float("nan")
            r["accel_surge_surf"] = float(np.nanmax(accel[sf])) if sf.stop > sf.start else float("nan")
            r["accel_surge_ratio"] = (r["accel_surge_surf"] / r["accel_surge_uw"]
                                      if r.get("accel_surge_uw") else float("nan"))
        else:
            r["accel_surge_uw"] = r["accel_surge_surf"] = r["accel_surge_ratio"] = float("nan")
    return r


def main():
    ap = argparse.ArgumentParser(description="Phase 65-01 underwater breakout probe")
    ap.add_argument("--id", action="append", default=None,
                    help="measure specific session id(s) by uuid (repeatable); bypasses the sweep")
    args = ap.parse_args()

    sb = _client()
    rows = _fetch(sb, ids=args.id)
    anns = _annotations(sb, [r["id"] for r in rows])

    if args.id:
        picked = rows  # measure exactly what was asked for
    else:
        # Prefer annotated sessions (they carry ground truth); always keep indigo ray; span strokes.
        def key(r):
            return (r["id"] not in anns, r.get("name") != INDIGO, r.get("stroke_type"))
        rows.sort(key=key)
        picked, per_stroke = [], {}
        for r in rows:
            s = r.get("stroke_type")
            annotated = r["id"] in anns
            # keep all annotated free/back/fly + indigo ray; cap unannotated at 1 per stroke
            if annotated or r.get("name") == INDIGO or per_stroke.get(s, 0) < 1:
                picked.append(r)
                per_stroke[s] = per_stroke.get(s, 0) + 1
        picked = picked[:12]

    print(f"\nUnderwater breakout probe — {len(picked)} sessions "
          f"({sum(r['id'] in anns for r in picked)} annotated)\n")
    results = []
    for r in picked:
        try:
            results.append(analyze(r, anns.get(r["id"])))
        except Exception as e:  # noqa: BLE001 — one bad session must not abort the sweep
            print(f"  {r.get('name') or r['id'][:8]} — ERROR {type(e).__name__}: {e}")

    hdr = f"{'name':<16}{'stroke':<11}{'fs':>5}{'b_end':>6}{'win?':>6}{'fallbk':>7}{'final_ip':>9}{'source':>16}{'cyc':>4}"
    print(hdr); print("-" * len(hdr))
    for r in results:
        print(f"{r['name'][:15]:<16}{r['stroke'][:10]:<11}{r['fs']:>5.0f}{r['b_end_s']:>6.1f}"
              f"{('Y' if r['win'] else 'N'):>6}{r['fallback_ip_s']:>7.1f}{r['final_ip_s']:>9.1f}"
              f"{r['source']:>16}{r['n_cycles']:>4}")

    print("\nRidge frequency (D8: is the underwater span at ~2x the steady stroke rate?)")
    print(f"{'name':<16}{'f_ref':>7}{'uw_freq':>9}{'uw/ref':>8}")
    for r in results:
        print(f"{r['name'][:15]:<16}{r['f_ref_hz']:>7.2f}{r['uw_freq_hz']:>9.2f}{r['uw_over_ref']:>8.2f}")

    print("\nGround-truth (annotated only): ip_end error + discriminating signals at the breakout")
    print(f"{'name':<16}{'true_bk':>8}{'ip_err':>7}{'cyc<bk':>7}{'mv_uw':>7}{'mv_sf':>7}{'a_uw':>7}{'a_sf':>7}{'a_sf/uw':>8}")
    for r in results:
        if r.get("breakout_s") is None:
            continue
        print(f"{r['name'][:15]:<16}{r['breakout_s']:>8.2f}{r['ip_err_s']:>7.2f}{r['cycles_before_breakout']:>7d}"
              f"{r['meanvel_uw']:>7.2f}{r['meanvel_surf']:>7.2f}{r['accel_surge_uw']:>7.1f}"
              f"{r['accel_surge_surf']:>7.1f}{r['accel_surge_ratio']:>8.2f}")

    print(f"\nConstants: _WINDOW_MIN_CYCLES={metrics._WINDOW_MIN_CYCLES} "
          f"_WINDOW_FREQ_TOL={metrics._WINDOW_FREQ_TOL} _WINDOW_HOLD_CYCLES={metrics._WINDOW_HOLD_CYCLES} "
          f"_WINDOW_POWER_FRAC={metrics._WINDOW_POWER_FRAC}")
    print("mv=mean|vel| (m/s), a=peak +accel surge (m/s^2), uw=underwater, sf=first 3s surface.\n")


if __name__ == "__main__":
    main()
