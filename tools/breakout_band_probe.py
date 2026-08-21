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
