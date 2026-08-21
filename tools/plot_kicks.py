"""plot_kicks.py — Phase 75-03 eyeball harness for detect_underwater_kicks (read-only DB).

The underwater dolphin-kick detector + its seven metrics DISPLAY, they do not grade — dolphin
kicks have no annotated ground truth (D7), so the only validation is a coach looking at the
detected kicks on real traces. This renders, for a spread of free/back/fly sessions, each
underwater window [underwater_start_s, stroke_start_s] with every detected downkick marked and
the seven metric values in the caption, as one contact-sheet PNG.

    python tools/plot_kicks.py                       # up to 12 sessions, spread across strokes
    python tools/plot_kicks.py --limit 9 --out DIR

Reads the DATABASE, never the local raw CSVs (user directive D-data): stored velocity_profile +
metrics_json.phases boundaries, pulled read-only with the .env service-role key — same discipline
as tools/backfill_phases.py / score_underwater.py. NO write path exists in this file. Prints a
session-id prefix + stroke only, never a name / note / email.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path = [p for p in sys.path if p not in ("", ".")]

import httpx                              # noqa: E402
import numpy as np                        # noqa: E402
import matplotlib                         # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt           # noqa: E402
from dotenv import load_dotenv            # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
import annotations as annot               # noqa: E402
import metrics                            # noqa: E402
import phase_metrics as pm                # noqa: E402

_KEYS = ("kick_count", "kick_tempo", "dist_per_kick", "kick_consistency",
         "per_kick_decay", "first_kick_impulse", "uw_ivv")


def _arr(values):
    return np.array([np.nan if v is None else float(v) for v in (values or [])], dtype=float)


class Rest:
    """GET-only PostgREST client (no write path — this tool never mutates the DB)."""

    def __init__(self, url, key):
        self.base = f"{url.rstrip('/')}/rest/v1"
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    def select(self, table, select, **params):
        r = httpx.get(f"{self.base}/{table}", params={"select": select, **params},
                      headers=self.headers, timeout=180)
        r.raise_for_status()
        return r.json()


def _build_ctx(row, ann, fs):
    vel = _arr(row.get("velocity_profile"))
    mj = row.get("metrics_json") or {}
    return pm.PhaseContext(
        t=np.arange(vel.size) / fs,
        vel=vel,
        dist=_arr(row.get("distance_profile")),
        accel=_arr(row.get("acceleration_profile")),
        fs=fs,
        stroke_type=row.get("stroke_type"),
        go_signal_s=None,
        annotation_phases=ann,
        seed_phases=annot.build_seed(mj, fs)["phases"],
        initial_phase=mj.get("initial_phase"),
    )


def _fmt(v, nd=2):
    return "-" if v is None else f"{v:.{nd}f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=12, help="max sessions on the contact sheet")
    ap.add_argument("--out", default=None, help="output dir (default: repo scratch)")
    ap.add_argument("--annotated-only", action="store_true",
                    help="Review only annotated non-breaststroke sessions, taking the kick "
                         "window from the coach annotation (ground-truth boundaries). Isolates "
                         "the kick detector from the auto pipeline's stroke_start error, which "
                         "each caption still reports (dotted line = where auto put stroke_start).")
    ap.add_argument("--max-boundary-err", type=float, default=None,
                    help="Implies --annotated-only; additionally drop sessions whose AUTO-path "
                         "boundary error vs the annotation exceeds this many seconds.")
    args = ap.parse_args()
    tol = args.max_boundary_err
    annotated = args.annotated_only or tol is not None

    load_dotenv(REPO_ROOT / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("Need SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
    db = Rest(url, key)

    heads = db.select("sessions", "id,sample_rate_hz,stroke_type",
                      velocity_profile="not.is.null", order="created_at.asc")
    ann_by = {a["session_id"]: a.get("phases")
              for a in db.select("session_annotations", "session_id,phases")}

    scanned = eligible = drop_breast = drop_nowindow = drop_bad = 0
    drop_noann = drop_badbound = 0
    pool = []
    for h in heads:
        scanned += 1
        sid = h["id"]
        stroke = h.get("stroke_type") or "?"
        if stroke == "breaststroke":
            drop_breast += 1
            continue
        ann = ann_by.get(sid)
        if annotated:
            # Ground truth needs both annotated window boundaries.
            ann_uw = pm._phase_val(ann, "underwater_start_s")
            ann_st = pm._phase_val(ann, "stroke_start_s")
            if ann_uw is None or ann_st is None:
                drop_noann += 1
                continue
        try:
            got = db.select(
                "sessions",
                "velocity_profile,distance_profile,acceleration_profile,metrics_json",
                id=f"eq.{sid}")
            row = {**(got[0] if got else {}), "stroke_type": stroke}
            fs = float(h.get("sample_rate_hz") or annot.FS_HZ)
            if _arr(row.get("velocity_profile")).size < 3:
                drop_bad += 1
                continue
            entry = {"sid": sid, "stroke": stroke, "fs": fs}
            # The window comes from the annotation when present (manual boundaries win in
            # resolve_boundaries), so the ground-truth window is used in annotated mode.
            ctx = _build_ctx(row, ann, fs)
            if annotated:
                # Measure how far the AUTO path (no annotation) placed stroke_start, for the
                # caption / optional filter — the auto pipeline's window right edge.
                b = pm.resolve_boundaries(_build_ctx(row, None, fs))
                auto_st = b.get("stroke_start_s")
                auto_uw = b.get("underwater_start_s")
                err_st = abs(auto_st - ann_st) if auto_st is not None else None
                err_uw = abs(auto_uw - ann_uw) if auto_uw is not None else None
                if tol is not None and (
                        err_st is None or err_uw is None or max(err_st, err_uw) > tol):
                    drop_badbound += 1
                    continue
                entry.update(auto_st=auto_st, err_st=err_st, err_uw=err_uw)
            w = pm._uw_window(ctx)
            if w is None:
                drop_nowindow += 1
                continue
            i0, i1, dur = w
            eligible += 1
            entry.update(ctx=ctx, i0=i0, i1=i1, dur=dur)
            pool.append(entry)
        except Exception as e:  # noqa: BLE001 — one bad row must not abort the scan
            drop_bad += 1
            print(f"  {sid[:8]} ERROR {type(e).__name__}: {e}")

    if not pool:
        sys.exit("No sessions matched (try relaxing --max-boundary-err, or omit it).")

    # Spread across strokes then duration, then take an evenly-spaced subset up to the limit.
    pool.sort(key=lambda p: (p["stroke"], p["dur"]))
    if len(pool) > args.limit:
        idx = np.linspace(0, len(pool) - 1, args.limit).round().astype(int)
        sel = [pool[i] for i in dict.fromkeys(idx)]          # dedupe, keep order
    else:
        sel = pool

    extra = "" if tol is None else (f", no-annotation {drop_noann}, "
                                    f"boundary>±{tol}s {drop_badbound}")
    print(f"scanned {scanned} · eligible {eligible} "
          f"(dropped: breast {drop_breast}, no-window {drop_nowindow}, bad {drop_bad}{extra}) "
          f"· plotting {len(sel)}")

    out_dir = Path(args.out) if args.out else (REPO_ROOT / "scratch")
    out_dir.mkdir(parents=True, exist_ok=True)

    n = len(sel)
    cols = 2 if n <= 8 else 3
    rows = -(-n // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(6.5 * cols, 2.7 * rows), squeeze=False)
    axf = axes.flatten()

    for ax, p in zip(axf, sel):
        ctx, fs, i0, i1 = p["ctx"], p["fs"], p["i0"], p["i1"]
        t, vel = ctx.t, ctx.vel
        peaks = metrics.detect_underwater_kicks(t, vel, i0, i1)
        peaks = np.asarray(peaks, dtype=int) if peaks is not None else np.array([], dtype=int)
        uw = pm.compute_phases(ctx)["underwater"]
        vals = {k: uw.get(k, {}).get("value") for k in _KEYS}

        lo = max(0, i0 - int(1.0 * fs))
        hi = min(len(t) - 1, i1 + int(2.0 * fs))
        m = slice(lo, hi)
        ax.plot(t[m], vel[m], lw=0.7, color="#888")
        ax.axvspan(t[i0], t[min(i1, len(t) - 1)], color="#4a90d9", alpha=0.10)
        ax.axvline(t[i0], color="#2e7d32", ls="-.", lw=1.0)
        ax.axvline(t[min(i1, len(t) - 1)], color="#c0392b", ls="-.", lw=1.0)
        if p.get("auto_st") is not None:                    # where the AUTO path put stroke_start
            ax.axvline(p["auto_st"], color="#8e44ad", ls=":", lw=1.0, alpha=0.8)
        for j, pk in enumerate(peaks, 1):
            ax.plot(t[pk], vel[pk], "o", ms=4, color="#1565c0")
            ax.annotate(str(j), (t[pk], vel[pk]), fontsize=6, color="#1565c0",
                        xytext=(0, 4), textcoords="offset points", ha="center")
        if len(peaks):                                      # first-kick-impulse trough
            pre = vel[i0:peaks[0] + 1]
            fin = np.where(np.isfinite(pre))[0]
            if fin.size:
                tr = i0 + fin[np.argmin(pre[fin])]
                ax.plot(t[tr], vel[tr], "v", ms=5, color="#e67e22")
        berr = (f"  auto stroke_start err={p['err_st']:.2f}s"
                if p.get("err_st") is not None else "")
        cap = (f"{p['sid'][:8]} {p['stroke']}  n={_fmt(vals['kick_count'],0)} "
               f"tempo={_fmt(vals['kick_tempo'])}/s  d/kick={_fmt(vals['dist_per_kick'])}m{berr}\n"
               f"CV={_fmt(vals['kick_consistency'])} decay={_fmt(vals['per_kick_decay'],0)}% "
               f"imp={_fmt(vals['first_kick_impulse'])} ivv={_fmt(vals['uw_ivv'])}")
        ax.set_title(cap, fontsize=7, loc="left")
        ax.tick_params(labelsize=6)
        ax.grid(alpha=0.15)

    for ax in axf[n:]:
        ax.axis("off")
    if annotated:
        sub = "  ·  GROUND-TRUTH window from annotation; purple dotted = auto stroke_start"
        if tol is not None:
            sub += f" (kept: auto err ≤ {tol}s)"
    else:
        sub = ""
    fig.suptitle("Phase 75-03 — underwater kicks (green=uw_start, red=stroke_start, "
                 "○=downkick, ▽=first-kick trough)" + sub, fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    out = out_dir / "kicks_eyeball.png"
    fig.savefig(out, dpi=115)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
