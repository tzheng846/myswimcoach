"""Candidate swim-window detectors, scored against human annotations (Phase 59-03 Task 1).

RESEARCH ONLY. Nothing here is imported by metrics.py. Candidates live in tools/ so a dead
end costs nothing (Phase 59 quarantine rule); the winner is copied into metrics.py by Task 2.

THE PROBLEM
-----------
`detect_phases` asks "where does MOTION start and stop" and `detect_initial_phase` asks
"where is the first deep trough". The coach marked "where does CYCLIC STROKING start and
stop". Phase 59-01/59-03 measured the consequence: `ip_end` lands 3.88 s early and
`swim_end` 3.55 s late (median |error|), and the resulting window is >5 s too wide on 19
of 22 sessions.

TWO FACTS ANY CANDIDATE MUST RESPECT — both established by measurement, do not re-derive:

  1. An AMPLITUDE threshold cannot find `finish`. Mean |vel| in the over-run region is
     0.403 m/s, EIGHT TIMES `_BASELINE_THRESH` (0.05). The swimmer really is still moving
     after the touch — drifting, pushing off. It is fast but NOT RHYTHMIC.

  2. A TROUGH cannot find `ip_end`. In 12 of 23 sessions the first qualifying trough is
     already the nearest one to the human mark and is still 0.6-6.1 s early; several
     freestyle traces contain exactly ONE qualifying trough in the whole 15 s search.
     Underwater dolphin kicking IS rhythmic, but at roughly twice the stroke frequency.

So: amplitude separates neither boundary. RHYTHM separates `finish` (drift is aperiodic),
and rhythm AT THE STROKE FREQUENCY separates `ip_end` (kicking is off-band).

Usage:
    python tools/window_candidates.py                    # fetch from Supabase
    python tools/window_candidates.py --export raw.json  # offline, cached input
"""
import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# Import the real supabase package BEFORE the repo root goes on sys.path — the local
# supabase/ SQL directory shadows it. Order is load-bearing; see score_segmenter.py.
sys.path = [p for p in sys.path if p not in ("", ".", str(_ROOT))]
try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd

import annotations as annot
import metrics as m
import segmenter_eval as se

# Current-detector baselines, from 59-01. A candidate must beat these to be worth shipping.
BASELINE_IP_MAE = 3.88
BASELINE_FIN_MAE = 3.55


# ── shared signal helpers ────────────────────────────────────────────────────

def _rhythm_envelope(vel, fs, win_s=1.5):
    """RMS of the detrended signal — 'how much rhythmic content is here right now'.

    Detrending subtracts a 3 s rolling mean, which is precisely what kills post-touch
    DRIFT: a swimmer coasting at a near-constant 0.4 m/s detrends to ~0, while a stroking
    swimmer oscillating about their mean does not. This is the whole reason an amplitude
    threshold fails and this one can work.
    """
    d = m._detrend_for_cwt(np.nan_to_num(vel), fs)
    w = max(3, int(win_s * fs))
    return np.sqrt(pd.Series(d ** 2).rolling(w, center=True, min_periods=1).mean().values)


def _ridge_freq(vel, fs):
    """Instantaneous dominant frequency (Hz) via the same CWT ridge the segmenter uses."""
    import pywt
    d = m._detrend_for_cwt(np.nan_to_num(vel), fs)
    if not np.any(np.isfinite(d)) or float(np.max(np.abs(d))) < 1e-9:
        return None, None
    dt = 1.0 / fs
    target = np.geomspace(1.0 / m._PERIOD_MAX_S, 1.0 / m._PERIOD_MIN_S, m._N_SCALES)
    scales = pywt.central_frequency(m._WAVELET) / (target * dt)
    coeffs, freqs = pywt.cwt(d, scales, m._WAVELET, sampling_period=dt)
    power = np.abs(coeffs) ** 2
    idx = m._track_ridge(power, freqs)
    return freqs[idx], power[idx, np.arange(power.shape[1])]


