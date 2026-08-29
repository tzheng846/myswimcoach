"""Read-only sweep (Phase 83-03): pick k, and decide whether to exclude cycle 1.

Splits annotated vs auto, because the two have different cycle provenance.
"""
import os
import sys
from statistics import median

sys.path = [p for p in sys.path if p not in ('', '.')]

import numpy as np
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

POINTS, MIN_ITEMS = 50, 5


def resample(vel, a, b):
    a, b = int(a), int(b)
    if b - a < 2 or a < 0 or b > len(vel):
        return None
    seg = vel[a:b]
    if not np.all(np.isfinite(seg)):
        return None
    return np.interp(np.linspace(0, len(seg) - 1, POINTS), np.arange(len(seg)), seg)


rows = sb.table("sessions").select(
    "id,stroke_type,sample_rate_hz,velocity_profile,metrics_json"
).not_.is_("velocity_profile", "null").execute().data

sess = []
for r in rows:
    mj = r.get("metrics_json") or {}
    cycles = mj.get("cycles") or []
    ph = (mj.get("phases") or {}).get("boundaries") or {}
    rel = bool(((mj.get("data_quality") or {}).get("segmentation_reliable")))
    fs = r.get("sample_rate_hz") or 100
    vel = np.array([np.nan if v is None else float(v) for v in (r.get("velocity_profile") or [])])
    if not cycles or vel.size < 2:
        continue
    profs, ns = [], []
    for i, c in enumerate(cycles):
        p = resample(vel, c.get("start_idx", -1), c.get("end_idx", -1))
        if p is not None:
            profs.append(p); ns.append(i + 1)
    gap = None
    ss, c0 = ph.get("stroke_start_s"), cycles[0].get("start_idx")
    if ss is not None and c0 is not None:
        gap = c0 / fs - ss
    sess.append(dict(rel=rel, profs=profs, ns=ns, gap=gap, n_cycles=len(cycles)))

ann = [s for s in sess if s["rel"]]
auto = [s for s in sess if not s["rel"]]
print(f"{len(sess)} usable sessions: {len(ann)} annotated, {len(auto)} auto\n")

for label, group in (("ANNOTATED", ann), ("AUTO", auto)):
    gaps = sorted(g for g in (s["gap"] for s in group) if g is not None)
    cc = sorted(s["n_cycles"] for s in group)
    if not cc:
        continue
    print(f"{label}: cycles/session median={median(cc):.0f} (min {cc[0]}, max {cc[-1]}); "
          f"<{MIN_ITEMS} cycles: {sum(1 for c in cc if c < MIN_ITEMS)}/{len(cc)}")
    if gaps:
        neg = sum(1 for g in gaps if g < 0)
        print(f"  breakout gap: median={median(gaps):.2f}s  min={gaps[0]:.2f}s  "
              f"max={gaps[-1]:.2f}s  NEGATIVE on {neg}/{len(gaps)}")
print()


def fire_rate(group, k, drop_first):
    ran = flagged = total_bands = total_flags = 0
    for s in group:
        profs, ns = s["profs"], s["ns"]
        if drop_first:
            keep = [i for i, n in enumerate(ns) if n != 1]
            profs = [profs[i] for i in keep]; ns = [ns[i] for i in keep]
        if len(profs) < MIN_ITEMS:
            continue
        ran += 1
        ref = np.median(np.vstack(profs), axis=0)
        d = [float(np.sqrt(np.mean((p - ref) ** 2))) for p in profs]
        med = median(d); mad = median([abs(x - med) for x in d])
        nf = 0 if mad <= 0 else sum(1 for x in d if x - med > k * mad)
        total_bands += len(d); total_flags += nf
        if nf:
            flagged += 1
    return ran, flagged, total_bands, total_flags


print(f"{'k':>5} {'drop c1':>8} | {'ran':>4} {'sessions w/ >=1 flag':>21} {'bands flagged':>16}")
print("-" * 62)
for drop in (False, True):
    for k in (3.0, 4.0, 5.0, 6.0, 8.0):
        ran, fl, tb, tf = fire_rate(sess, k, drop)
        pct = f"{100*fl/ran:.0f}%" if ran else "-"
        bpct = f"{100*tf/tb:.1f}%" if tb else "-"
        print(f"{k:>5.1f} {str(drop):>8} | {ran:>4} {fl:>10} ({pct:>4}){'':>6} {tf:>5}/{tb:<5} ({bpct:>5})")
