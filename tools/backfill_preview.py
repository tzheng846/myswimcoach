"""Preview what Phase 59-03 would change on ALREADY-STORED sessions. WRITES NOTHING.

Phase 59-03 fixed two coupled errors in the auto pipeline — the swim window and the
freestyle/backstroke cycle definition. Newly-processed sessions get the corrected
numbers immediately; rows already in Supabase keep whatever was computed when they were
uploaded. This tool quantifies that gap so a later backfill plan can be written against
real numbers instead of an estimate.

⚠ THIS TOOL IS READ-ONLY BY CONSTRUCTION. It contains no update/upsert/insert/delete
call, and 59-03's verification greps for exactly that. Authorising the DB write is a
separate plan and a separate decision (CONTEXT D20).

⚠ THE CORPUS IS ALREADY MIXED, AND WAS BEFORE THIS PLAN. Sessions whose metrics were
recomputed from a human annotation are ALREADY on the human scale — annotating a session
has always halved its freestyle stroke rate relative to its un-annotated neighbours.
59-03 does not create that inconsistency; it changes which axis it falls on. Those rows
are flagged ANNOTATED below and **a backfill must never overwrite them**: their
metrics_json is human-derived ground truth, and replacing it with a machine estimate
would destroy annotation work.

Usage:
    python tools/backfill_preview.py
    python tools/backfill_preview.py --stroke freestyle
"""
import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# Import the real supabase package before the repo root joins sys.path — the local
# supabase/ SQL directory shadows it. Order is load-bearing; see score_segmenter.py.
sys.path = [p for p in sys.path if p not in ("", ".", str(_ROOT))]
try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None
sys.path.insert(0, str(_ROOT))

import numpy as np

import annotations as annot
import metrics as m

PAIRED_STROKES = ("freestyle", "backstroke")


def _fetch():
    if create_client is None:
        sys.exit("Error: supabase-py is not importable.")
    try:
        from dotenv import load_dotenv
        load_dotenv(str(_ROOT / ".env"))
    except ImportError:
        pass
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        sys.exit("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    sb = create_client(url, key)
    return (sb.table("sessions")
            .select("id, stroke_type, created_at, sample_rate_hz, velocity_profile, "
                    "distance_profile, metrics_json, metrics_json_auto")
            .execute().data) or []


def _stored(row):
    """The stroke rate/count a coach sees today, and whether it is human-derived."""
    mj = row.get("metrics_json") or {}
    sess = mj.get("session") or {}
    annotated = bool((mj.get("data_quality") or {}).get("recomputed_from_annotation"))
    return sess.get("stroke_rate_spm"), sess.get("stroke_count"), annotated


def _recompute(row):
    """What the CURRENT code would produce from the stored profiles. Never raises."""
    vel = np.asarray(row.get("velocity_profile") or [], dtype=float)
    dist = np.asarray(row.get("distance_profile") or [], dtype=float)
    if vel.size < 200:
        return None, None, "no velocity_profile"
    if dist.size != vel.size:
        # Distance only feeds dps/impulse, not the rate — synthesize so the rate is
        # still previewable, and say so rather than silently substituting.
        dist = np.concatenate(([0.0], np.cumsum(np.maximum(vel[:-1], 0)) / 1.0))
        note = "dist synthesized"
    else:
        note = ""
    fs = float(row.get("sample_rate_hz") or annot.FS_HZ)
    t = np.arange(vel.size) / fs
    try:
        s = m.compute_session_metrics(t, vel, dist,
                                      stroke_type=row.get("stroke_type"))["session"]
        return s.get("stroke_rate_spm"), s.get("stroke_count"), note
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"


def _f(v, nd=1):
    return "-" if v is None or (isinstance(v, float) and v != v) else f"{v:.{nd}f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stroke", help="limit to one stroke_type")
    args = ap.parse_args()

    rows = [r for r in _fetch() if (r.get("stroke_type") or "") in PAIRED_STROKES]
    if args.stroke:
        rows = [r for r in rows if r.get("stroke_type") == args.stroke]
    rows.sort(key=lambda r: r.get("created_at") or "")

    print("=" * 96)
    print(f"BACKFILL PREVIEW - {len(rows)} freestyle/backstroke sessions. NOTHING IS WRITTEN.")
    print("=" * 96)
    print(f'{"created":<18}{"stroke":<12}{"spm now":>9}{"spm new":>9}{"ratio":>8}'
          f'{"n now":>7}{"n new":>7}  flag')

    changed, annotated_rows, failed = [], [], 0
    for r in rows:
        old_spm, old_n, annotated = _stored(r)
        new_spm, new_n, note = _recompute(r)
        if new_spm is None:
            failed += 1
        ratio = (old_spm / new_spm) if (old_spm and new_spm) else None
        flag = "ANNOTATED - do not overwrite" if annotated else note
        if annotated:
            annotated_rows.append(r)
        elif ratio is not None and abs(ratio - 1.0) > 0.02:
            changed.append(ratio)
        print(f'{(r.get("created_at") or "")[:16]:<18}{r["stroke_type"]:<12}'
              f'{_f(old_spm):>9}{_f(new_spm):>9}{_f(ratio, 2):>8}'
              f'{str(old_n or "-"):>7}{str(new_n or "-"):>7}  {flag}')

    print(f'\n{"-" * 96}')
    print(f"  total freestyle/backstroke rows      {len(rows)}")
    print(f"  ANNOTATED (already human scale)      {len(annotated_rows)}   <- a backfill "
          f"must SKIP these")
    print(f"  auto rows whose numbers would move   {len(changed)}")
    if changed:
        print(f"  their stored/new ratio               median {np.median(changed):.2f}   "
              f"range {min(changed):.2f}-{max(changed):.2f}")
    if failed:
        print(f"  could not recompute                  {failed}")
    print("\nNo write was performed. Authorising the DB update is a separate plan.")


if __name__ == "__main__":
    main()