def _longest_run(mask, fs, min_gap_s=1.0):
    """Longest contiguous True run, after bridging gaps shorter than min_gap_s.

    Gap-bridging matters: a single slow stroke or a breath can dip the envelope below
    threshold mid-swim, and without bridging the window would be truncated at that dip.
    """
    if not mask.any():
        return None
    m_ = mask.copy()
    gap = max(1, int(min_gap_s * fs))
    idx = np.flatnonzero(m_)
    for a, b in zip(idx[:-1], idx[1:]):
        if 1 < b - a <= gap:
            m_[a:b] = True
    idx = np.flatnonzero(m_)
    splits = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[splits + 1]]
    ends = np.r_[idx[splits], idx[-1]]
    best = int(np.argmax(ends - starts))
    return int(starts[best]), int(ends[best]) + 1


# ── candidates ───────────────────────────────────────────────────────────────

def cand_envelope(t, vel, fs, frac=0.35):
    """A: rhythm envelope over a fraction of its own in-swim peak."""
    env = _rhythm_envelope(vel, fs)
    ref = float(np.percentile(env, 95))
    if ref < 1e-9:
        return None
    return _longest_run(env > frac * ref, fs)


def cand_envelope_band(t, vel, fs, frac=0.35):
    """B: envelope AND the local dominant period inside the stroke band.

    Adds the constraint that separates underwater kicking from stroking — kicking is
    rhythmic but roughly twice the stroke frequency, so it falls outside the band that the
    swim's own median ridge frequency defines.
    """
    env = _rhythm_envelope(vel, fs)
    ref = float(np.percentile(env, 95))
    if ref < 1e-9:
        return None
    rf, _ = _ridge_freq(vel, fs)
    if rf is None:
        return None
    amp = env > frac * ref
    if not amp.any():
        return None
    f_med = float(np.median(rf[amp]))
    in_band = (rf > 0.65 * f_med) & (rf < 1.55 * f_med)
    return _longest_run(amp & in_band, fs)


def cand_ridge_power(t, vel, fs, frac=0.25):
    """C: CWT ridge POWER, rather than broadband RMS."""
    rf, rp = _ridge_freq(vel, fs)
    if rp is None:
        return None
    rp = np.sqrt(np.maximum(rp, 0))
    ref = float(np.percentile(rp, 95))
    if ref < 1e-9:
        return None
    return _longest_run(rp > frac * ref, fs)


def cand_settle(t, vel, fs, frac=0.25, tol=0.30, hold_cycles=1.0):
    """D: ridge power for `finish`, frequency SETTLING for `ip_end`.

    A and B both fail `ip_end` by 4-8 s and always EARLY, because underwater dolphin
    kicking is rhythmic and an amplitude-or-band test happily accepts it. B's band filter
    could not reject it either: its reference median was computed over a mask that
    INCLUDED the kicking, so the band centred on the wrong frequency.

    The discriminator is the frequency TRANSITION. Kicking runs at roughly twice the
    stroke rate, so at breakout the ridge frequency roughly halves and then holds steady.
    So: take the steady-state stroke frequency from the LATTER part of the swim — which is
    unambiguously stroking — and call `ip_end` the first sustained moment the ridge settles
    near it.
    """
    rf, rp = _ridge_freq(vel, fs)
    if rp is None:
        return None
    amp = np.sqrt(np.maximum(rp, 0))
    ref = float(np.percentile(amp, 95))
    if ref < 1e-9:
        return None
    run = _longest_run(amp > frac * ref, fs)
    if run is None:
        return None
    i0, i1 = run

    # Steady-state stroke frequency: the back 60% of the active region is past any
    # breakout, so it is stroking by construction.
    back = rf[i0 + int(0.4 * (i1 - i0)):i1]
    if back.size < 3:
        return run
    f_ref = float(np.median(back))
    if f_ref <= 0:
        return run

    near = np.abs(rf - f_ref) <= tol * f_ref
    hold = max(1, int(hold_cycles / f_ref * fs))
    # First index within [i0, i1) where `near` holds continuously for one cycle.
    c = 0
    for i in range(i0, i1):
        c = c + 1 if near[i] else 0
        if c >= hold:
            return int(i - hold + 1), i1
    return run


CANDIDATES = {
    "A_envelope": cand_envelope,
    "B_env+band": cand_envelope_band,
    "C_ridgepow": cand_ridge_power,
    "D_settle": cand_settle,
}


# ── pairing wrapper (the 59-03 Task 3 change, previewed here for the gate) ────

