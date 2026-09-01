"""Read-only probe: for every stored session that reaches 20 m, what is the tail distance past
20 m to finish? Diagnoses why splits_remainder (23/99) is far below splits_20m (56/99) at the
88-01 backfill checkpoint, per D3's stated stop condition."""
import os
import sys
from pathlib import Path

import httpx
import numpy as np
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import annotations as annot
import phase_metrics as pm

load_dotenv(REPO_ROOT / ".env")
url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
headers = {"apikey": key, "Authorization": f"Bearer {key}"}
base = f"{url.rstrip('/')}/rest/v1"


def _arr(values):
    return np.array([np.nan if v is None else float(v) for v in (values or [])], dtype=float)


rows = httpx.get(f"{base}/sessions", params={"select": "id,sample_rate_hz,stroke_type",
                  "velocity_profile": "not.is.null", "order": "created_at.asc"},
                 headers=headers, timeout=180).json()
ann_rows = httpx.get(f"{base}/session_annotations", params={"select": "session_id,phases"},
                     headers=headers, timeout=180).json()
ann_by_session = {a["session_id"]: a.get("phases") for a in ann_rows}

tails = []
for r in rows:
    sid = r["id"]
    got = httpx.get(f"{base}/sessions",
                    params={"select": "velocity_profile,distance_profile,acceleration_profile,metrics_json",
                            "id": f"eq.{sid}"}, headers=headers, timeout=180).json()
    row = got[0] if got else {}
    vel = _arr(row.get("velocity_profile"))
    dist = _arr(row.get("distance_profile"))
    if vel.size < 2 or dist.size != vel.size:
        continue
    fs = float(r.get("sample_rate_hz") or annot.FS_HZ)
    mj = row.get("metrics_json") or {}
    ctx = pm.PhaseContext(
        t=np.arange(vel.size) / fs, vel=vel, dist=dist,
        accel=_arr(row.get("acceleration_profile")), fs=fs, stroke_type=r.get("stroke_type"),
        go_signal_s=mj.get("go_signal_s"), annotation_phases=ann_by_session.get(sid),
        seed_phases=annot.build_seed(mj, fs)["phases"], initial_phase=mj.get("initial_phase"),
        cycles=mj.get("cycles"),
        segmentation_reliable=bool((mj.get("data_quality") or {}).get("segmentation_reliable", False)),
    )
    anchor = pm._dive_relative(ctx)
    if anchor is None:
        continue
    i_start, rel, end = anchor
    hits = np.nonzero(np.isfinite(rel) & (rel >= 20.0))[0]
    if len(hits) == 0:
        continue  # never reaches 20m -- not part of the splits_20m/remainder gap
    i_a = int(hits[0]) + i_start
    i_b = i_start + len(rel) - 1
    if i_b <= i_a:
        continue
    tail = float(ctx.dist[i_b]) - float(ctx.dist[i_a])
    tails.append((sid[:8], r.get("stroke_type"), tail))

tails.sort(key=lambda x: x[2])
print(f"{len(tails)} sessions reach 20 m (matches splits_20m count)")
under_floor = [t for t in tails if t[2] < pm._MIN_REMAINDER_M]
print(f"{len(under_floor)} of them have a tail < {pm._MIN_REMAINDER_M} m (the current floor)")
print()
print("Full distribution of tail-past-20m (m), sorted:")
for sid, stroke, tail in tails:
    flag = "  <- under floor" if tail < pm._MIN_REMAINDER_M else ""
    print(f"  {sid} {stroke or '?':12} {tail:7.3f}{flag}")

arr = np.array([t[2] for t in tails])
print()
print("Percentiles (m):", {p: round(float(np.percentile(arr, p)), 3) for p in (5, 10, 25, 50, 75, 90)})
for floor in (0.0, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0):
    n = int(np.sum(arr >= floor))
    print(f"  floor {floor:>4} m -> {n} of {len(tails)} would fill")
