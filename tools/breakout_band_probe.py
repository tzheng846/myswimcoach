"""breakout_band_probe.py — test the USER'S breakout hypothesis (2026-08-20, read-only).

HYPOTHESIS (user, verbatim): "dolphin kick is mostly cyclic, so there's a band of frequency
that's active for an extended period of time. Then it's when that frequency disappears, you
know breakout started. But this assumes that underwater dolphin kicks exist."

So: the underwater dolphin-kick phase should show SUSTAINED power in a KICK BAND (~1.8-3 Hz,
ABOVE the stroke band ~0.8-1.3 Hz and ABOVE production's 0.25-2.0 Hz ridge window — which is
precisely why the ridge detectors never saw it). Breakout = where that band's power drops off.

This probe does two things against the coach's `stroke_start_s` ground truth:
  1. CHARACTERISE (uses ground truth): is there a distinct sustained kick band? where (Hz)?
     does its power actually drop at the true breakout? (kick-band power uw-window vs surface)
  2. DETECT (no ground truth): find the sustained kick-band run after underwater_start, mark
     its END as the candidate breakout, and score |candidate - true stroke_start_s| against
     the current detector's residual.

Read-only Supabase (service-role key from .env), same discipline as tools/underwater_probe.py:
no write, no PII printed (session id prefix / stroke only).

PHASE 77 addition: butterfly gets its own section, scoring the shipped
metrics.detect_breakout_fly (arm-cycle APPEARANCE - the arm/fundamental band-power ratio)
against the same marks, plus the P_surface/P_uw fingerprint, the band-edge jitter grid, the
contrast-gate sweep, and the annotated-vs-auto underwater-start seam check. The kick-band
columns are retained for fly because they are the measurement that REJECTED the kick rule
there (4.46 s vs a 2.43 s incumbent).

    python tools/breakout_band_probe.py
    python tools/breakout_band_probe.py --plot   # also dump PNGs to the scratchpad
"""
import argparse
import os
import sys
from pathlib import Path

# The local supabase/ folder shadows the installed supabase-py package — drop bare-path
# entries before importing, exactly as underwater_probe.py:30 does.
sys.path = [p for p in sys.path if p not in ("", ".")]

import numpy as np                      # noqa: E402
import pywt                             # noqa: E402
from dotenv import load_dotenv          # noqa: E402
from supabase import create_client      # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))      # ...but let us import the project's own modules
import metrics                          # noqa: E402
import annotations as annot             # noqa: E402

STROKES = ("freestyle", "backstroke", "butterfly")   # the dolphin-kick strokes (breast = pulldown)

# Scalogram band — WIDER than production (_PERIOD_MIN_S/_MAX_S => 0.25-2.0 Hz) so the kick
# band is actually visible. cmor1.5-1.0 to match metrics.py.
_F_LO, _F_HI, _N_F = 0.5, 5.0, 96
_KICK_LO, _KICK_HI = 1.8, 3.2   # dolphin-kick band (tunable — v1 fixed guess)
_STROKE_LO, _STROKE_HI = 0.7, 1.5