def _paired(t_seg, vel_seg):
    cyc = m.segment_cycles_wavelet(t_seg, vel_seg)
    if not cyc:
        return cyc
    b = ([c["start_idx"] for c in cyc] + [cyc[-1]["end_idx"]])[0::2]
    out = []
    for i in range(len(b) - 1):
        if b[i + 1] - b[i] >= 2:
            out.append({"cycle_num": len(out), "start_idx": b[i], "end_idx": b[i + 1],
                        "peak_idx": b[i] + int(np.argmax(vel_seg[b[i]:b[i + 1]]))})
    return out or None


def _rate_with(t, vel, dist, ip, swim_end, stroke):
    m.SEGMENTER_BY_STROKE["freestyle"] = _paired
    m.SEGMENTER_BY_STROKE["backstroke"] = _paired
    try:
        man = {"ip_end_idx": int(ip), "swim_end_idx": int(swim_end)}
        return m.compute_session_metrics(t, vel, dist, manual=man,
                                         stroke_type=stroke)["session"]["stroke_rate_spm"]
    finally:
        m.SEGMENTER_BY_STROKE.clear()


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
    url, key = os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        sys.exit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    sb = create_client(url, key)
    anns = (sb.table("session_annotations")
            .select("session_id, phases, stroke_marks_s").execute().data) or []
    rows = (sb.table("sessions")
            .select("id, stroke_type, created_at, sample_rate_hz, velocity_profile")
            .in_("id", [a["session_id"] for a in anns]).execute().data) or []
    by_id = {r["id"]: r for r in rows}
    return [{"annotation": a, "session": by_id[a["session_id"]]}
            for a in anns if a["session_id"] in by_id]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", help="cached input JSON (offline)")
    args = ap.parse_args()

    recs = _load(args.export)
    per_cand = {k: {"ip": [], "fin": [], "ratio": [], "miss": 0} for k in CANDIDATES}
    cur = {"ip": [], "fin": []}
    rows = []

    for r in recs:
        s, a = r["session"], r["annotation"]
        st = s.get("stroke_type") or "?"
        fs = float(s.get("sample_rate_hz") or annot.FS_HZ)
        vel = np.asarray(s.get("velocity_profile") or [], float)
        if vel.size < 200:
            continue
        t = np.arange(vel.size) / fs
        dist = np.concatenate(([0.0], np.cumsum(np.maximum(vel[:-1], 0)) / fs))
        ph = a.get("phases") or {}
        hs, hf = ph.get("stroke_start_s"), ph.get("finish_s")
        marks = sorted(a.get("stroke_marks_s") or [])
        tc = marks[0::annot.marks_per_cycle(st)]
        human_rate = 60.0 / float(np.mean(np.diff(tc))) if len(tc) >= 3 else None

        p = m.detect_phases(t, vel)
        cur_ip = m.detect_initial_phase(t, vel, p["baseline_end"])["initial_phase_end_idx"] / fs
        cur_fin = p["swim_end"] / fs
        if hs is not None:
            cur["ip"].append(abs(cur_ip - hs))
        if hf is not None:
            cur["fin"].append(abs(cur_fin - hf))

        row = {"when": (s.get("created_at") or "")[5:19], "stroke": st, "c": {}}
        for name, fn in CANDIDATES.items():
            try:
                w = fn(t, vel, fs)
            except Exception:
                w = None
            if w is None:
                per_cand[name]["miss"] += 1
                row["c"][name] = None
                continue
            i0, i1 = w
            if hs is not None:
                per_cand[name]["ip"].append(abs(i0 / fs - hs))
            if hf is not None:
                per_cand[name]["fin"].append(abs(i1 / fs - hf))
            ratio = None
            if human_rate and st in ("freestyle", "backstroke"):
                try:
                    v = _rate_with(t, vel, dist, i0, i1, st) / human_rate
                    # A degenerate window can yield no steady cycles -> NaN rate. Count it
                    # as a miss rather than poisoning the median with NaN.
                    if v == v and np.isfinite(v):
                        ratio = v
                        per_cand[name]["ratio"].append(v)
                    else:
                        per_cand[name]["miss"] += 1
                except Exception:
                    per_cand[name]["miss"] += 1
            row["c"][name] = (i0 / fs - (hs or 0), i1 / fs - (hf or 0), ratio)
        rows.append(row)

    print("=" * 104)
    print(f"WINDOW CANDIDATES vs human marks   n={len(rows)} sessions")
    print(f"current detector baseline: ip_end MAE {BASELINE_IP_MAE:.2f}s, "
          f"finish MAE {BASELINE_FIN_MAE:.2f}s")
    print("=" * 104)
    hdr = f'{"when":<15}{"stroke":<13}'
    for k in CANDIDATES:
        hdr += f'{k+" ip/fin":>22}'
    print(hdr)
    for r in sorted(rows, key=lambda r: r["when"]):
        line = f'{r["when"]:<15}{r["stroke"]:<13}'
        for k in CANDIDATES:
            v = r["c"][k]
            line += f'{"      none":>22}' if v is None else f'{v[0]:>+11.1f}{v[1]:>+11.1f}'
        print(line)

    print(f'\n{"candidate":<14}{"ip MAE":>9}{"fin MAE":>9}{"none":>6}'
          f'{"ratio med":>11}{"in +-15%":>10}')
    print(f'{"CURRENT":<14}{np.median(cur["ip"]):>9.2f}{np.median(cur["fin"]):>9.2f}'
          f'{0:>6}{"1.647":>11}{"0/12":>10}')
    for k, d in per_cand.items():
        ipm = np.median(d["ip"]) if d["ip"] else float("nan")
        fim = np.median(d["fin"]) if d["fin"] else float("nan")
        rat = d["ratio"]
        med = np.median(rat) if rat else float("nan")
        ok = sum(1 for x in rat if 0.85 <= x <= 1.15)
        print(f'{k:<14}{ipm:>9.2f}{fim:>9.2f}{d["miss"]:>6}{med:>11.3f}'
              f'{f"{ok}/{len(rat)}":>10}')
    # Per-stroke breakdown (AC-1: the improvement must hold per stroke, not just in aggregate)
    print(f'\n{"PER-STROKE |error|, median (s)":<32}{"ip_end":>18}{"finish":>18}')
    print(f'{"":<32}{"current":>9}{"best":>9}{"current":>9}{"best":>9}')
    best = max(CANDIDATES, key=lambda k: (0.85 <= np.median(per_cand[k]["ratio"] or [0]) <= 1.15,
                                          -np.median(per_cand[k]["ip"] or [99])))
    for stroke in ("freestyle", "butterfly", "breaststroke"):
        ci, cf, bi, bf = [], [], [], []
        for r in rows:
            if r["stroke"] != stroke:
                continue
            rec = [x for x in recs if (x["session"].get("created_at") or "")[5:19] == r["when"]][0]
            s, a = rec["session"], rec["annotation"]
            fs = float(s.get("sample_rate_hz") or annot.FS_HZ)
            vel = np.asarray(s["velocity_profile"], float)
            t = np.arange(vel.size) / fs
            ph = a.get("phases") or {}
            p = m.detect_phases(t, vel)
            cip = m.detect_initial_phase(t, vel, p["baseline_end"])["initial_phase_end_idx"] / fs
            if ph.get("stroke_start_s") is not None:
                ci.append(abs(cip - ph["stroke_start_s"]))
            if ph.get("finish_s") is not None:
                cf.append(abs(p["swim_end"] / fs - ph["finish_s"]))
            v = r["c"][best]
            if v is not None:
                if ph.get("stroke_start_s") is not None:
                    bi.append(abs(v[0]))
                if ph.get("finish_s") is not None:
                    bf.append(abs(v[1]))
        if ci:
            print(f'  {stroke:<30}{np.median(ci):>9.2f}{np.median(bi):>9.2f}'
                  f'{np.median(cf):>9.2f}{np.median(bf):>9.2f}')
    print(f'  (best = {best})')

    print("\nGATE (AC-2): median ratio in 0.85-1.15 AND median |log ratio| < 0.50")
    for k, d in per_cand.items():
        if d["ratio"]:
            lg = float(np.median(np.abs(np.log(d["ratio"]))))
            print(f"  {k:<14} |log| {lg:.3f}   {'PASS' if 0.85 <= np.median(d['ratio']) <= 1.15 and lg < 0.50 else 'fail'}")


if __name__ == "__main__":
    main()
