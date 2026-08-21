"""Probe the live database for the figures DATA-FLOW.md cites (read-only).

Every number in DATA-FLOW.md's snapshot section comes from this script, so the snapshot is
reproducible instead of a one-off measurement that rots in a chat log:

    python tools/dataflow_probe.py

Reports table row counts, per-column population for ``sessions``, the key STRUCTURE of every
jsonb payload, the storage buckets, and the handful of cross-column gaps the document calls
out (video without an origin, sessions predating the sample-rate migration).

Why this exists
---------------
``CODEBASE-AUDIT.md`` and ``API-AUDIT.md`` both assert things about the live system that were
true when written and are not now. A document that cites live figures needs a way to re-take
them, or it joins them. Phase 61-01's ``tools/rampup_impact.py`` set the precedent.

Read-only by construction
-------------------------
Only HTTP GET is issued — there is no insert, update, upsert or delete anywhere in this file,
and nothing is written to storage. It runs with the service-role key, which BYPASSES row-level
security, so that restriction is load-bearing rather than stylistic.

No personal data is printed. The script reports keys, types, counts and array lengths; it never
prints a field value, so athlete names, parent emails, dates of birth and session notes stay in
the database. Counting how many are non-null is safe; showing them is not.

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env. The key is used only as a request
header and is never printed.
"""
import argparse
import os
import sys
from collections import Counter
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

TABLES = [
    "athletes", "coaches", "devices", "reports",
    "session_annotations", "sessions", "teams",
]

# Fetched one row at a time rather than in the bulk population sweep: a velocity_profile is
# thousands of floats and 62 of them is a needless several MB over the wire.
HEAVY_COLS = ("velocity_profile", "distance_profile", "metrics_json", "metrics_json_auto")

# Printing any of these would move personal data out of the database and into a terminal
# scrollback, a summary, or a commit. Population counts only.
PII_COLS = ("name", "notes", "email", "parent_email", "parent_name", "dob")


class Rest:
    """Minimal read-only PostgREST client. GET only, by design."""

    def __init__(self, url, key):
        self.base = f"{url.rstrip('/')}/rest/v1"
        self.storage = f"{url.rstrip('/')}/storage/v1"
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    def count(self, table, **filters):
        """Exact row count, optionally filtered. Reads the Content-Range header, no rows.

        Selects "*" rather than a named key column: `devices` is keyed on chip_id and has no
        `id` at all, so any hardcoded column name is a 400 waiting for the next table.
        """
        resp = httpx.get(
            f"{self.base}/{table}",
            params={"select": "*", "limit": 0, **filters},
            headers={**self.headers, "Prefer": "count=exact"},
            timeout=30,
        )
        resp.raise_for_status()
        rng = resp.headers.get("content-range", "")
        return int(rng.split("/")[-1]) if "/" in rng else None

    def select(self, table, select, **params):
        resp = httpx.get(
            f"{self.base}/{table}",
            params={"select": select, **params},
            headers=self.headers,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    def buckets(self):
        resp = httpx.get(f"{self.storage}/bucket", headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()


def shape(value):
    """One-line description of a value's structure — keys and types, never contents."""
    if isinstance(value, dict):
        return "{" + ", ".join(sorted(value)) + "}"
    if isinstance(value, list):
        if not value:
            return "[] (empty)"
        return f"[{len(value)} x {type(value[0]).__name__}]"
    if value is None:
        return "null"
    return type(value).__name__


def rule(title):
    print(f"\n--- {title} " + "-" * max(0, 68 - len(title)))


def report_counts(db):
    rule("table row counts")
    for table in TABLES:
        print(f"  {table:22} {db.count(table)}")


def report_buckets(db):
    rule("storage buckets")
    try:
        for b in db.buckets():
            vis = "public" if b.get("public") else "private"
            print(f"  {b.get('name'):22} {vis}")
    except Exception as e:
        print(f"  (unavailable: {type(e).__name__})")


def report_sessions(db):
    """Per-column population over every session row."""
    total = db.count("sessions")
    probe = db.select("sessions", "*", limit=1)
    if not probe:
        print("  (no sessions)")
        return
    columns = sorted(probe[0].keys())
    light = [c for c in columns if c not in HEAVY_COLS]

    rows = db.select("sessions", ",".join(light))

    rule(f"sessions column population (of {total} rows)")
    for col in columns:
        if col in HEAVY_COLS:
            # Counted server-side instead of pulled down.
            non_null = total - db.count("sessions", **{col: "is.null"})
        else:
            non_null = sum(1 for r in rows if r.get(col) is not None)
        note = "  (pii: counted, never printed)" if col in PII_COLS else ""
        print(f"  {col:22} non-null {non_null}/{total}{note}")

    rule("distributions")
    for col in ("stroke_type", "upload_status"):
        dist = dict(Counter(r.get(col) for r in rows))
        print(f"  {col:22} {dist}")

    rule("cross-column gaps")
    orphan_video = db.count("sessions", video_path="not.is.null", video_origin_s="is.null")
    print(f"  video_path set but video_origin_s NULL   {orphan_video}/{total}")
    print(f"  sample_rate_hz NULL (pre-Phase-52 rows)  {db.count('sessions', sample_rate_hz='is.null')}/{total}")
    print(f"  metrics recomputed from an annotation    {total - db.count('sessions', metrics_json_auto='is.null')}/{total}")


def report_jsonb(db):
    """Key structure of every jsonb payload, sampled from real rows."""
    rule("jsonb payload structure — sessions")
    rows = db.select(
        "sessions",
        "id,sample_rate_hz,metrics_json,metrics_json_auto,velocity_profile,distance_profile",
        limit=1,
        order="created_at.desc",
    )
    if rows:
        row = rows[0]
        mj = row.get("metrics_json") or {}
        print(f"  metrics_json                {shape(mj)}")
        for key in ("session", "data_quality", "initial_phase"):
            if key in mj:
                print(f"    .{key:24} {shape(mj[key])}")
        cycles = mj.get("cycles") or []
        print(f"    .cycles                   {shape(cycles)}")
        if cycles:
            print(f"      cycles[0]               {shape(cycles[0])}")
        print(f"  metrics_json_auto           {shape(row.get('metrics_json_auto'))}")
        print(f"  velocity_profile            {shape(row.get('velocity_profile'))}")
        print(f"  distance_profile            {shape(row.get('distance_profile'))}")
        print(f"  sample_rate_hz              {row.get('sample_rate_hz')}  (this row's true rate)")

    rule("jsonb payload structure — session_annotations")
    rows = db.select("session_annotations", "phases,stroke_marks_s,source", limit=1)
    if rows:
        row = rows[0]
        print(f"  phases                      {shape(row.get('phases'))}")
        marks = row.get("stroke_marks_s") or []
        print(f"  stroke_marks_s              {shape(marks)}")
        print(f"  source                      {row.get('source')}")

    rule("jsonb payload structure — reports")
    rows = db.select("reports", "config_json", limit=1)
    if rows:
        cfg = rows[0].get("config_json") or {}
        print(f"  config_json                 {shape(cfg)}")
        metrics = cfg.get("metrics")
        if isinstance(metrics, list):
            print(f"    .metrics                  {shape(metrics)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("error: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not found in .env", file=sys.stderr)
        return 1

    db = Rest(url, key)
    try:
        report_counts(db)
        report_buckets(db)
        report_sessions(db)
        report_jsonb(db)
    except Exception as e:
        print(f"error: probe failed ({type(e).__name__}: {e})", file=sys.stderr)
        return 1

    print("\nread-only: this script issues GET only and writes nothing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