def _client():
    load_dotenv(REPO_ROOT / ".env")
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        sys.exit("Need SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
    return create_client(url, key)


def _arr(x):
    return np.array([np.nan if v is None else float(v) for v in (x or [])], dtype=float)


_COLS = "id, name, stroke_type, sample_rate_hz, velocity_profile, distance_profile"


def _fetch(sb):
    """Annotated free/back/fly sessions that carry a stroke_start_s ground-truth mark."""
    anns = (sb.table("session_annotations").select("session_id, phases").execute().data) or []
    truth = {}
    for a in anns:
        ph = a.get("phases") or {}
        ss = ph.get("stroke_start_s")
        if ss is not None:
            truth[a["session_id"]] = ph
    if not truth:
        return []
    rows = (sb.table("sessions").select(_COLS)
            .in_("id", list(truth.keys())).execute().data) or []
    out = []
    for r in rows:
        if r.get("stroke_type") in STROKES and r.get("velocity_profile"):
            out.append((r, truth[r["id"]]))
    return out


def _scalogram(vel, fs):
    """(power[n_f, n_t], freqs_hz) over [_F_LO, _F_HI], detrended like production."""
    active = metrics._detrend_for_cwt(np.nan_to_num(vel), fs)
    if not np.any(np.isfinite(active)) or float(np.max(np.abs(active))) < 1e-9:
        return None, None
    dt = 1.0 / fs
    target = np.geomspace(_F_LO, _F_HI, _N_F)
    scales = pywt.central_frequency(metrics._WAVELET) / (target * dt)
    coeffs, freqs = pywt.cwt(active, scales, metrics._WAVELET, sampling_period=dt)
    return np.abs(coeffs) ** 2, freqs


def _band_power(power, freqs, lo, hi, fs, smooth_s=0.4):
    """Mean power in [lo, hi] Hz at each time, smoothed with a centered rolling mean."""
    sel = (freqs >= lo) & (freqs <= hi)
    if not sel.any():
        return np.zeros(power.shape[1])
    p = power[sel].mean(axis=0)
    w = max(1, int(smooth_s * fs))
    kern = np.ones(w) / w
    return np.convolve(p, kern, mode="same")


def _dom_freq(power, freqs, i0, i1):
    """Dominant (max-power) frequency over samples [i0, i1)."""
    i0, i1 = max(0, i0), min(power.shape[1], i1)
    if i1 <= i0:
        return float("nan")
    col = power[:, i0:i1].mean(axis=1)
    return float(freqs[int(np.argmax(col))])


def _detect_breakout(pk, uw_start_idx, fs, frac=0.35, hold_s=0.6):
    """User's rule: breakout = where the sustained kick band DISAPPEARS.

    From uw_start, find the sustained high-kick-power run; return the first sample after it
    where kick power stays below `frac * run_peak` for `hold_s`. None if no sustained run.
    """
    n = pk.size
    s = max(0, int(uw_start_idx))
    if s >= n - 1:
        return None
    ref = float(np.percentile(pk[s:], 95))
    if ref < 1e-12:
        return None
    active = pk > frac * ref
    # first active sample at/after uw_start = kicking begins
    idx = np.flatnonzero(active[s:])
    if idx.size == 0:
        return None
    kick_start = s + int(idx[0])
    # walk forward: first point where it stays INACTIVE for hold_s
    hold = max(1, int(hold_s * fs))
    run_below = 0
    for i in range(kick_start, n):
        if not active[i]:
            run_below += 1
            if run_below >= hold:
                return i - hold + 1     # breakout = where the band first went quiet
        else:
            run_below = 0
    return None


def _current_ip(vel, fs):
    """The production breakout (ip_end) as compute_session_metrics resolves it."""
    t = np.arange(vel.size) / fs
    ph = metrics.detect_phases(t, vel)
    b_end = ph["baseline_end"]
    win = metrics.detect_swim_window(t, vel)
    if win is not None:
        return min(max(int(win[0]), b_end), int(win[1]) - 1) / fs
    return metrics.detect_initial_phase(t, vel, b_end)["initial_phase_end_idx"] / fs


def main():
    ap = argparse.ArgumentParser(description="Breakout kick-band-disappearance probe")
    ap.add_argument("--plot", action="store_true", help="dump PNGs to the scratchpad dir")
    ap.add_argument("--frac", type=float, default=0.35)
    args = ap.parse_args()

    sb = _client()
    data = _fetch(sb)
    print(f"\nBreakout kick-band probe — {len(data)} annotated free/back/fly sessions")
    print(f"kick band {_KICK_LO}-{_KICK_HI} Hz | stroke band {_STROKE_LO}-{_STROKE_HI} Hz | "
          f"frac={args.frac}\n")

    hdr = (f"{'id':<10}{'stroke':<11}{'fs':>4}{'true_bk':>8}{'uw_st':>7}"
           f"{'uw_domHz':>9}{'sf_domHz':>9}{'Pk_uw/sf':>9}"
           f"{'cur_ip':>8}{'cur_err':>8}{'cand':>7}{'cand_err':>9}{'ship_err':>9}")
    print(hdr); print("-" * len(hdr))

    cur_errs, cand_errs, cand_miss = [], [], 0
    ship_errs, ship_refused = [], 0
    by_stroke = {}   # stroke -> {"cur": [], "cand": [], "ship": [], "miss": 0}
    plot_dir = Path(os.environ.get("TEMP", "/tmp")) / "breakout_band"
    if args.plot:
        plot_dir.mkdir(parents=True, exist_ok=True)

    for row, ph in sorted(data, key=lambda d: d[0].get("stroke_type") or ""):
        sid = row["id"][:8]
        stroke = row.get("stroke_type") or "?"
        fs = float(row.get("sample_rate_hz") or annot.FS_HZ)
        vel = _arr(row.get("velocity_profile"))
        if vel.size < 200:
            continue
        true_bk = float(ph["stroke_start_s"])
        uw_st = ph.get("underwater_start_s")

        power, freqs = _scalogram(vel, fs)
        if power is None:
            continue
        pk = _band_power(power, freqs, _KICK_LO, _KICK_HI, fs)

        # underwater-start index: annotation if present else the 75-02 auto detector
        t = np.arange(vel.size) / fs
        if uw_st is not None:
            uw_idx = int(round(float(uw_st) * fs))
        else:
            bend = metrics.detect_phases(t, vel)["baseline_end"]
            di = metrics.detect_underwater_start(t, vel, bend)
            uw_idx = int(di) if di is not None else metrics.detect_phases(t, vel)["baseline_end"]

        bk_idx = int(round(true_bk * fs))
        uw_dom = _dom_freq(power, freqs, uw_idx, bk_idx)                       # true underwater span
        sf_dom = _dom_freq(power, freqs, bk_idx, min(bk_idx + int(3 * fs), vel.size))
        # does kick-band power drop at the true breakout? (characterisation)
        pk_uw = float(np.median(pk[uw_idx:bk_idx])) if bk_idx > uw_idx else float("nan")
        pk_sf = float(np.median(pk[bk_idx:min(bk_idx + int(3 * fs), vel.size)]))
        pk_ratio = pk_uw / pk_sf if pk_sf > 1e-12 else float("nan")

        cur_ip = _current_ip(vel, fs)
        cand_idx = _detect_breakout(pk, uw_idx, fs, frac=args.frac)
        cand = cand_idx / fs if cand_idx is not None else float("nan")

        # ── the SHIPPED detector on the PRODUCTION path (76-01 Task 3) ────────────
        # The `cand` column above is this probe's own exploratory reimplementation and
        # it is NOT what compute_session_metrics runs: production bounds the search by
        # swim_end and vetoes collapses. Scoring only `cand` lets the committed number
        # drift away from the shipped one — measured 0.30 s vs 0.81 s on freestyle the
        # first time the two were compared. `ship_err` is the number that ships.
        # Boundary resolution mirrors compute_session_metrics EXACTLY, fallbacks included:
        # detect_phases supplies swim_end when detect_swim_window returns None, so those
        # sessions are scored rather than skipped (production still runs the branch on them).
        phs = metrics.detect_phases(t, vel)
        swim_end = phs["swim_end"]
        win = metrics.detect_swim_window(t, vel, stroke)
        if win is not None:
            swim_end = min(max(int(win[1]), phs["baseline_end"] + 1), vel.size)
        ship_idx = metrics.detect_breakout_kickband(t, vel, uw_idx, swim_end)
        if ship_idx is None or not metrics._breakout_leaves_swim(t, vel, ship_idx, swim_end):
            ship_refused += 1                          # falls back to the incumbent ip_end
            ship_err = cur_ip - true_bk
        else:
            ship_err = ship_idx / fs - true_bk
        ship_errs.append(abs(ship_err))

        st = by_stroke.setdefault(stroke, {"cur": [], "cand": [], "ship": [], "miss": 0})
        if np.isfinite(ship_err):
            st["ship"].append(abs(ship_err))
        cur_err = cur_ip - true_bk
        cur_errs.append(abs(cur_err)); st["cur"].append(abs(cur_err))
        if cand_idx is None:
            cand_miss += 1; st["miss"] += 1
            cand_err = float("nan")
        else:
            cand_err = cand - true_bk
            cand_errs.append(abs(cand_err)); st["cand"].append(abs(cand_err))

        print(f"{sid:<10}{stroke[:10]:<11}{fs:>4.0f}{true_bk:>8.2f}"
              f"{(uw_idx / fs):>7.2f}{uw_dom:>9.2f}{sf_dom:>9.2f}{pk_ratio:>9.2f}"
              f"{cur_ip:>8.2f}{cur_err:>+8.2f}{cand:>7.2f}{cand_err:>+9.2f}"
              f"{ship_err:>+9.2f}")

        if args.plot:
            _plot(sid, stroke, vel, fs, freqs, power, pk, uw_idx, bk_idx, cand_idx, plot_dir)

    def _stat(name, errs, miss=0):
        if not errs:
            print(f"  {name:<10} no data")
            return
        a = np.array(errs)
        print(f"  {name:<10} median |err| {np.median(a):>5.2f}s  mean {a.mean():>5.2f}s  "
              f"<=0.5s {int((a <= 0.5).sum())}/{len(a)}  <=1.0s {int((a <= 1.0).sum())}/{len(a)}"
              f"  miss {miss}")

    print("\nSCORE vs coach stroke_start_s (all strokes):")
    _stat("current", cur_errs)
    _stat("kick-band", cand_errs, cand_miss)
    _stat("SHIPPED", ship_errs)
    print(f"    (SHIPPED = metrics.detect_breakout_kickband on the production path - "
          f"swim_end-bounded + collapse-guarded; {ship_refused} refused/vetoed -> "
          f"incumbent ip_end, scored as such)")
    print("\nPER-STROKE:")
    for stroke, d in sorted(by_stroke.items()):
        print(f" [{stroke}]  n={len(d['cur'])}")
        _stat("  current", d["cur"])
        _stat("  kick-band", d["cand"], d["miss"])
        _stat("  SHIPPED", d["ship"])
    print("\nCHARACTERISATION: uw_domHz should be ~2-2.5 (kick), sf_domHz lower (stroke),")
    print("Pk_uw/sf >> 1 means kick-band power really does drop at breakout (hypothesis holds).\n")


    # Phase 77: butterfly is scored by its OWN detector below - the kick-band
    # columns above are the measurement that REJECTED the kick rule for fly.
    fly_report(data, plot_dir if args.plot else None)


# ── FLY: the shipped arm-cycle-APPEARANCE detector (Phase 77) ────────────────────
# Butterfly cannot use the kick-band rule above and measured WORSE than the incumbent
# under it (the surface stroke keeps the ~2 Hz band). Everything below scores
# metrics.detect_breakout_fly — the SHIPPED function, never a reimplementation, for the
# same reason ship_err exists above: a probe-local copy drifts away from production.
_FLY_H2_HZ = (1.5, 2.0)          # 2-beat harmonic — reported in the fingerprint only


def _fly_sessions(data):
    """Butterfly rows with everything the fly scorers need, resolved ONCE.

    Boundary resolution mirrors compute_session_metrics exactly, fallbacks included.
    Returns dicts so the scorers below can be cheap (the CWT is the expensive part).
    """
    out = []
    for row, ph in sorted(data, key=lambda d: d[0]["id"]):
        if row.get("stroke_type") != "butterfly":
            continue
        fs = float(row.get("sample_rate_hz") or annot.FS_HZ)
        vel = _arr(row.get("velocity_profile"))
        if vel.size < 200:
            continue
        t = np.arange(vel.size) / fs
        phs = metrics.detect_phases(t, vel)
        swim_end = phs["swim_end"]
        win = metrics.detect_swim_window(t, vel, "butterfly")
        if win is not None:
            swim_end = min(max(int(win[1]), phs["baseline_end"] + 1), vel.size)
        # the production underwater start (75-02) — and the annotated one, to show the
        # production seam holds on fly rather than assuming it
        di = metrics.detect_underwater_start(t, vel, phs["baseline_end"])
        uw_auto = int(di) if di is not None else phs["baseline_end"]
        uw_st = ph.get("underwater_start_s")
        uw_ann = int(round(float(uw_st) * fs)) if uw_st is not None else uw_auto
        power, freqs = _scalogram(vel, fs)
        if power is None:
            continue
        out.append(dict(sid=row["id"][:8], fs=fs, vel=vel, t=t,
                        true_bk=float(ph["stroke_start_s"]),
                        uw_ann=uw_ann, uw_auto=uw_auto, swim_end=swim_end,
                        power=power, freqs=freqs,
                        cur_ip=_current_ip(vel, fs)))
    return out


def _fly_score(S, uw_key="uw_ann"):
    """Score the SHIPPED detect_breakout_fly. Refusals fall back to the incumbent ip_end
    and are scored as such — a refusal is not a free pass, it is today's answer."""
    errs, refused, rows = [], 0, []
    for s in S:
        bk = metrics.detect_breakout_fly(s["t"], s["vel"], s[uw_key], s["swim_end"])
        if bk is not None and not metrics._breakout_leaves_swim(
                s["t"], s["vel"], bk, s["swim_end"]):
            bk = None                                  # collapse guard vetoed it
        if bk is None:
            refused += 1
            det, err = float("nan"), s["cur_ip"] - s["true_bk"]
        else:
            det = bk / s["fs"]
            err = det - s["true_bk"]
        errs.append(abs(err))
        rows.append((s["sid"], s["true_bk"], s[uw_key] / s["fs"], det, err,
                     s["cur_ip"] - s["true_bk"]))
    return np.array(errs), refused, rows


def _fly_fingerprint(S):
    """P_surface / P_uw per band at the TRUE breakout. Uses ground truth — this is
    characterisation, not detection. The ratio cancels the CWT's 1/f bias."""
    print("\nFLY FINGERPRINT — P_surface / P_uw at the coach's mark (>1 APPEARS, <1 DROPS)")
    bands = (("arm  0.8-1.1", metrics._FLY_ARM_HZ),
             ("fund 1.1-1.5", metrics._FLY_FUND_HZ),
             ("h2   1.5-2.0", _FLY_H2_HZ))
    for label, band in bands:
        ratios = []
        for s in S:
            p = _band_power(s["power"], s["freqs"], band[0], band[1], s["fs"])
            bk = int(round(s["true_bk"] * s["fs"]))
            uw, end = s["uw_ann"], min(bk + int(3 * s["fs"]), s["vel"].size)
            if bk <= uw or end <= bk:
                continue
            a, b = float(np.median(p[uw:bk])), float(np.median(p[bk:end]))
            if a > 1e-12:
                ratios.append(b / a)
        if not ratios:
            print(f"  {label}   no data")
            continue
        r = np.array(ratios)
        print(f"  {label} Hz   median {np.median(r):>5.2f}x   "
              f">1 in {int((r > 1).sum())}/{r.size}")


def _fly_jitter_grid(S):
    """AC-2: every band-edge cell must beat the incumbent, or the win is a knife-edge fit.

    Monkeypatches the SHIPPED constants so the grid measures the real detector, gates and
    all, rather than a parallel implementation that could drift from it.
    """
    arms = [(0.75, 1.05), (0.8, 1.1), (0.85, 1.15), (0.8, 1.2)]
    funds = [(1.0, 1.4), (1.1, 1.5), (1.2, 1.6), (1.1, 1.6)]
    keep = (metrics._FLY_ARM_HZ, metrics._FLY_FUND_HZ)
    inc = np.median([abs(s["cur_ip"] - s["true_bk"]) for s in S])
    print(f"\nBAND-EDGE JITTER GRID — median |err| (s); incumbent = {inc:.2f} s")
    print(f"{'arm \\\\ fund':<14}" + "".join(f"{str(f):>13}" for f in funds))
    worst = 0.0
    try:
        for arm in arms:
            cells = []
            for fund in funds:
                metrics._FLY_ARM_HZ, metrics._FLY_FUND_HZ = arm, fund
                e, ref, _ = _fly_score(S)
                med = float(np.median(e)) if e.size else float("nan")
                worst = max(worst, med)
                cells.append(f"{med:.2f}({ref}r)")
            print(f"{str(arm):<14}" + "".join(f"{c:>13}" for c in cells))
    finally:
        metrics._FLY_ARM_HZ, metrics._FLY_FUND_HZ = keep
    print(f"  cell = median|err|(refusals). worst cell {worst:.2f} s "
          f"{'<' if worst < inc else '>='} incumbent {inc:.2f} s "
          f"-> {'physical' if worst < inc else 'KNIFE-EDGE'}")


def _fly_contrast_sweep(S):
    """_FLY_MIN_CONTRAST is the gate that lets the detector refuse for lack of signal at
    all (the low/rise thresholds are drawn from the ratio's own range, so without it a
    merely rippling ratio always supplies a 'rise'). Sweep it rather than assume it."""
    keep = metrics._FLY_MIN_CONTRAST
    print("\n_FLY_MIN_CONTRAST SWEEP — the refuse-for-lack-of-signal gate")
    print(f"{'contrast':>9}{'median':>9}{'mean':>8}{'<=1.0s':>9}{'refused':>9}")
    try:
        for c in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0):
            metrics._FLY_MIN_CONTRAST = c
            e, ref, _ = _fly_score(S)
            print(f"{c:>9.1f}{np.median(e):>9.2f}{e.mean():>8.2f}"
                  f"{f'{int((e <= 1.0).sum())}/{e.size}':>9}{ref:>9}")
    finally:
        metrics._FLY_MIN_CONTRAST = keep


