"""
_home_data_probe.py — READ-ONLY. Locate the session the marketing home page will
be drawn from (athlete "Chantee", session named "100%", recorded 2026-08-19) and
report whether it carries everything the mockup needs:
phase boundaries, per-phase metrics, cycles, kick bands, and a sample rate.

Usage:  python scratch/_home_data_probe.py
"""

import json
import os
import sys

sys.path = [p for p in sys.path if p not in ("", ".")]

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)

ath = sb.table("athletes").select("id, name").execute().data or []
match = [a for a in ath if "chantee" in (a.get("name") or "").lower()]
print("athletes matching 'chantee':", [(a["name"], a["id"][:8]) for a in match])
if not match:
    print("ALL ATHLETES:", sorted((a.get("name") or "?") for a in ath))
    sys.exit(1)

rows = (
    sb.table("sessions")
    .select("id, name, recorded_at, stroke_type, sample_rate_hz, "
            "velocity_profile, distance_profile, metrics_json, athlete_id")
    .in_("athlete_id", [a["id"] for a in match])
    .order("recorded_at", desc=True)
    .execute()
).data or []

print(f"\n{len(rows)} Chantee sessions:")
for r in rows:
    n = len(r.get("velocity_profile") or [])
    fs = r.get("sample_rate_hz")
    dur = f"{n / fs:.1f}s" if (n and fs) else "?"
    mj = r.get("metrics_json") or {}
    ph = mj.get("phases") or {}
    print(f"  {(r.get('recorded_at') or '')[:10]}  {(r.get('stroke_type') or '?'):<13} "
          f"{str(r.get('name'))[:24]:<26} fs={fs} n={n} ({dur}) "
          f"schema={ph.get('schema_version')} cycles={len(mj.get('cycles') or [])}")

target = [r for r in rows
          if (r.get("name") or "").strip() == "100%"
          and (r.get("recorded_at") or "").startswith("2026-08-19")]
if not target:
    target = [r for r in rows if (r.get("name") or "").strip() == "100%"]
    print("\n!! no 2026-08-19 match; falling back to name-only match")
if not target:
    print("\n!! NO SESSION NAMED '100%' FOUND")
    sys.exit(1)

s = target[0]
mj = s["metrics_json"] or {}
ph = mj.get("phases") or {}
print("\n=== TARGET ===")
print("id           ", s["id"])
print("recorded_at  ", s["recorded_at"])
print("stroke_type  ", s["stroke_type"])
print("sample_rate  ", s["sample_rate_hz"])
print("n samples    ", len(s.get("velocity_profile") or []))
print("schema_ver   ", ph.get("schema_version"))
print("boundaries   ", json.dumps(ph.get("boundaries"), indent=2)[:600])
print("kick_bands   ", len(ph.get("kick_bands") or []))
print("cycles       ", len(mj.get("cycles") or []))
print("seg_reliable ", mj.get("segmentation_reliable"))

mets = ph.get("metrics") or {}
print(f"\nmetrics: {len(mets)} keys")
by_phase = {}
for k, v in mets.items():
    p = (v or {}).get("phase", "?")
    by_phase.setdefault(p, []).append((k, (v or {}).get("value"), (v or {}).get("unit")))
for p, items in sorted(by_phase.items()):
    print(f"\n-- {p} ({len(items)})")
    for k, val, unit in sorted(items):
        print(f"   {k:<34} {val}  {unit or ''}")

with open("scratch/_home_session.json", "w", encoding="utf-8") as f:
    json.dump(s, f)
print("\nwrote scratch/_home_session.json")
