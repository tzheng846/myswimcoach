"""
fetch_sessions.py — Download sessions from Supabase and open in inspect_cycles.

Usage
-----
    python fetch_sessions.py              # list latest 20 sessions
    python fetch_sessions.py --limit 50  # list latest 50 sessions
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# The local supabase/ folder (SQL migrations) shadows the installed supabase-py
# package when running from the project directory. Remove bare-path entries
# before importing so Python finds the real package in site-packages.
sys.path = [p for p in sys.path if p not in ('', '.')]

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL              = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

FS = 100.0   # velocity/distance profiles stored at 100 Hz


def _get_client():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def _fetch_sessions(sb, limit):
    resp = (
        sb.table("sessions")
        .select("id, name, recorded_at, stroke_type, athlete_id, velocity_profile, distance_profile")
        .order("recorded_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = resp.data or []

    # Enrich with athlete names — non-fatal if athletes table schema differs
    athlete_ids = list({r["athlete_id"] for r in rows if r.get("athlete_id")})
    athlete_names = {}
    if athlete_ids:
        try:
            ath_resp = (
                sb.table("athletes")
                .select("id, name")
                .in_("id", athlete_ids)
                .execute()
            )
            for a in (ath_resp.data or []):
                athlete_names[a["id"]] = a.get("name", "")
        except Exception:
            pass

    for r in rows:
        aid = r.get("athlete_id") or ""
        r["_athlete_label"] = athlete_names.get(aid) or (aid[:8] if aid else "—")

    return rows


def _display_list(sessions):
    print(f"\n  {'#':<4} {'Date':<20} {'Athlete':<16} {'Stroke':<14} Name")
    print("  " + "-" * 70)
    for i, s in enumerate(sessions, 1):
        date    = (s.get("recorded_at") or "")[:19].replace("T", " ")
        athlete = (s["_athlete_label"])[:15]
        stroke  = (s.get("stroke_type") or "—")[:13]
        name    = s.get("name") or s["id"][:8]
        n_pts   = len(s.get("velocity_profile") or [])
        dur     = f"{n_pts / FS:.0f}s" if n_pts else "—"
        print(f"  {i:<4} {date:<20} {athlete:<16} {stroke:<14} {name}  ({dur})")
    print()


def _parse_selection(raw, n):
    """Parse '1 3 5', '1,3,5', or '1-3' into sorted 0-based indices."""
    indices = set()
    for tok in raw.replace(",", " ").split():
        if "-" in tok:
            parts = tok.split("-", 1)
            lo, hi = int(parts[0]), int(parts[1])
            indices.update(range(lo - 1, hi))
        else:
            indices.add(int(tok) - 1)
    return sorted(i for i in indices if 0 <= i < n)


def _save_csv(session, out_dir):
    vel  = session.get("velocity_profile") or []
    dist = session.get("distance_profile") or []
    n    = len(vel)
    if n == 0:
        return None

    name      = session.get("name") or ""
    safe_name = "".join(c if (c.isalnum() or c in "-_") else "_" for c in name)
    uid       = session["id"][:8]
    out_path  = Path(out_dir) / f"{safe_name}_{uid}.csv"

    t  = np.arange(n) / FS
    df = pd.DataFrame({
        "time_s": t,
        "vel_ms":  [float(v) if v is not None else float("nan") for v in vel],
        "dist_m":  [float(d) if d is not None else float("nan") for d in dist],
    })
    df.to_csv(out_path, index=False, float_format="%.4f")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="List Supabase sessions, pick some, visualise in browser."
    )
    parser.add_argument(
        "--limit", type=int, default=20,
        help="Max sessions to list (default: 20)",
    )
    args = parser.parse_args()

    sb       = _get_client()
    sessions = _fetch_sessions(sb, args.limit)

    if not sessions:
        print("No sessions found.")
        sys.exit(0)

    _display_list(sessions)

    try:
        raw = input("Select sessions (e.g. 1  or  1 3 5  or  1-3): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        sys.exit(0)

    if not raw:
        print("No selection — exiting.")
        sys.exit(0)

    try:
        indices = _parse_selection(raw, len(sessions))
    except ValueError:
        print("Invalid selection.")
        sys.exit(1)

    if not indices:
        print("Nothing matched.")
        sys.exit(0)

    Path("processed").mkdir(exist_ok=True)
    csv_paths = []
    for i in indices:
        s    = sessions[i]
        path = _save_csv(s, "processed")
        if path:
            print(f"  Saved  -> {path}")
            csv_paths.append(str(path))
        else:
            label = s.get("name") or s["id"][:8]
            print(f"  Skipped {label} — no signal data")

    if not csv_paths:
        print("Nothing to plot.")
        sys.exit(0)

    print(f"\nLaunching inspect_cycles with {len(csv_paths)} session(s)...")
    script = Path(__file__).parent / "inspect_cycles.py"
    subprocess.run([sys.executable, str(script)] + csv_paths + ["--cycles", "0", "6"])


if __name__ == "__main__":
    main()