def _fly_refine_compare(S):
    """D5: is the per-session f0 band refinement worth switching on? Measured, not assumed."""
    keep = metrics._FLY_REFINE_BANDS
    print("\nBAND REFINEMENT (D5) — fixed physical bands vs per-session f0")
    try:
        for flag in (False, True):
            metrics._FLY_REFINE_BANDS = flag
            e, ref, _ = _fly_score(S)
            print(f"  refine={str(flag):<5} median {np.median(e):.2f}s  mean {e.mean():.2f}s  "
                  f"<=1.0s {int((e <= 1.0).sum())}/{e.size}  refused {ref}")
    finally:
        metrics._FLY_REFINE_BANDS = keep


def fly_report(data, plot_dir=None):
    S = _fly_sessions(data)
    if not S:
        print("\nno butterfly sessions with a stroke_start_s mark\n")
        return
    print(f"\n{'=' * 78}\nFLY BREAKOUT (Phase 77) — shipped metrics.detect_breakout_fly, "
          f"{len(S)} sessions\n{'=' * 78}")
    print(f"arm {metrics._FLY_ARM_HZ} Hz / fund {metrics._FLY_FUND_HZ} Hz | "
          f"contrast>={metrics._FLY_MIN_CONTRAST} | refine={metrics._FLY_REFINE_BANDS}")

    errs, refused, rows = _fly_score(S)
    hdr = f"{'id':<10}{'true_bk':>8}{'uw_st':>7}{'detect':>8}{'err':>8}{'inc_err':>9}"
    print("\n" + hdr); print("-" * len(hdr))
    for sid, tb, uw, det, err, ierr in sorted(rows, key=lambda r: abs(r[4])):
        d = f"{det:>8.2f}" if np.isfinite(det) else f"{'REFUSE':>8}"
        print(f"{sid:<10}{tb:>8.2f}{uw:>7.2f}{d}{err:>+8.2f}{ierr:>+9.2f}")

    inc = np.array([abs(s["cur_ip"] - s["true_bk"]) for s in S])
    print(f"\n  SHIPPED    median |err| {np.median(errs):.2f}s  mean {errs.mean():.2f}s  "
          f"<=0.5s {int((errs <= 0.5).sum())}/{errs.size}  "
          f"<=1.0s {int((errs <= 1.0).sum())}/{errs.size}  refused {refused}")
    print(f"  incumbent  median |err| {np.median(inc):.2f}s  mean {inc.mean():.2f}s  "
          f"<=1.0s {int((inc <= 1.0).sum())}/{inc.size}")
    print("  (refusals are scored at the incumbent ip_end they fall back to)")

    _fly_fingerprint(S)

    # production-seam check: the annotated underwater start vs the auto 75-02 one
    e_auto, ref_auto, _ = _fly_score(S, uw_key="uw_auto")
    print(f"\nPRODUCTION SEAM — underwater start: annotated vs auto detect_underwater_start")
    print(f"  annotated  median {np.median(errs):.2f}s  refused {refused}")
    print(f"  AUTO (75-02) median {np.median(e_auto):.2f}s  refused {ref_auto}   "
          f"<- what production actually runs")

    _fly_contrast_sweep(S)
    _fly_refine_compare(S)
    _fly_jitter_grid(S)

    if plot_dir is not None:
        for s in S:
            _fly_plot(s, plot_dir)
        print(f"\n  fly PNGs -> {plot_dir}")
    print()


