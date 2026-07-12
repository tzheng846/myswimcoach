"""
fetch_annotations.py — Dump the trial-annotation ground-truth set to a local JSON.

Dev tool for segmenter tuning (Phase 47-04 → 16-06): pulls every annotated session
from Supabase (service key, like fetch_sessions.py) and writes annotations_export.json
in the same record shape as GET /annotations/export.

Usage
-----
    python fetch_annotations.py                      # writes annotations_export.json
    python fetch_annotations.py --out my_labels.json
"""

import argparse
import json
import os
import sys

# The local supabase/ folder (SQL migrations) shadows the installed supabase-py
# package when running from the project directory. Remove bare-path entries
# before importing so Python finds the real package in site-packages.
sys.path = [p for p in sys.path if p not in ('', '.')]

from collections import Counter

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL              = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def _get_client():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def _fetch(sb):
    ann_resp = (
        sb.table("session_annotations")
        .select("session_id, phases, stroke_marks_s, source, updated_at")
        .execute()
    )
    annotations = ann_resp.data or []
    if not annotations:
        return []

    ids = [a["session_id"] for a in annotations]
    sess_resp = (
        sb.table("sessions")
        .select("id, stroke_type, created_at, raw_csv_path, metrics_json")
        .in_("id", ids)
        .execute()
    )
    sess_by_id = {s["id"]: s for s in (sess_resp.data or [])}

    out = []
    for a in annotations:
        s = sess_by_id.get(a["session_id"]) or {}
        lap = ((s.get("metrics_json") or {}).get("session") or {}).get("lap_time_s")
        out.append({
            "session_id":   a["session_id"],
            "stroke_type":  s.get("stroke_type"),
            "created_at":   s.get("created_at"),
            "duration_s":   lap,
            "raw_csv_path": s.get("raw_csv_path"),
            "annotation": {
                "phases":         a.get("phases"),
                "stroke_marks_s": a.get("stroke_marks_s"),
                "source":         a.get("source"),
                "updated_at":     a.get("updated_at"),
            },
        })
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Export annotated sessions (ground truth) to a local JSON file."
    )
    parser.add_argument(
        "--out", default="annotations_export.json",
        help="Output path (default: annotations_export.json)",
    )
    args = parser.parse_args()

    sb = _get_client()
    records = _fetch(sb)

    if not records:
        print("No annotated sessions found.")
        sys.exit(0)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"sessions": records}, f, indent=2)

    strokes = Counter((r.get("stroke_type") or "unknown") for r in records)
    marks   = sum(len(r["annotation"].get("stroke_marks_s") or []) for r in records)
    print(f"Wrote {len(records)} annotated session(s) -> {args.out}")
    print(f"  stroke marks total: {marks}")
    for stroke, n in strokes.most_common():
        print(f"  {stroke}: {n}")


if __name__ == "__main__":
    main()
