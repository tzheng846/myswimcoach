"""Read-only probe (Phase 83-03): is per-lap shape-anomaly detection viable?

Answers three questions against the STORED library, changing nothing:
  1. How many stroke cycles does a real session actually have?
  2. How long is the un-banded breakout pull (stroke_start_s -> cycles[0].start_idx)?
  3. What does the shipped k=3.0 MAD gate fire on -- and does it fire at all?

Mirrors web/lib/cycleShape.js exactly (resample 50 -> pointwise median -> RMSE -> one-sided
MAD gate) so the numbers are the ones the browser would produce.
"""
import json
import os
import sys
from statistics import median

sys.path = [p for p in sys.path if p not in ('', '.')]

import numpy as np
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

POINTS, K, MIN_ITEMS = 50, 3.0, 5


def resample(vel, a, b, points=POINTS):
    a, b = int(a), int(b)
    if b - a < 2 or a < 0 or b > len(vel):
        return None
    seg = vel[a:b]
    if not np.all(np.isfinite(seg)):
        return None
    pos = np.linspace(0, len(seg) - 1, points)
    return np.interp(pos, np.arange(len(seg)), seg)


def gate(profiles):
    """-> (n_flagged, dists, med, mad) using the shipped rule."""
    if len(profiles) < MIN_ITEMS:
        return None
    ref = np.median(np.vstack(profiles), axis=0)
    dists = [float(np.sqrt(np.mean((p - ref) ** 2))) for p in profiles]
    med = median(dists)
    mad = median([abs(d - med) for d in dists])
    if mad <= 0:
        return 0, dists, med, mad
    return sum(1 for d in dists if d - med > K * mad), dists, med, mad


rows = sb.table("sessions").select(
    "id,stroke_type,sample_rate_hz,velocity_profile,metrics_json"
).not_.is_("velocity_profile", "null").execute().data

print(f"{len(rows)} sessions with a velocity profile\n")

cyc_counts, gaps, fired, gated_out, flagged_is_first = [], [], 0, 0, 0
eligible = 0

for r in rows:
    mj = r.get("metrics_json") or {}
    cycles = mj.get("cycles") or []
    ph = (mj.get("phases") or {}).get("boundaries") or {}
    fs = r.get("sample_rate_hz") or 100
    vel = np.array([np.nan if v is None else float(v) for v in (r.get("velocity_profile") or [])])
    if not cycles or vel.size < 2:
        continue
    cyc_counts.append(len(cycles))

    ss = ph.get("stroke_start_s")
    c0 = cycles[0].get("start_idx")
    if ss is not None and c0 is not None:
        gaps.append(c0 / fs - ss)

    profs, ns = [], []
    for i, c in enumerate(cycles):
        p = resample(vel, c.get("start_idx", -1), c.get("end_idx", -1))
        if p is not None:
            profs.append(p)
            ns.append(i + 1)
    g = gate(profs)
    if g is None:
        gated_out += 1
        continue
    eligible += 1
    n_flag, dists, med, mad = g
    if n_flag:
        fired += 1
        worst = ns[int(np.argmax(dists))]
        if worst == 1:
            flagged_is_first += 1


def stats(xs, label, unit=""):
    if not xs:
        print(f"{label}: no data")
        return
    xs = sorted(xs)
    print(f"{label}: n={len(xs)}  min={xs[0]:.2f}{unit}  median={median(xs):.2f}{unit}  "
          f"max={xs[-1]:.2f}{unit}")


stats(cyc_counts, "Cycles per session")
print(f"  sessions with <{MIN_ITEMS} cycles: "
      f"{sum(1 for c in cyc_counts if c < MIN_ITEMS)}/{len(cyc_counts)}")
stats(gaps, "Breakout-pull gap (stroke_start -> cycle 1)", " s")
print(f"\nGate at k={K}, minItems={MIN_ITEMS}:")
print(f"  too few usable cycles to even run: {gated_out}")
print(f"  ran the gate:                      {eligible}")
print(f"  fired at least one flag:           {fired}"
      + (f"  ({100*fired/eligible:.0f}%)" if eligible else ""))
print(f"  ...of those, the flag was cycle 1: {flagged_is_first}")