def _fly_plot(s, out_dir):
    """velocity + the arm & fundamental band powers + their ratio + the detected breakout."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fs, vel, t = s["fs"], s["vel"], s["t"]
    arm = _band_power(s["power"], s["freqs"], *metrics._FLY_ARM_HZ, fs)
    fund = _band_power(s["power"], s["freqs"], *metrics._FLY_FUND_HZ, fs)
    ratio = metrics._fly_band_ratio(vel, fs, s["uw_ann"])
    bk = metrics.detect_breakout_fly(t, vel, s["uw_ann"], s["swim_end"])
    vetoed = bk is not None and not metrics._breakout_leaves_swim(
        t, vel, bk, s["swim_end"])

    fig, ax = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    ax[0].plot(t, vel, lw=0.7); ax[0].set_ylabel("vel m/s")
    ax[1].plot(t, arm, lw=0.9, color="tab:blue", label=f"arm {metrics._FLY_ARM_HZ}")
    ax[1].plot(t, fund, lw=0.9, color="tab:orange", label=f"fund {metrics._FLY_FUND_HZ}")
    ax[1].set_ylabel("band P"); ax[1].legend(fontsize=7, loc="upper right")
    if ratio is not None:
        ax[2].plot(t, ratio, lw=0.9, color="tab:purple")
    ax[2].set_ylabel("arm / fund"); ax[2].set_xlabel("s")
    # the underwater window the detector searches from
    for a in ax:
        a.axvspan(s["uw_ann"] / fs, s["true_bk"], color="green", alpha=0.08)
        a.axvline(s["uw_ann"] / fs, color="green", ls="--", lw=1, label="uw_start")
        a.axvline(s["true_bk"], color="red", lw=1.5, label="coach mark")
        a.axvline(s["cur_ip"], color="grey", ls="-.", lw=1, label="incumbent")
        if bk is not None:
            a.axvline(bk / fs, color="blue", ls=":", lw=1.8, label="detected")
    ax[0].legend(fontsize=7, loc="upper right")
    state = "VETOED" if vetoed else ("REFUSED" if bk is None else
                                     f"err {bk / fs - s['true_bk']:+.2f}s")
    fig.suptitle(f"{s['sid']} — butterfly — {state}")
    fig.tight_layout()
    fig.savefig(out_dir / f"fly_{s['sid']}.png", dpi=90)
    plt.close(fig)


def _plot(sid, stroke, vel, fs, freqs, power, pk, uw_idx, bk_idx, cand_idx, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = np.arange(vel.size) / fs
    fig, ax = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    ax[0].plot(t, vel, lw=0.7); ax[0].set_ylabel("vel m/s")
    ax[1].pcolormesh(t, freqs, np.log(power + 1e-9), shading="auto", cmap="magma")
    ax[1].axhspan(_KICK_LO, _KICK_HI, color="cyan", alpha=0.15); ax[1].set_ylabel("Hz")
    ax[2].plot(t, pk, lw=0.8, color="tab:purple"); ax[2].set_ylabel("kick-band P"); ax[2].set_xlabel("s")
    for a in ax:
        a.axvline(uw_idx / fs, color="green", ls="--", lw=1, label="uw_start")
        a.axvline(bk_idx / fs, color="red", lw=1.5, label="true breakout")
        if cand_idx is not None:
            a.axvline(cand_idx / fs, color="blue", ls=":", lw=1.5, label="candidate")
    ax[0].legend(fontsize=7, loc="upper right")
    fig.suptitle(f"{sid} — {stroke}")
    fig.tight_layout()
    fig.savefig(out_dir / f"{sid}_{stroke}.png", dpi=90)
    plt.close(fig)


if __name__ == "__main__":
    main()
