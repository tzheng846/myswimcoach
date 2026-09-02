"""Phase 90-02 — expected leaderboard counts, straight from the database.

READ-ONLY. Prints nothing but counts; writes nothing; never echoes a credential.

Purpose: 90-03's human-verify. The coach-facing page partitions the roster CLIENT-side, so the
cheapest possible check that the partition is right is a second, independent count taken
server-side. If this table and the page disagree, the page is wrong.

It mirrors web/lib/leaderboard.js deliberately: the same 15 m guard, the same DERIVED lap time
(finish_s - dive_start_s, never the stored metrics_json.session.lap_time_s, which is the duration
of the RECORDING), and the same "at least one non-null value in the athlete's eligible swims"
definition of rankable.

One known asymmetry: this runs as the service role and therefore sees every athlete, while the
page reads under RLS as one signed-in coach. With a single coach on this database the two agree;
with more than one they will not, and that is expected rather than a defect.

Run: PYTHONIOENCODING=utf-8 python scratch/_lb_expect.py
"""

import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

MIN_DIST_M = 15.0
SEL = (
    "id, athlete_id, stroke_type, recorded_at, "
    "mean_vel_ms:metrics_json->session->mean_vel_ms, "
    "max_vel_ms:metrics_json->session->max_vel_ms, "
    "total_dist_m:metrics_json->session->total_dist_m, "
    "dive_start_s:metrics_json->phases->boundaries->dive_start_s, "
    "finish_s:metrics_json->phases->boundaries->finish_s, "
    "uw_avg_speed:metrics_json->phases->underwater->uw_avg_speed->value, "
    "splits_5m:metrics_json->phases->swim->splits_5m->value, "
    "splits_10m:metrics_json->phases->swim->splits_10m->value, "
    "splits_15m:metrics_json->phases->swim->splits_15m->value, "
    "splits_20m:metrics_json->phases->swim->splits_20m->value"
)
METRICS = [
    ("mean_vel_ms", "Average speed"),
    ("max_vel_ms", "Top speed"),
    ("elapsed_s", "Lap time"),
    ("uw_avg_speed", "Underwater speed"),
    ("splits_5m", "Split 0-5 m"),
    ("splits_10m", "Split 5-10 m"),
    ("splits_15m", "Split 10-15 m"),
    ("splits_20m", "Split 15-20 m"),
]


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def metric_value(row, key):
    """One row's value for one metric, or None. Mirrors leaderboard.js metricValue()."""
    if key == "elapsed_s":
        dive, finish = row.get("dive_start_s"), row.get("finish_s")
        if not (is_num(dive) and is_num(finish)):
            return None
        elapsed = finish - dive
        return elapsed if elapsed > 0 else None
    v = row.get(key)
    return v if is_num(v) else None


athletes = {a["id"]: a["name"] for a in sb.table("athletes").select("id,name").order("name").execute().data}
rows = sb.table("sessions").select(SEL).order("recorded_at", desc=True).execute().data

mine = [r for r in rows if r["athlete_id"] in athletes]
elig = [r for r in mine if is_num(r.get("total_dist_m")) and r["total_dist_m"] >= MIN_DIST_M]

print(f"athletes on roster : {len(athletes)}")
print(f"sessions fetched   : {len(rows)}  (roster-scoped: {len(mine)})")
print(f"guard total_dist_m >= {MIN_DIST_M:g} m : {len(elig)} eligible, {len(mine) - len(elig)} excluded")

# Tab order on the page is swims descending, then label — match it so the two read side by side.
strokes = sorted({r["stroke_type"] for r in elig})
strokes.sort(key=lambda s: (-len([r for r in elig if r["stroke_type"] == s]), s))

checked = 0
for stroke in strokes:
    ss = [r for r in elig if r["stroke_type"] == stroke]
    ids = {r["athlete_id"] for r in ss}
    checked += len(ss)
    print(f"\n{stroke.upper()}: {len(ids)} athletes / {len(ss)} eligible swims")
    for key, label in METRICS:
        rankable = sum(
            1
            for a in ids
            if any(metric_value(r, key) is not None for r in ss if r["athlete_id"] == a)
        )
        print(f"  {label:<18} {rankable} of {len(ids)} athletes ranked")

print(f"\nstroke blocks: {len(strokes)}  |  swims across blocks: {checked}  (must equal {len(elig)})")
